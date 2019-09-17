from ansible.module_utils.basic import *
import re

def create_aggr_list(aggr_string):
    """
    This parses the aggr_string from the CLI and creates
    an aggregate list to sort, choose where to put
    the volume.

    aggr_string example:

        '<results xmlns="http://www.netapp.com/filer/admin" status="passed">
        <cli-output>
                                   \n\n\nAggregate     Size Available
                                   Used% State   #Vols  Nodes
        RAID Status\n-----

        - ------------\nw1ssinacl0101_aggr1_fsas 344.9TB 40.92TB 88% online 130\n
         w1ssinacl01-0'

    :param aggr_string:
    :return list of Netapp Aggregates:
    """
    # split string right before '-----\n' and take second index
    parse_dash_newline = aggr_string.split('-\\n')[1]

    # replace \n + space with empty character
    replace_new_line = parse_dash_newline.replace('\\n ', '')

    # split into a list and removing last 3 items.
    semi_draft_list = replace_new_line.split('\\n')[:-3]  # remove last 3 lines

    final_list = []
    for i in range(len(semi_draft_list)):
        # remove multiple white spaces in each index
        remove_white_space = re.sub(' +', ' ', semi_draft_list[i])

        # replace the last commas
        last_comma = remove_white_space.replace(',', '')

        # split the string of spaces into a list
        final_aggr_list = last_comma.split()

        aggr_dict = {
            'name': final_aggr_list[0],
            'size': final_aggr_list[1],
            'available': final_aggr_list[2],
            'used': final_aggr_list[3],
            'num_vols': final_aggr_list[5],
            'nodes': final_aggr_list[6]
        }
        final_list.append(aggr_dict)
    return final_list


def sort_aggr_list(aggr_list):
    """
    This sorts the aggr_list of dictionaries on the ['used'] key
    and puts the lowest valued of 'Used%' dictionary first.

    :param aggr_list:
    :return sorted_list of aggregates with least 'used' value first:
    """
    if not aggr_list or not len(aggr_list):
        ans_failure = "NO AGGREGATE OR EMPTY LIST"
    else:
        sorted_list = sorted(aggr_list, key=lambda i: i['used'], reverse=False)
        ans_failure = None
    return sorted_list, ans_failure


def create_vserver_list(vserver_string):
    """
    This is
    :param vserver_string:
    :return:
    """

    # remove the first 2 lines
    new_list = vserver_string.split('\\n')[3:]

    # remove the last 3 lines
    new_list = new_list[:-3 or None]

    vserver_list = []
    for i in range(len(new_list)):
        node_info = new_list[i].split()

        # Parsing out business unit code from column '0'
        # or 'vserver' column by splitting based on '_'
        bu_list = node_info[0].split('_')

        new_dict = {
            'vserver': node_info[0],
            'nb-name': node_info[1],
            'status': node_info[2],
            'domain': node_info[3],
            'authentication': node_info[4],
            # splitting column[1] based on '-' and first '0'
            # char - T, P, D, etc..
            'environment': node_info[1].split('-')[1][0],

            # Now using index of bu_list[1] because when we split above
            # it puts the business code in index 2 of the bu_list.
            # Testing if the length of list is greater than 1, then
            # else assign None.  This helps with index out of range errors
            # since some of your vserver names don't have '_3XXX'
            'business-unit': bu_list[1] if len(bu_list) > 1 else None

        }
        vserver_list.append(new_dict)
    return vserver_list


def format_vserver_list(vserver_string):
    """
    This is just to show part of the parsing that is
    done in the create_vserver_list() function.

    The view will be similar to a Netapp Cluster
    Console/SSH session by remove the first 2 lines.

    :param vserver_string:
    :return: Returns the view of the console via
    type 'string'
    """
    # just a function to display the results with a
    # basic format of splitting \n
    # remove the first 2 lines.
    # need two slashes as to escape '\'
    new_list = vserver_string.split('\\n')[3:]

    # remove the last 3 lines
    cli_view = new_list[:-3 or None]
    return cli_view


def search_vserver(environment,
                   business_unit, vserver_list):
    """
    This searches for the vserver using the parameters
    passed.

    :param domain:
    :param environment:
    :param business_unit:
    :param vserver_list:
    :return: Returns a dictionary of a found vserver
    """

    result = ""

    for i in range(len(vserver_list)):
        vservers = vserver_list[i]
        if environment == vservers['environment'] and \
            business_unit == vservers['business-unit']:
            result = vserver_list[i]
            break

    if not result:
        result = "NO VSERVERS FOUND!"
        return None, result
    else:
        return result, None


def parse_volume_output(volume_cli_output):
    """
    This is a basic parse to see if a volume exists

    :param volume_cli_output:
    :return parse_cli_output:
    """
    parse_cli_output = volume_cli_output.split('<cli-output>')[1]
    parse_cli_final = parse_cli_output.split('</cli')[0]
    return parse_cli_final


def main():
    """
    Ansible module template
    """

    module = AnsibleModule(
        argument_spec=dict(
            vserver_string=dict(required=False, type="str"),
            volume_cli_output=dict(required=False, type="str"),
            domain=dict(required=False, type="str"),
            environment=dict(required=False, type="str"),
            business_unit=dict(required=False, type="str"),
            aggr_string=dict(required=False, type="str"),
            action=dict(required=True, choices=[
                "create_vserver_list", "format_vserver",
                "search_vserver","get_aggregate",
                "parse_volume"
            ])
        ))

    # defining variables
    vserver_string = module.params["vserver_string"]
    volume_cli_output = module.params["volume_cli_output"]
    environment = module.params["environment"]
    domain = module.params["domain"]
    business_unit = module.params["business_unit"]
    aggr_string = module.params["aggr_string"]
    action = module.params["action"]

    ans_failure = None
    ans_changed = False
    ans_return = None

    if action == "parse_volume":
        if not volume_cli_output:
            ans_failure = "NO VOLUME_CLI_OUTPUT PASSED!"
        else:
            volume_parsed = parse_volume_output(volume_cli_output)
            ans_return = volume_parsed
            ans_failure = None

    if action == "search_vserver":
        if not environment or \
                not business_unit or \
                not vserver_string:
            ans_failure = "NO VSERVER STRING " \
                          "OR ENV OR BU PASSED!"
        else:
            vserver_list = create_vserver_list(vserver_string)
            ans_return, ans_failure = search_vserver(environment,
                                            business_unit, vserver_list)

    if action == "format_vserver":
        if not vserver_string:
            ans_failure = "NO VSERVER STRING PASSED!"
        else:
            vserver_format = format_vserver_list(vserver_string)
            ans_return = vserver_format

    if action == "get_aggregate":
        if not aggr_string:
            ans_failure = "NO AGGREGATE STRING PASSED!"
        else:
            try:
                aggr_list = create_aggr_list(aggr_string)
                sorted_aggr_list, ans_failure = sort_aggr_list(aggr_list)
                ans_return = sorted_aggr_list
                ans_changed = False
            except Exception as e:
                ans_failure = "PROBLEM WITH LIST! Error {}".format(str(e))
                ans_return = None
                ans_changed = False

    if action == "create_vserver_list":
        if not vserver_string:
            ans_failure = "NO VSERVER STRING PASSED!"
        else:
            ans_return = create_vserver_list(vserver_string)

    if ans_failure is None:
        module.exit_json(changed=ans_changed, meta=ans_return)
    else:
        module.fail_json(msg=ans_failure,
                         changed=ans_changed,
                         meta=ans_return)
        

if __name__ == '__main__':
    main()

