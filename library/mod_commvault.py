from ansible.module_utils.basic import *
import commvault
import xml.etree.ElementTree as ET


def parse_license_props(license_response):
    """
    Parses out all the necessary XML values and stores into
    client properties variables.

    :param client_response:
    :return Dictionary of K,V variable values of license properties:
    """

    return_my_dict_please = {}
    license = ET.fromstring(license_response)
    license_info = license.findall(".//licensesInfo")

    if not license_info:
        ans_failure = "no active license element/node"
    else:
        platform_type = license_info[0].attrib["platformType"]
        license = license.findall(".//license")
        app_type = license[0].attrib["appType"]
        license_type = license[0].attrib["licenseType"]
        license_name = license[0].attrib["licenseName"]

        return_my_dict_please = {
            "app_type":app_type,
            "license_type":license_type,
            "license_name":license_name,
            "platform_type":platform_type
        }
        ans_failure = None

    return return_my_dict_please, ans_failure


def parse_client_props(client_response):
    """
    Parses out all the necessary XML values and stores into variables
    client properties variables.

    :param client_response:
    :return Returns dictionary of K,V variable values:
    """
    return_my_dict_please = {}

    client = ET.fromstring(client_response)
    activePhysicalNode = client.findall(".//ActivePhysicalNode")
    if not activePhysicalNode:
        ans_failure = "no 'ActivePhysicalNode': " \
                      "CLIENT NOT FOUND"
    else:
        # this is to parse out the client properties
        client_entity = client.findall(".//client/clientEntity")
        client_name = client_entity[0].attrib["clientName"]
        client_id = client_entity[0].attrib["clientId"]
        hostname = client_entity[0].attrib["hostName"]
        client_guid = client_entity[0].attrib["clientGUID"]
        commcell_name = client_entity[0].attrib["commCellName"]

        # this is to parse out the client description and displayname
        client_comments = client.findall(".//clientProperties/client")
        client_description = client_comments[0].attrib["clientDescription"]
        client_display_name = client_comments[0].attrib["displayName"]

        return_my_dict_please = {
            "client_id": client_id,
            "client_guid": client_guid,
            "host_name": hostname,
            "client_name": client_name,
            "commcell_name": commcell_name,
            "client_description": client_description,
            "client_display_name": client_display_name
        }
        ans_failure = None

    return return_my_dict_please, ans_failure


def main():
    """
    Ansible module template
    """

    module = AnsibleModule(
        argument_spec=dict(
            client=dict(required=False, type="str"),
            username=dict(required=True, type="str"),
            password=dict(required=True, type="str"),
            client_id=dict(required=False, type="str"),
            commserve=dict(required=True, type="str"),
            action=dict(required=True, choices=[
                "search_client_id","search_client_name",
                "get_client_list", "unlicense_client",
                "get_client_license"
            ])
        ))

    # creating variables
    client = module.params["client"]
    client_id = module.params["client_id"]
    commserve = module.params["commserve"]
    username = module.params["username"]
    password = module.params["password"]
    action = module.params["action"]

    ans_return = {}
    ans_failure = None
    ans_changed = False

    try:
        comm_obj = commvault.CommvaultClient(commserve,
                                             username,
                                             password)
    except Exception as e:
        ans_failure = "Connection failure: {}".format(str(e))
        module.fail_json(msg=ans_failure,
                         changed=ans_changed,
                         meta=ans_return)

    if action == "search_client_id":
        if not client_id:
            ans_failure = "no client_id was passed"
        else:
            try:
                client_response = comm_obj.search_client_id(client_id)
                ans_return, ans_failure = parse_client_props(client_response)
                ans_changed = False
            except Exception as e:
                ans_failure = "Client ID {} not found: ".format(str(e))
                ans_return = None
                ans_changed = False

    if action == "search_client_name":
        if not client:
            ans_failure = "no client name was passed"
        else:
            try:
                client_response = comm_obj.search_client_name(client)
                ans_return, ans_failure = parse_client_props(client_response)
                ans_changed = False
            except Exception as e:
                ans_failure = "Client Name {} not found: ".format(str(e))
                ans_return = None
                ans_changed = False

    if action == "get_client_list":
        try:
            ans_return, ans_failure = comm_obj.get_client_list()
            ans_changed = False
        except Exception as e:
            ans_failure = "Client list not returned: " + str(e)
            ans_return = None
            ans_changed = False

    if action == "get_client_license":
        if not client:
            ans_failure = "no client name was passed"
        else:
            try:
                client_response = comm_obj.search_client_name(client)
                client_props, ans_failure = parse_client_props(client_response)

                if ans_failure:
                    module.fail_json(changed=ans_changed, msg=ans_failure)
                else:
                    license_xml = comm_obj.get_client_license(client_props['client_id'])
                    ans_return, ans_failure = parse_license_props(license_xml)

                    if ans_failure:
                        # if no license is found - 'meta=False'.  This allows a
                        # proper exit for decommission.
                        module.exit_json(meta=False, msg=ans_failure)
                    ans_changed = False

            except Exception as e:
                ans_failure = "Client Name {} not found: " \
                              "Encountered ERROR {}".format(client, str(e))
                ans_return = None
                ans_changed = False

    if action == "unlicense_client":
        if not client:
            ans_failure = "no client name passed"
            ans_changed = False
        else:
            try:
                client_response = comm_obj.search_client_name(client)
                client_props, ans_failure = parse_client_props(client_response)
                license_xml = comm_obj.get_client_license(client_props['client_id'])
                license_props, ans_failure = parse_license_props(license_xml)
                license_response = comm_obj.unlicense_client(client_props['client_name'],
                                                             int(license_props['app_type']),
                                                             int(license_props['platform_type']),
                                                             license_props['license_name'])

                ans_return = license_response
                ans_changed = True

            except Exception as e:
                ans_failure = "Client Name {} not found: " \
                              "Encountered ERROR {}".format(client, str(e))
                ans_return = None
                ans_changed = False

    if not ans_failure:
        module.exit_json(changed=ans_changed, meta=ans_return)
    else:
        module.fail_json(msg=ans_failure,
                         changed=ans_changed,
                         meta=ans_return)


if __name__ == '__main__':
    main()
