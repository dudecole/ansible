#!/usr/bin/python
#
#
from ansible.module_utils.basic import *
import solarwinds
import requests


def list_node(node_list, node_name=None):
    """
    :param node_list:
    :param node_name: Name to search for
    :return: Found and/or not found dictionary of nodes
    """

    found_node_list = []

    if not node_name:
        return "no node name entered", None
    else:
        for i in range(len(node_list['results'])):
            if node_name in node_list['results'][i]['NodeName']:
                found_node_dict = {
                    'nodename': node_list['results'][i]['NodeName'],
                    'ip': node_list['results'][i]['IPAddress'],
                    'nodeid': node_list['results'][i]['NodeID']
                }
                found_node_list.append(found_node_dict)

    if not found_node_list:
        return "No item was found", None
    else:
        return None, {'matched': found_node_list}


def main():
    """
    Ansible module template
    """

    module = AnsibleModule(
        argument_spec=dict(
            node_name=dict(required=False, type="str"),
            solar_host=dict(required=True, type="str"),
            solar_user=dict(required=True, type="str"),
            solar_pw=dict(required=True, type="str"),
            ip=dict(required=False,type="str"),
            action=dict(required=True, choices=[
                "add_node","delete_node","get_node"
            ])
        ))

    #creating variables
    node_name = module.params["node_name"]
    solar_host = module.params["solar_host"]
    solar_user = module.params["solar_user"]
    solar_pw = module.params["solar_pw"]
    ip = module.params["ip"]
    action = module.params["action"]

    ans_failure = None
    ans_return = {}
    ans_changed = False

    solar_instance = solarwinds.Solarwinds(hostname=solar_host,
                                           username=solar_user,
                                           password=solar_pw,
                                           verify=False)

    if action == "add_node":
        if (not ip) or (not node_name):
            ans_failure = "No IP Address or Node Name given"
            ans_return = None
        else:
            try:
                found_node = solar_instance.get_node(ip_address=ip)
                if found_node['results']:
                    ans_failure = "Solarwinds node " \
                                  "already exists!"
                    ans_changed = False
                else:
                    solar_instance.add_node(node_name=node_name,
                                            ip_address=ip)

                    ans_return = "successfully added " + ip + \
                                 " to " + solar_host
                    ans_changed = True

            except requests.exceptions.RequestException as e:
                ans_failure = "unable to add record: " + str(e)
                ans_return = None
                ans_changed = False

    elif action == "get_node":
        if not ip:
            ans_failure = "No IP address given"
        else:
            try:
                ans_return = solar_instance.get_node(ip_address=ip)
                if not ans_return['results']:
                    ans_failure = "Unable to find Solarwinds " \
                                  "Node with IP"

            except requests.exceptions.RequestException as e:
                ans_failure = "unable to find record: " + str(e)
                ans_return = None
                ans_changed = False

    elif action == "delete_node":
        if not ip:
            ans_failure = "No IP address given"
        else:
            try:
                found_node = solar_instance.get_node(ip_address=ip)

                if len(found_node['results']) >= 1:
                    solar_instance.delete_node(ip_address=ip)
                    ans_return = "Node IP: " + ip + \
                                 " successfully deleted!"
                    ans_changed = True
                else:
                    ans_failure = "No Node with ip: " + \
                                  ip + " found!"
                    ans_changed = False

            except requests.exceptions.RequestException as e:
                ans_failure = "unable to delete the node: " + str(e)
                ans_return = None
                ans_changed = False

    if ans_failure is None:
        module.exit_json(changed=ans_changed, meta=ans_return)
    else:
        module.fail_json(msg=ans_failure,
                         changed=ans_changed,
                         meta=ans_return)


if __name__ == '__main__':
    main()

