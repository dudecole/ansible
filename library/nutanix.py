"""
This library contains classes and functions for communicating with
the Nutanix Prism Central and Prism Element API.  Prism Central is at
v3 and Prism Element is at v2 for API versions.

The actions and methods of the Prism Central can change more global settings
hence the need for the Prism Element API for more granular changes to clusters,
hosts, and vms.

Todo: - Function to get a VM uuid
      - Log file functionality
            - Try/Catch blocks, with errors written to log file

Documentation: pydoc ./nutanix.py

Contact: DCole
         dudecole@outlook.com
"""
import json
import requests
requests.packages.urllib3.disable_warnings()

HTTPS = 'https://'

CENTRAL_API = '/api/nutanix/v3/'
ELEMENT_API = '/PrismGateway/services/rest/v2.0/'


class NutanixException(Exception):
    pass

# Stuff for FIQL queries
class FiqlOutOfBoundsException(NutanixException):
    pass

def fiql_upper_bound(lower_bound):

    if len(lower_bound) <= 0:
        raise FiqlOutOfBoundsException("String given was empty")

    # This does NOT work for non-ascii. Sorry kids
    pivot_ord = ord(lower_bound[-1])
    if pivot_ord >= 126 or pivot_ord < 32:
        raise FiqlOutOfBoundsException("Character not ascii: " + lower_bound[-1])

    increm = chr(ord(lower_bound[-1])+1)
    return lower_bound[0:-1] + increm

def fiql_query_like(key, prefix):
    '''
    Generates a FIQL query that works with Nutanix which will allow us to query
    for all items with <key> values that share some string prefix.

    This can be used, e.g. to find all VMs that have similar names:
    fiql_query_like('vm_name', '1982-ssmngo-t') returns a FIQL query for all
    VMs with names that start with the string '1982-ssmngo-t'.
    '''

    return '{key}=ge={lower_bound};{key}=lt={upper_bound}'.format(
        key=key,
        lower_bound=prefix,
        upper_bound=fiql_upper_bound(prefix))


