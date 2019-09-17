#!/usr/bin/python

from ansible.module_utils.basic import *
import infoblox
import os
import json
from netaddr import IPNetwork


def get_subnet_ips(network_list):
    """
    ToDO - Verify if this function is even needed.

    Function that calls the infoblox library to get all the IPs in the subnet
    and returns all the extensible attributes of each IP address (which aren't
    being inherited from parent correctly) and also includes all the details
    needed to check the IP status

    :param network:
    :return:
    """
    if not network_list:
        print("no network entered")
        ans_return = "no network entered"
    else:
        ans_return = json.dumps(network_list, indent=4)
    return ans_return


def add_host_record(network, instance, fqdn):
    """
    Calls the infoblox.create_host_record() method

    :param network: 10.x.x.x/24 format
    :param instance: object initialized in main
    :param fqdn:
    :return: next_ip address returned
    """
    if not network or not fqdn:
        return "no network or fqdn entered", None

    record = instance.create_host_record(network, fqdn)
    next_ip = record[0]['ipv4addrs'][0]['ipv4addr']

    return next_ip


def get_vlan_id(network):
    """
    Function that calls infoblox library to get the network information and
    parses out the return from the library.

    :param network:
    :return: returns VLAN ID Number

    """

    if not network:
        print("no network entered")
        vlan_id = "no network entered"
    else:
        vlan_id = network[0]['extattrs']['VLAN']['value']
    return vlan_id


def ping_ip(ip_address):
    """Function that validates that an IP is not in use"""

    response = os.system("ping -n 1 " + ip_address)
    # checking response, returning 1 if in use or 0 if not
    if response == 0:
        # ip in use
        ping_status = 1
    else:
        # ip available
        ping_status = 0
    return ping_status


def main():
    """
    Ansible module template
    """

    module = AnsibleModule(
        argument_spec=dict(
            ip_address=dict(required=False, type="str"),
            vrf=dict(required=False, type="str"),
            environment=dict(required=False, type="str"),
            subnet=dict(required=False, type="str"),
            site=dict(required=False, type="str"),
            ib_host=dict(required=True, type="str"),
            network_zone=dict(required=False, type="str"),
            version=dict(required=False, type="str"),
            ib_user=dict(required=True, type="str"),
            ib_pw=dict(required=True, type="str"),
            fqdn=dict(required=False, type="str"),
            action=dict(required=True, choices=[
                "ping_ip","get_network",
                "get_subnet_ips","get_vlan",
                "get_next_ip","get_gateway",
                "add_host_record", "get_netmask",
                "get_ip_status"
            ])
        ))

    # creating ansible parameters to variables
    subnet = module.params["subnet"]
    ip_address = module.params["ip_address"]
    vrf = module.params["vrf"]
    environment = module.params["environment"]
    site = module.params["site"]
    ib_host = module.params["ib_host"]
    ib_user = module.params["ib_user"]
    ib_pw = module.params["ib_pw"]
    network_zone = module.params["network_zone"]
    version = module.params["version"]
    fqdn = module.params["fqdn"]

    # assigning action dictionary to action variable
    action = module.params["action"]

    ans_return = {}
    ans_failure = None
    ans_changed = False

    # instantiate class
    ib_instance = infoblox.InfoBlox(ib_host=ib_host, user=ib_user, pw=ib_pw)

    if action == "get_ip_status":
        # this will search for an IP address and return the whole network/prefix
        if not ip_address:
            ans_failure = "no IP address was entered"
        else:
            try:
                ip_status = ib_instance.get_ip_properties(ip_address)
                ans_return = ip_status
            except Exception as e:
                ans_failure = "IP Address {} not found: ".format(str(e))
                ans_return = None
                ans_changed = False

    if action == "ping_ip":
        if not ip_address:
            ans_failure = "no IP address was entered"
        else:
            ans_return = ping_ip(ip_address)

    if action == "get_netmask":
        if not subnet:
            ans_failure = "no network passed"
        else:
            subnet_obj = IPNetwork(subnet)
            ans_return = str(subnet_obj.netmask)

    if action == "get_network":
        # need to also test against Prod or Non Prod not existing
        if site is None or environment is None or network_zone is None:
            ans_failure = "Please enter site, env, and zone"
        else:
            network = ib_instance.get_bu_network(vrf=vrf, site=site, env=environment,
                                             zone=network_zone, version=version)

        if not network:
            network = ib_instance.get_bu_network(site=site, env=environment)
            ans_return = network[0]['network']

        else:
            ans_return = network[0]['network']

    if action == "get_vlan":
        if not subnet:
            ans_failure = "Missing subnet"
        else:
            subnet_details = ib_instance.get_subnet_details(subnet)
            ans_return = get_vlan_id(subnet_details)

    if action == "get_subnet_ips":
        if not subnet:
            ans_failure = "Missing subnet"
        else:
            network_ips = ib_instance.get_network_details(subnet)
            ans_return = get_subnet_ips(network_ips)

    if action == "add_host_record":
        if not subnet:
            ans_failure = "Missing subnet for get_next_ip"
        else:
            # network_ips = ib_instance.get_network_details(subnet)
            next_ip = add_host_record(subnet, ib_instance, fqdn)
            if next_ip is None:
                ans_failure = "not available"
            else:
                ans_return = next_ip

    if ans_failure is None:
        module.exit_json(changed=False, meta=ans_return)
    else:
        module.fail_json(changed=ans_changed, meta=ans_return, msg=ans_failure)


if __name__ == '__main__':
    main()