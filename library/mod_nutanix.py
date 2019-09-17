from ansible.module_utils.basic import *
import hashlib
import nutanix
import re
import requests


NUM_THREADS_PER_CORE = 1
NUM_VCPUS_PER_SOCKET = 1
MINIMUM_MEMORY = 256


def get_vm_from_list(vm_dict, search):
    """
    This function parses the vm_dict that is returned from the method call -
    nutanix_object.get_vms() from the nutanix.py library.

    :param vm_dict: Dictionary that is returned from Prism Central - vms/list
    :param search: This is the VM name to search
    :return: Message is returned whether the VM exists or not.
    """
    vm_return = None
    for i in vm_dict['entities']:
        if search.lower() == (i['spec']['name']).lower():
            vm_return = {
                'vm_name': i['spec']['name'],
                'vm_uuid': i['metadata']['uuid']
            }
            break

    if vm_return is not None:
        return "VM already exists", vm_return
    else:
        return None, "No VM with name: " + search + " exists"


def check_delete(delete_result):
    if delete_result['state'] == "ERROR":
        return '; '.join([thing['message'] for thing in delete_result['message_list']])
    else:
        return None


def get_vlan_uuid(vlan_dict, search):
    """
    Parses the vlan_dict that is received from the method call -

           vlan_dict = nutanix_object.get_networks(api=nutanix.ELEMENT_API)

    :param vlan_dict:
    :param search: VLAN ID is an str type
    :return: Dictionary of matched VLANs is returned when found_vlan dictionary
    is NOT none.
    """

    found_vlan = None
    for i in vlan_dict['entities']:
        vlan_id = i['vlan_id']

        if search == vlan_id:
            found_vlan = {
                'network_uuid': i['uuid'],
                'vlan_name': i['name'],
                'vlan_id': i['vlan_id']
            }
            break

    if not found_vlan:
        return "Nothing matched your search", None
    else:
        return None, found_vlan


def get_cluster_ip(cluster_dicts, search):  # <- could use the variable name search_str= instead of name
    '''
    build with the capability to search for all if name==None
    '''

    cluster_ip = {}
    new_dict = {}
    found_cluster = {}

    for i in range(len(cluster_dicts['entities'])):
        cluster_name = cluster_dicts['entities'][i]['status']['name']

        if search in cluster_name:
            cluster_ip = cluster_dicts['entities'][i]['spec']['resources']['network']['external_ip']
            found_cluster[i] = {cluster_name: cluster_ip}

        else:
            new_dict[cluster_name] = cluster_dicts['entities'][i]['spec']['resources']['network']

    if not cluster_ip:
        return "No clusters matched your search criteria", {'cluster_ips': new_dict}

    else:
        return None, {'matches': found_cluster, 'external_ip': cluster_ip, 'other':new_dict}


def determine_placement(vm, candidates, sibling_counts):
    '''
    Determine a good spot for the next created VM to land.
    '''
    if len(candidates) == 0:
        return "No clusters available", None

    for cname in candidates.keys():
        if cname not in sibling_counts:
            candidates[cname]['sibling_count'] = 0
        else:
            candidates[cname]['sibling_count'] = sibling_counts[cname]

    if len(candidates) == 1:
        cname = candidates.keys()[0]
        return None, [{'cluster_name': cname,
                       'sibling_count': candidates[cname]['sibling_count'],
                       'free_memory': candidates[cname]['free_memory']}]

    else:
        # Sort ascending by sibling count, descending by free memory, then alphabetically
        find_least = [(v[1]['sibling_count'], v[1]['free_memory']*-1, v[0]) for v in candidates.items()]
        # Then turn it into something usable, printable and that makes sense
        result = [{'cluster_name': v[2],
                   'sibling_count': candidates[v[2]]['sibling_count'],
                   'free_memory': candidates[v[2]]['free_memory']} for v in sorted(find_least)]
        return None, result