class Nutanix:

    def __init__(self, username='gus', password='chiggins', port='9440',
                 central_addr=None, element_addr=None):

        self.username = username
        self.password = password
        self.port = port
        self.central_addr = central_addr
        self.element_addr = element_addr
        self.start_auth = self._begin_connection(api=CENTRAL_API)

    def _begin_connection(self, api=CENTRAL_API):
        """
        This is just to begin a connection to the nutanix api for the initialization
        of the object/class in the mod_nutanix.py file.

        :param api:
        :return:
        """

        url = HTTPS + self.central_addr + ':' + self.port + api + 'clusters/list'
        my_headers = {'Content-type': 'application/json',
                      'Accept': 'application/json',
                      'Authorization': 'Basic'}
        d = '{}'
        r = requests.post(url,
                          data=d,
                          auth=(self.username, self.password),
                          headers=my_headers,
                          verify=False
                          )
        r.raise_for_status()
        return r.json()

    def get_hosts(self, api=ELEMENT_API):
        """
        Gets all the hosts json data
        :param api:
        :return: host json data
        """
        url = HTTPS + self.element_addr + ':' + self.port + api + 'hosts/'
        my_headers = {'Content-type': 'application/json',
                      'Accept': 'application/json',
                      'Authorization': 'Basic'}
        r = requests.get(url,
                         auth=(self.username, self.password),
                         headers=my_headers,
                         verify=False
                         )

        r.raise_for_status()
        return r.json()

    def get_networks(self, api=ELEMENT_API):
        '''returns list of dictionaries of networks'''

        # this is calling the prism element API of v2.0

        url = HTTPS + self.element_addr + ':' + self.port + api + 'networks/'
        my_headers = {'Content-type': 'application/json',
                      'Accept': 'application/json',
                      'Authorization':'Basic'}
        r = requests.get(url,
                         auth=(self.username, self.password),
                         headers=my_headers,
                         verify=False
                         )

        r.raise_for_status()
        return r.json()

    def add_network(self, api=ELEMENT_API, network_name=None, vlan_id=None):
        """
        Adds a VLAN to the cluster

        :param api: Prism Element v2 api URI
        :param network_name: VLAN_1234
        :param vlan_id: Integer that is converted to str(vlan_id) due to
        string concatenation
        :return: {'network_uuid': 'xxxxx-xxx-xxx-xxx-xxxxx'}

        """

        url = HTTPS + self.element_addr + ':' + self.port + api + 'networks/'
        my_headers = {'Content-type': 'application/json',
                      'Accept': 'application/json',
                      'Authorization':'Basic'}

        d = '{"name":' + '"' + network_name + '",' + \
            '"vlan_id":' + str(vlan_id) + \
            '}'

        r = requests.post(url,
                          data=d,
                          auth=(self.username, self.password),
                          headers=my_headers,
                          verify=False
                          )

        r.raise_for_status()
        return r.json()

    def get_cluster_w_uuid(self, api=ELEMENT_API, cluster_uuid=None):
        """

        This uses the prism element (cluster API of V2) to
        query for a cluster with a UUID.  This returns a cluster's dictionary.

        The URI is
        https://10.60.114.23:9440/api/nutanix/v2.0/clusters/{id}

        :param api:
        :param cluster_uuid:
        :return:
        """
        url = HTTPS + self.central_addr + ':' + \
              self.port + api + 'clusters/' + \
              cluster_uuid

        my_headers = {'Content-type': 'application/json',
                      'Accept': 'application/json',
                      'Authorization': 'Basic'}

        r = requests.get(url,
                         auth=(self.username, self.password),
                         headers=my_headers,
                         verify=False
                         )
        r.raise_for_status()
        return r.json()

    def get_cluster_element(self, api=ELEMENT_API):
        """
        This is because nutanix has a different api for the
        the cluster level.  Instead of a 'post' it is a 'get'
        and i'm calling it get_cluster_element because each cluster
        has its own 'prism element'.

        This can be used to get the cluster 'stats' AND 'usage_stats'

        :param api:
        :return:
        """

        url = HTTPS + self.element_addr + ':' + self.port + api + 'clusters/'
        my_headers = {'Content-type': 'application/json',
                      'Accept': 'application/json',
                      'Authorization':'Basic'}

        r = requests.get(url,
                           auth=(self.username, self.password),
                           headers=my_headers,
                           verify=False)

        r.raise_for_status()
        return r.json()

    def get_cluster(self, api=CENTRAL_API):
        '''returns list of dictionaries of clusters'''

        url = HTTPS + self.central_addr + ':' + self.port + api + 'clusters/list'
        my_headers = {'Content-type': 'application/json',
                      'Accept': 'application/json',
                      'Authorization':'Basic'}
        d = '{}'
        r = requests.post(url,
                          data=d,
                          auth=(self.username, self.password),
                          headers=my_headers,
                          verify=False
                          )
        r.raise_for_status()
        return r.json()

    def get_vms(self, api=CENTRAL_API):

        url = HTTPS + self.central_addr + ':' + self.port + api + 'vms/list'
        my_headers = {'Content-type': 'application/json',
                      'Accept': 'application/json',
                      'Authorization':'Basic'}

        total_vms = self.get_vms_length(api=CENTRAL_API)

        d = '{"length":' + str(total_vms) + '}'
        r = requests.post(url,
                           data=d,
                           auth=(self.username, self.password),
                           headers=my_headers,
                           verify=False)

        r.raise_for_status()
        return r.json()

    def get_vms_length(self, api=CENTRAL_API):

        my_headers = {'Content-type': 'application/json',
                      'Accept': 'application/json',
                      'Authorization':'Basic'}
        url = HTTPS + self.central_addr + ':' + self.port + api + 'vms/list'
        r = requests.post(
            url=url,
            data='{}',
            auth=(self.username, self.password),
            headers=my_headers,
            verify=False
        )

        r.raise_for_status()
        vmlist_metadata = r.json()
        return vmlist_metadata['metadata']['total_matches']

    def delete_vms(self, api=CENTRAL_API, uuid=None):
        my_headers = {
                'Accept': 'application/json',
                'Authorization':'Basic'
                }
        url = ''.join([HTTPS,
                       self.central_addr,
                       ':',
                       self.port,
                       api,
                       'vms/',
                       uuid])
        r = requests.delete(
            url=url,
            auth=(self.username, self.password),
            headers=my_headers,
            verify=False
        )

        r.raise_for_status()
        return r.json()

    def get_project(self, api=CENTRAL_API, proj_name='default'):
        """
        This searches for a project based on a name.  If no name is used
        then it will assign the 'default' string to search for the
        default project.

        proj_name:
            This assumes the projects on nutanix are all in lowercase

        The data format is as follows:
        data = {"filter":"name==default","kind": "project"}
        :param api:
        :param proj_name:
        :return:
        """
        my_headers = {
                'Content-type': 'application/json',
                'Accept': 'application/json',
                'Authorization':'Basic'
                }
        url = ''.join([HTTPS,
                       self.central_addr,
                       ':',
                       self.port,
                       api,
                       'projects/list'])

        data = '{"filter":' + '"name==' + proj_name + '"' + \
               ',"kind": "project"}'

        r = requests.post(
            url=url,
            data=data,
            auth=(self.username, self.password),
            headers=my_headers,
            verify=False
        )

        r.raise_for_status()
        return r.json()

    def add_project(self, api=CENTRAL_API, proj_name='default'):
        # this should be put in the module and this should be a
        # basic - PROJECTS ARE ONLY USED WITH NUTANIX 'CALM'
        """
            This function checks to see if a projects exists, and
            if it doesn't exist, then it creates one.

            It returns the task for creating the new project OR
            It returns the dictionary saying project exists with
            a project uuid to use.

        :param api:
        :param proj_name:
        :return: returns the task in JSON format OR
                 a dictionary with the pre-existing project uuid
        """

        my_headers = {
                'Content-type': 'application/json',
                'Accept': 'application/json',
                'Authorization':'Basic'
                }
        url = ''.join([HTTPS,
                       self.central_addr,
                       ':',
                       self.port,
                       api,
                       'projects'])

        data = '{' + \
               '"spec":' + '{' + \
                   '"name":' + '"' + proj_name + '",' + \
                   '"resources":' + '{},' + \
                   '"description":"' + proj_name + '"' + \
               '},' + \
               '"metadata": {' + \
                   '"kind":"project"' + \
               '}}'

        # search for the project before trying to create it
        # does it allow for duplicates is this why i wrote it
        # this way?
        proj_exists = self.get_project(api=CENTRAL_API,proj_name=proj_name)

        if not proj_exists['entities']:
            r = requests.post(
                url=url,
                data=data,
                auth=(self.username, self.password),
                headers=my_headers,
                verify=False
            )
            r.raise_for_status()
            return_proj = r.json()

        else:
            # this should be changed dude. Why did i..
            # keep as generic json return instead of dict stuff
            proj_uuid = proj_exists['entities'][0]['metadata']['uuid']
            return_proj = {'status': 'FAILURE',
                           'msg':'project: ' + proj_name + ' already exists.',
                           'metadata':{'uuid': proj_uuid}}

        return return_proj

    def get_task(self, api=CENTRAL_API, task_uuid=None):
        """
            Function to return the task information.  Can be used
            to check if a task is complete before continuing.

        :param api:
        :param task_uuid:
        :return: JSON response for the task
        """

        my_headers = {
                'Content-type': 'application/json',
                'Accept': 'application/json',
                'Authorization':'Basic'
                }

        url = ''.join([HTTPS,
                       self.central_addr,
                       ':',
                       self.port,
                       api,
                       'tasks/' + task_uuid])

        r = requests.get(url,
                         auth=(self.username, self.password),
                         headers=my_headers,
                         verify=False
                         )

        r.raise_for_status()
        return r.json()

    def get_vm_w_uuid(self,api=CENTRAL_API,vm_uuid=None):
        """
            This is another function to find the VM by its UUID.
        :param api:
        :param vm_uuid:
        :return: JSON response for the VM.
        """
        my_headers = {
            'Content-type': 'application/json',
            'Accept': 'application/json',
            'Authorization': 'Basic'
        }

        url = ''.join([HTTPS,
                       self.central_addr,
                       ':',
                       self.port,
                       api,
                       'vms/' + vm_uuid])

        r = requests.get(url,
                         auth=(self.username, self.password),
                         headers=my_headers,
                         verify=False
                         )

        r.raise_for_status()
        return r.json()

    def _get_vms_like(self, vmname_prefix, api=CENTRAL_API):
        url = HTTPS + self.central_addr + ':' + self.port + api + 'vms/list'
        my_headers = {'Content-type': 'application/json',
                      'Accept': 'application/json',
                      'Authorization': 'Basic'}

        fiql_filter = fiql_query_like('vm_name', vmname_prefix)
        d = '{"filter":"' + fiql_filter + '"}'

        r = requests.post(url,
                          data=d,
                          auth=(self.username, self.password),
                          headers=my_headers,
                          verify=False)
        r.raise_for_status()
        return r.json()

    def get_vms_like(self, vmname_prefix, api=CENTRAL_API):

        if vmname_prefix is None or len(vmname_prefix) <= 0:
            return None

        lower_results = self._get_vms_like(api=api, vmname_prefix=vmname_prefix.lower())
        upper_results = self._get_vms_like(api=api, vmname_prefix=vmname_prefix.upper())

        returned_entities = []

        if lower_results['entities']:
            returned_entities.extend(lower_results['entities'])

        if upper_results['entities']:
            returned_entities.extend(upper_results['entities'])

        results = {'entities': returned_entities }

        return results

    def _get_vm(self, api=CENTRAL_API, vmname=None):
        url = HTTPS + self.central_addr + ':' + self.port + api + 'vms/list'
        my_headers = {'Content-type': 'application/json',
                      'Accept': 'application/json',
                      'Authorization': 'Basic'}

        d = '{"filter":"vm_name==' + vmname + '"}'

        r = requests.post(url,
                          data=d,
                          auth=(self.username, self.password),
                          headers=my_headers,
                          verify=False)

        r.raise_for_status()
        return r.json()

    def get_vm(self, api=CENTRAL_API, vmname=None):

        if vmname is None:
            return None

        results = self._get_vm(api=api, vmname=vmname.lower())

        if results['entities']:
            return results

        results = self._get_vm(api=api, vmname=vmname.upper())

        return results

    def update_vm(self, api=CENTRAL_API, vm_uuid=None, vm_dict=None):
        """
            This function requires vm_uuid and vm_dict.

            vm_dict: this contains the 'spec' and 'metadata' and is
                    converted into a json string with json.dumps.  This is to
                    prepare the dictionary to be used as a json string for the
                    'PUT' method - to update the VM.

            vm_uuid: self explanatory...  ;)

        :param api:
        :param vm_uuid:
        :param vm_dict:
        :return: returns JSON response from a successful run OR
                a dictionary from a failure - Maybe change this to
                be a JSON response for both.  Keep it consistent
        """

        data = {}
        vm_return = {}
        if not vm_dict or not vm_uuid:
            # Why did i do this - keep it json please
            vm_return = (json.loads(json.dumps({'metadata': 'failure',
                                                'spec': 'no VM UUID or VM Dict passed'})))

        else:
            my_headers = {
                'Content-type': 'application/json',
                'Accept': 'application/json',
                'Authorization': 'Basic'
            }
            url = ''.join([HTTPS,
                           self.central_addr,
                           ':',
                           self.port,
                           api,
                           'vms/' + vm_uuid])

            data = json.dumps(vm_dict)
            r = requests.put(
                url=url,
                data=data,
                auth=(self.username, self.password),
                headers=my_headers,
                verify=False
            )
            r.raise_for_status()
            vm_return = r.json()

        return vm_return

    def get_category(self, category_name, api=CENTRAL_API):
        """
            This is to find the Category by its name.

        :param category_name:
        :param api:
        :return:
        """
        my_headers = {
            'Content-type': 'application/json',
            'Accept': 'application/json',
            'Authorization': 'Basic'
        }

        url = ''.join([HTTPS,
                       self.central_addr,
                       ':',
                       self.port,
                       api,
                       'categories/' + category_name])

        r = requests.get(url,
                         auth=(self.username, self.password),
                         headers=my_headers,
                         verify=False
                         )

        r.raise_for_status()
        return r.json()

    def get_category_values(self, category_name, api=CENTRAL_API):
        """
            This is to find the Category sub-values(~sub categories).
            Searching for the category name.

        :param category_name:
        :param api:
        :return:
        """
        my_headers = {
            'Content-type': 'application/json',
            'Accept': 'application/json',
            'Authorization': 'Basic'
        }

        d = '{}'
        url = ''.join([HTTPS,
                       self.central_addr,
                       ':',
                       self.port,
                       api,
                       'categories/' + category_name,
                       '/list'])

        r = requests.post(url,
                          data=d,
                          auth=(self.username, self.password),
                          headers=my_headers,
                          verify=False)

        r.raise_for_status()
        return r.json()

    def get_category_value(self, category_name,
                           category_value,
                           api=CENTRAL_API):
        """
            This is to find the Category by its name
            and search for a specific value(sub-category).

        :param category_name:
        :param category_value:
        :param api:
        :return:
        """
        my_headers = {
            'Content-type': 'application/json',
            'Accept': 'application/json',
            'Authorization': 'Basic'
        }

        url = ''.join([HTTPS,
                       self.central_addr,
                       ':',
                       self.port,
                       api,
                       'categories/' + category_name,
                       '/',
                       category_value])

        r = requests.get(url,
                         auth=(self.username, self.password),
                         headers=my_headers,
                         verify=False
                         )

        r.raise_for_status()
        return r.json()

    def get_category_value(self, category_name,
                           category_value,
                           api=CENTRAL_API):
        """
            This is to find the Category by its name
            and search for a specific value(sub-category).

        :param category_name:
        :param category_value:
        :param api:
        :return:
        """
        my_headers = {
            'Content-type': 'application/json',
            'Accept': 'application/json',
            'Authorization': 'Basic'
        }

        url = ''.join([HTTPS,
                       self.central_addr,
                       ':',
                       self.port,
                       api,
                       'categories/' + category_name,
                       '/',
                       category_value])

        r = requests.get(url,
                         auth=(self.username, self.password),
                         headers=my_headers,
                         verify=False
                         )

        r.raise_for_status()
        return r.json()

    def get_vms_in_category(self, category_name, category_value, api=CENTRAL_API):
        """
        This returns the Vms that are assigned to a category AND/OR
        a category value (sub-category).

        :param category_name:
        :param category_value:
        :param api:
        :return:
        """
        if not category_name:
            # Forcing this to be required
            return None

        if not category_value:
            d = '"filter":"category_name=={name}"'.format(
                name=category_name)
        else:
            d = '"filter": "category_name=={name};' \
                'category_value=={value}"'.format(
                name=category_name,
                value=category_value)

        my_headers = {
            'Content-type': 'application/json',
            'Accept': 'application/json',
            'Authorization': 'Basic'
        }

        url = ''.join([HTTPS,
                       self.central_addr,
                       ':',
                       self.port,
                       api,
                       'vms/list'])

        r = requests.post(url,
                          data='{'+d+'}',
                          auth=(self.username, self.password),
                          headers=my_headers,
                          verify=False)

        r.raise_for_status()
        return r.json()
