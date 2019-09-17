#!/usr/bin/python
#
#
from ansible.module_utils.basic import *
import servicenow
import json
import requests

def main():

    module = AnsibleModule(
        argument_spec=dict(
            ritm_number=dict(required=False, type="str"),
            ip_address=dict(required=False, type="str"),
            snow_user=dict(required=True, type="str"),
            snow_pw=dict(required=True, type="str"),
            snow_instance=dict(required=True, type="str"),
            vlan_id=dict(required=False, type="str"),
            ritm_sysid=dict(required=False, type="str"),
            vlan_sysid=dict(required=False, type="str"),
            action=dict(required=True, choices=[
                "set_ritm_vars", "get_ritm", "close_ip",
                "close_dns","close_vm_create",
                "close_prep","close_db","get_vlan_sysid",
                "get_current_stage","close_rsh","close_backup",
                "get_requester_info"
            ])
        ))

    ritm_sysid = module.params["ritm_sysid"]
    ip_address = module.params["ip_address"]
    vlan_id = module.params["vlan_id"]
    ritm_number = module.params["ritm_number"]
    action = module.params["action"]
    snow_user = module.params["snow_user"]
    snow_pw = module.params["snow_pw"]
    snow_instance = module.params["snow_instance"]
    vlan_sysid = module.params["vlan_sysid"]

    # snow_instance configured in dev_ and prod_ vaults, respectively
    # "test" set in dev_vault (env=dev), "prod" set in prod_vault (env=prod)
    if snow_instance == "prod":
        snow_instance = servicenow.PROD
    else: # default to test
        snow_instance = servicenow.TEST

    snowreq = servicenow.NVSRequest(snow_user, snow_pw, snow_instance, ritm_number)

    if snowreq.number is None:
        module.fail_json(changed=False, msg="No workable tickets in queue", meta={})
    
    response = snowreq.get_request_vars()
    ritm_dict = response.json()

    ans_failure = None
    ans_return = {}
    ans_changed = False

    if action == "get_ritm":
        ans_return = servicenow.get_ritm(snowreq, ritm_dict)

    elif action == "get_vlan_sysid":
        if not vlan_id:
            ans_failure = "No VLAN ID was passed"
        else:
            vlan_name = 'VLAN_' + vlan_id
            try:
                vlan_sysid = servicenow.get_vlan_sysid(snowreq,vlan_name)
                if not vlan_sysid['result']:
                    # ['result'][0]['sys_id']
                    ans_failure = "VLAN_ID: " + vlan_id + \
                            " was not found in Servicenow CMDB"
                    ans_return = None
                else:
                    ans_return = {"sys_id": vlan_sysid['result'][0]['sys_id'],
                                  "name": vlan_name}
                    ans_failure = None
                    ans_changed = None
                    
            except requests.RequestException as e:
                ans_failure = "unable to find VLAN SysID" + str(e)
                ans_return = None

    elif action == "set_ritm_vars":
        if not vlan_sysid or not ip_address:
            ans_failure = "No VLAN passed here man"
            ans_return = None
        else:
            try:
                update_result = snowreq.update_vars({'vm_ip': ip_address,
                                              'vm_vlan': vlan_sysid})
                ans_return = {'update_result':str(update_result)}
                ans_changed = True
            except requests.RequestException as e:
                ans_failure = "Unable to update ticket with IP:" + \
                    ip_address + "OR VLAN: " + vlan_id + "error: " + \
                    str(e)
                ans_changed = False

    elif action == "get_current_stage":
        ans_return = snowreq.get_current_stage()

    elif action == "close_ip":
        ans_return = snowreq.close_stage(servicenow.STAGE_IP_ASSIGN)

    elif action == "close_dns":
        ans_return = snowreq.close_stage(servicenow.STAGE_DNS_ENTRY)

    elif action == "close_prep":
        ans_return = snowreq.close_stage(servicenow.STAGE_OS_PREP)

    elif action == "close_vm_create":
        ans_return = snowreq.close_stage(servicenow.STAGE_VM_CREATE)

    elif action == "close_rsh":
        ans_return = snowreq.close_stage(servicenow.STAGE_RSH)

    elif action == "close_backup":
        ans_return = snowreq.close_stage(servicenow.STAGE_BACKUP_CONFIG)

    elif action == "get_requester_info":
        if not ritm_number:
            ans_failure = "missing ritm"
            ans_return = None
        else:
            try:
                clientreq = servicenow.Client(snow_user, snow_pw, snow_instance)
                ticket_vars = servicenow.get_requester_info(clientreq, ritm_number)
                ans_return = ticket_vars
            except requests.RequestException as e:
                ans_failure = "unable to get ticket vars" + str(e)

    if ans_failure is None:
        module.exit_json(changed=ans_changed, meta=ans_return)
    else:
        module.fail_json(changed=ans_changed,
                         meta=ans_return,
                         msg=ans_failure)


if __name__ == '__main__':
    main()