def get_cluster_uuid(cluster_dicts, search):
    ''' build with the capability to search for all if name==None '''

    # We're looking for hostnames, which are generally
    # case insensitive
    find_pattern = re.compile(search, re.IGNORECASE)

    found_cluster_list = []
    not_match_list = []
    for i in range(len(cluster_dicts['entities'])):
        cluster_name = cluster_dicts['entities'][i]['status']['name']

        if find_pattern.search(cluster_name):
            found_cluster = {
                "cluster_uuid": cluster_dicts['entities'][i]['metadata']['uuid'],
                "cluster_name": cluster_dicts['entities'][i]['status']['name'],
                "cluster_ip": cluster_dicts['entities'][i]['status']['resources']['network']['external_ip']
            }
            found_cluster_list.append(found_cluster)

        else:
            not_matched = {
                "cluster_uuid": cluster_dicts['entities'][i]['metadata']['uuid'],
                "cluster_name": cluster_dicts['entities'][i]['status']['name']
            }
            not_match_list.append(not_matched)

    if len(found_cluster_list) <= 0:
        return "Didn't find a cluster that matched", {'clusters': not_match_list}
    else:
        return None, {
                'matched': found_cluster_list,
                'not_matched': not_match_list,
                }


def get_host_uuids(cluster_dicts):
    # gets a list of host uuids to use
    # to get the host memory stats
    host_uuids = []
    if not cluster_dicts:
        return "unable to get host uuids - " \
               "no cluster_dicts was passed"
    else:
        for unit in cluster_dicts['rackable_units']:
            for uuid in cluster_dicts['rackable_units'][unit]['node_uuids']:
                host_uuids.append(uuid)

    return host_uuids


def get_cluster_mem_total(host_dicts):
    """ parses the host_dicts for total physical
    memory in the cluster (bytes)
    """
    if not host_dicts:
        return "didn't receive a host_dicts value", None
    else:
        mem_total = 0
        for i in host_dicts['entities']:
            if i['memory_capacity_in_bytes'] is None:
                continue
            else:
                mem_total = mem_total + int(i['memory_capacity_in_bytes'])
        return None, mem_total


def get_memory_usage(cluster_dicts):
    """
    parses the cluster_dict for the PPM value of total
    cluster memory, and converts from PPM to decimal
    which represents the % of memory that is used.

    example: .75 (75%)
    :param cluster_dicts:
    :return: decimal of memory usage .XX
    """
    if not cluster_dicts:
        return "didn't receive a cluster_dict value", None
    else:
        mem_usage_ppm = cluster_dicts['entities'][0]['stats']['hypervisor_memory_usage_ppm']
        mem_usage_ppm = float(mem_usage_ppm)
        # convert ppm to decimal value and only uses 2
        # decimal places
        mem_decimal = round((mem_usage_ppm / 1000000), 2)

    return None, mem_decimal


def get_cluster_capacity(user, password,
        port, central_addr,
        element_addr, max_memory):

    try:
        c_element = nutanix.Nutanix(username=user, password=password,
                                         port=port, central_addr=central_addr,
                                         element_addr=element_addr)
        host_dicts = c_element.get_hosts(api=nutanix.ELEMENT_API)
        cluster_dicts = c_element.get_cluster_element(api=nutanix.ELEMENT_API)
        ans_failure, total_mem_bytes = get_cluster_mem_total(host_dicts)
        ans_failure, memory_usage_decimal = get_memory_usage(cluster_dicts)

        if not ans_failure:
            total_mem_mb = total_mem_bytes/1024/1024
            # memory_usage_decimal is ppm / 1 million so 750000 ppm (75%)
            # would be .75
            used_memory = memory_usage_decimal * total_mem_mb
            free_memory = round(((total_mem_mb * max_memory) - used_memory), 2)
            return None, {
                "free_memory": free_memory,
                "used_memory": used_memory,
                "total_mem_mb": total_mem_mb
            }
        else:
            return ans_failure, None
    except requests.exceptions.RequestException as e:
        return "get_cluster_capacity failure: " + str(e), None


def get_vm_assign_candidates(user, password,
        port, central_addr, filtered_clusters, vm_memory, max_memory):
    """
    Return a list of Nutanix clusters containing enough memory to assign a VM
    without exceeding some <max_memory> threshold.
    """
    candidates = {}

    for c in filtered_clusters:
        ans_failure, cluster_capacity = get_cluster_capacity(user, password,
                port, central_addr, c['cluster_ip'], max_memory)
        if ans_failure:
            return ans_failure, None
        elif cluster_capacity['free_memory'] >= vm_memory:
            candidates[c['cluster_name']] = cluster_capacity
    return None, candidates


def get_sibling_counts(nutanix_object, vm):
    s = re.search('^(?P<basename>.*[^0-9])(?P<cnumber>[0-9]+)$', vm)
    if s:
        vm_cnumber = int(s.group('cnumber'))
        vm_basename = s.group('basename')
    else:
        # Hostname cluster numbers are 1-starting
        vm_cnumber = 1
        vm_basename = vm

    vm_siblings = nutanix_object.get_vms_like(vm_basename, api=nutanix.CENTRAL_API)
    counts = {}
    for v in vm_siblings['entities']:
        v_ntx_cluster_name = v['spec']['cluster_reference']['name']
        if v_ntx_cluster_name in counts:
            counts[v_ntx_cluster_name] = counts[v_ntx_cluster_name] + 1
        else:
            counts[v_ntx_cluster_name] = 1
    return counts


def main():

    module = AnsibleModule(
        argument_spec=dict(
            action=dict(required=True, choices=[
                "add_project",
                "add_vlan",
                "delete_vm",
                "get_cluster",
                "get_project",
                "get_vlan",
                "get_vlan_uuid",
                "get_vm",
                "query_vm_details",
                "resize_vm",
                "update_vm_project",
                "update_vm_category",
                "find_vms_in_category"
            ]),
            central_addr=dict(required=False, type="str"),
            cluster=dict(required=False, type="str"),
            cluster_pattern=dict(required=False, type="str"),
            element_addr=dict(required=False, type="str"),
            max_memory=dict(required=False, type="str"),
            password=dict(required=True, type="str"),
            port=dict(required=False, type="str"),
            project=dict(required=False, type="str"),
            user=dict(required=True, type="str"),
            vlan=dict(required=False, type="int"),
            vm=dict(required=False, type="str"),
            vm_cpu=dict(required=False, type="str"),
            vm_memory=dict(required=False, type="str"),
            category_name=dict(required=False, type="str"),
            category_value=dict(required=False, type="str")
        ))

    # this is where all the module params get defined
    user = module.params["user"]
    password = module.params["password"]
    vlan = module.params["vlan"]
    vm = module.params["vm"]
    port = module.params["port"]
    action = module.params["action"]
    central_addr = module.params["central_addr"]
    element_addr = module.params["element_addr"]
    project = module.params["project"]
    cluster_pattern = module.params["cluster_pattern"]
    vm_memory = module.params["vm_memory"]
    vm_cpu = module.params["vm_cpu"]
    max_memory = module.params["max_memory"]
    category_name = module.params["category_name"]
    category_value = module.params["category_value"]

    ans_failure = None
    ans_return = {}
    ans_changed = False

    try:
        # instantiating the Nutanix class via nutanix_object.
        nutanix_object = nutanix.Nutanix(username=user, password=password,
                                     port=port, central_addr=central_addr,
                                     element_addr=element_addr)

    except Exception as e:
        ans_failure = {"Initialization Error": "{}".format(str(e))}
        module.fail_json(msg=ans_failure,
                         changed=ans_changed,
                         meta=ans_return)

    if action == 'get_cluster':
        if (not vm_memory) or \
           (not max_memory):
            ans_failure = "no cluster address or vm_memory or" \
                          "max_memory was entered!"
        if not ans_failure:
            vm_memory = int(vm_memory)
            if vm_memory < MINIMUM_MEMORY :
                ans_failure = "vm_memory must be at least {m} mb or greater".format(m=MINIMUM_MEMORY)
            ans_return['vm_memory_mb'] = vm_memory

        if not ans_failure:
            max_memory = float(max_memory)
            if max_memory <= 0.0 or max_memory > 1.0:
                ans_failure = "max_memory lies outside the (0.0,1.0] range: {m}".format(m=max_memory)
            ans_return['max_memory'] = max_memory

        if not ans_failure:
            cluster_dicts = nutanix_object.get_cluster(api=nutanix.CENTRAL_API)
            ans_failure, filtered_clusters = get_cluster_uuid(cluster_dicts, search=cluster_pattern)
            ans_return['clusters_matching_pattern'] = filtered_clusters

        if not ans_failure:
            ans_failure, candidates = get_vm_assign_candidates(
                user,
                password,
                port,
                central_addr,
                filtered_clusters['matched'],
                vm_memory,
                max_memory)
            ans_return['candidates'] = candidates

        if not ans_failure:
            sibling_counts = get_sibling_counts(nutanix_object, vm)
            ans_failure, placement_list = determine_placement(vm, candidates, sibling_counts)
            ans_return['placement_list'] = placement_list

        if not ans_failure:
            for i in filtered_clusters['matched']:
                if i['cluster_name'] == placement_list[0]['cluster_name']:
                    ans_return['recommended_cluster'] = i
                    break

    elif action == 'get_cluster_ip':
        cluster = module.params["cluster"]
        cluster_dicts = nutanix_object.get_cluster(api=nutanix.CENTRAL_API)
        ans_failure, ans_return = get_cluster_ip(cluster_dicts, search=cluster)

    elif action == 'get_vlan':
        if (not element_addr) or (not vlan):
            ans_failure = "No element address OR vlan entered"
        else:
            vlan_dict = nutanix_object.get_networks(api=nutanix.ELEMENT_API)
            ans_failure, ans_return = get_vlan_uuid(vlan_dict, search=vlan)

    elif action == 'add_vlan':
        if (not element_addr) or (not vlan):
            ans_failure = "No element address OR vlan entered"
        else:
            vlan_name = 'VLAN_' + str(vlan)
            vlan_dict = nutanix_object.get_networks(api=nutanix.ELEMENT_API)
            ans_failure, ans_return = get_vlan_uuid(vlan_dict, search=vlan)

            if ans_failure:
                try:
                    ans_return = nutanix_object.add_network(api=nutanix.ELEMENT_API,
                                                            network_name=vlan_name,
                                                            vlan_id=vlan)
                    ans_changed = True
                    ans_failure = None

                except requests.exceptions.RequestException as e:
                    ans_failure = "failed to add VLAN: " + str(e)
                    ans_return = None
                    ans_changed = False
            else:
                ans_changed = False
                ans_failure = "VLAN already exists!"

    elif action == 'get_vm':
        if not vm:
            ans_failure = "No VM was passed!"
            ans_return = None
        else:
            try:
                vm_return = nutanix_object.get_vm(api=nutanix.CENTRAL_API, vmname=vm)
                if vm_return['entities']:
                    ans_failure = "VM already exists!"
                    ans_return = vm_return['entities']
                else:
                    ans_failure = None
                    ans_return = "No VM matched!"

            except requests.exceptions.RequestException as e:
                ans_failure = "get_vm failure: " + str(e)
                ans_return = None

    elif action == 'query_vm_details':
        if not vm:
            ans_failure = "No VM was passed!"
            ans_return = None
        else:
            try:
                vm_return = nutanix_object.get_vm(api=nutanix.CENTRAL_API, vmname=vm)
                if vm_return['entities']:
                    ans_failure = None
                    ans_return = vm_return['entities']
                else:
                    ans_failure = "No VM exists with name: " + vm
                    ans_return = None

            except requests.exceptions.RequestException as e:
                ans_failure = "get_vm failure: " + str(e)
                ans_return = None

    elif action == 'resize_vm':
        if not vm_cpu and not vm_memory:
            ans_failure = "Need to specify at least one of vm_cpu or vm_memory for resize_vm"
            ans_changed = False
            ans_return = None

        if not ans_failure:
            vm_dict = nutanix_object.get_vm(vmname=vm)
            if vm_dict['metadata'] == 'failure':
                ans_failure = "Cant locate VM: " + vm
                ans_return = None
                ans_changed = False
            else:
                new_dict = {'metadata': vm_dict['entities'][0]['metadata'], 'spec': vm_dict['entities'][0]['spec']}
                vm_uuid = new_dict['metadata']['uuid']

        if not ans_failure and vm_cpu:
            vm_cpu = int(vm_cpu)
            if vm_cpu <= 0:
                ans_failure = "vm_cpu must be a positive number"

        if not ans_failure and vm_cpu:
            old_cpu = new_dict['spec']['resources']['num_sockets']
            if vm_cpu != old_cpu:
                new_dict['spec']['resources']['num_sockets'] = vm_cpu

        if not ans_failure and vm_memory:
            vm_memory = int(vm_memory)
            old_memory = new_dict['spec']['resources']['memory_size_mib']

        # The rest of the blocks for  memory changes
        # really only need to be done if old_memory != vm_memory,
        # since if there is no memory changes, why do anything?
        if not ans_failure and vm_memory and old_memory != vm_memory:
            if vm_memory < MINIMUM_MEMORY :
                ans_failure = "vm_memory must be at least {m} mb or greater".format(m=MINIMUM_MEMORY)

        if not ans_failure and vm_memory and old_memory != vm_memory:
            # If we're trying to shrink memory, just let that right on through
            if old_memory > vm_memory:
                new_dict['spec']['resources']['memory_size_mib'] = vm_memory
            # If we're trying to grow memory, we'll need to do a free memory check
            # (which, as can be seen, is a pain)
            else:
                if not max_memory:
                    ans_failure = "max_memory not specified, need to specify it for resize_vm if" + \
                            " vm_memory is specified"

                if not ans_failure:
                    max_memory = float(max_memory)
                    if max_memory <= 0.0 or max_memory > 1.0:
                        ans_failure = "max_memory lies outside the (0.0,1.0] range: {m}".format(m=max_memory)

                if not ans_failure:
                    cluster_uuid = vm_dict['entities'][0]['spec']['cluster_reference']['uuid']
                    try:
                        cluster_raw = nutanix_object.get_cluster_w_uuid(api=nutanix.CENTRAL_API,
                                cluster_uuid=cluster_uuid)
                        if 'state' in cluster_raw and cluster_raw['state'] == 'ERROR':
                            ans_failure = "Can't locate cluster: " + cluster_uuid
                            ans_return = None
                            ans_changed = False
                    except Exception as e:
                        ans_failure = "Can't locate cluster: " + cluster_uuid
                        ans_return = None
                        ans_changed = False

                if not ans_failure:
                    element_addr = cluster_raw['spec']['resources']['network']['external_ip']
                    ans_failure, cluster_capacity = get_cluster_capacity(user, password,
                            port, central_addr, element_addr, max_memory)

                if not ans_failure:
                    # FINALLY, what you've all been waiting for:
                    # The ACTUAL memory check
                    if cluster_capacity['free_memory'] >= (vm_memory - old_memory):
                        new_dict['spec']['resources']['memory_size_mib'] = vm_memory
                    else:
                        ans_failure = "Insufficient memory for resize_vm"
                        ans_return = cluster_capacity

        if not ans_failure:
                # Guard to make sure that if nothing needs changed, don't change anything
                if (vm_cpu and vm_cpu != old_cpu) or (vm_memory and vm_memory != old_memory):
                    try:
                        ans_return = nutanix_object.update_vm(nutanix.CENTRAL_API,vm_uuid,new_dict)
                        ans_changed = True
                    except requests.exceptions.RequestException as e:
                        ans_failure = "VM update error: {e}".format(e=str(e))
                        ans_return = None
                        ans_changed = False
                else:
                    ans_failure = None
                    ans_return = "No changes needed"
                    ans_changed = False

    elif action == 'update_vm_project':
        proj_exists = nutanix_object.get_project(api=nutanix.CENTRAL_API, proj_name=project)
        if proj_exists['metadata']['total_matches'] == 0:
            ans_return = proj_exists, "Project with name " + project + " doesn't exist."
            ans_failure = True
            ans_changed = False
        else:
            proj_dict = proj_exists['entities'][0]
            proj_uuid = proj_dict['metadata']['uuid']
            proj_name = proj_dict['spec']['name']

            vm_dict = nutanix_object.get_vm(vmname=vm)
            if vm_dict['metadata'] == 'failure':
                ans_failure = "Cant locate VM: " + vm
                ans_return = None
                ans_changed = False

            else:
                new_dict = {'metadata': vm_dict['entities'][0]['metadata'], 'spec': vm_dict['entities'][0]['spec']}
                vm_uuid = new_dict['metadata']['uuid']
                new_dict['metadata']['project_reference']['name'] = proj_name
                new_dict['metadata']['project_reference']['uuid'] = proj_uuid

                try:
                    ans_return = nutanix_object.update_vm(nutanix.CENTRAL_API,vm_uuid,new_dict)
                    ans_changed = True

                except requests.exceptions.RequestException as e:
                    ans_failure = "VM Update Error error: " + str(e)
                    ans_return = None
                    ans_changed = False

    elif action == 'update_vm_category':
        if not (category_value or
                category_name or
                vm):
            ans_failure = "Category Name/Value and VM is required!"
        else:
            try:
                nutanix_object.get_category(category_name,
                                            api=nutanix.CENTRAL_API)
                nutanix_object.get_category_value(category_name,
                                                  category_value,
                                                  api=nutanix.CENTRAL_API)
                vm_dict = nutanix_object.get_vm(api=nutanix.CENTRAL_API,
                                                vmname=vm)
                if vm_dict['entities']:
                    # setting VM uuid
                    vm_uuid = vm_dict['entities'][0]['metadata']['uuid']

                    # creating new dictionary to update VM with
                    new_dict = {'metadata': vm_dict['entities'][0]['metadata'],
                                'spec': vm_dict['entities'][0]['spec']}

                    # Assigning the category to the metadata portion of new_dict
                    new_dict['metadata']['categories'][category_name] = category_value

                    # Updating the VM with the whole new_dict, which contains
                    # the new category
                    ans_return = nutanix_object.update_vm(api=nutanix.CENTRAL_API,
                                                          vm_uuid=vm_uuid,
                                                          vm_dict=new_dict)
                else:
                    ans_failure = "ERROR: VM {} not found!".format(vm)

            except Exception as e:
                ans_failure = "ERROR: {}".format(str(e))

    elif action == "find_vms_in_category":
        if not category_name:
            ans_failure = "Category Name is required!"
        if not ans_failure:
            try:
                if not category_value:
                    # run search without value in fiql
                    ans_return = nutanix_object.get_vms_in_category(category_name,
                                                                    category_value=None,
                                                                    api=nutanix.CENTRAL_API)
                    ans_changed = False
                    ans_failure = None
                else:
                    # run search with both category_name/value in fiql
                    ans_return = nutanix_object.get_vms_in_category(category_name,
                                                                    category_value,
                                                                    api=nutanix.CENTRAL_API)
                    ans_changed = False
                    ans_failure = None

            except Exception as e:
                ans_failure = "ERROR: No VMs returned: {}".format(str(e))
                ans_changed = False
                ans_return = None

    elif action == 'delete_vm':
        vm_return = nutanix_object.get_vm(api=nutanix.CENTRAL_API, vmname=vm)
        # vm_dict = nutanix_object.get_vms(api=nutanix.CENTRAL_API)
        # vm_exists, vm_details = get_vm_from_list(vm_dict, search=vm)
        if vm_return['entities']:
            vm_uuid = vm_return['entities'][0]['metadata']['uuid']
            try:
                ans_return = nutanix_object.delete_vms(api=nutanix.CENTRAL_API,
                                                       uuid=vm_uuid)
                ans_changed = True
            except requests.exceptions.RequestException as e:
                ans_failure = "VM Delete error: " + str(e)
                ans_return = None
                ans_changed = False

    elif action == 'get_project':
        ans_return = nutanix_object.get_project(api=nutanix.CENTRAL_API, proj_name=project)

    elif action == 'add_project':
        proj_exists = nutanix_object.get_project(api=nutanix.CENTRAL_API, proj_name=project)
        if proj_exists['metadata']['total_matches'] == 0:
            try:
                ans_return = nutanix_object.add_project(api=nutanix.CENTRAL_API, proj_name=project)
                ans_changed = True
            except requests.exceptions.RequestException as e:
                ans_failure = "Project create error: " + str(e)
                ans_return = None
                ans_changed = False
        else:
            ans_failure = "Project already exists"
            ans_changed = False
            ans_return = None

    if ans_failure is None:
        module.exit_json(changed=ans_changed, meta=ans_return)
    else:
        module.fail_json(msg=ans_failure,
                         changed=ans_changed,
                         meta=ans_return)


if __name__ == '__main__':
    main()
