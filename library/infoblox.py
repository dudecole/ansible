"""
This library contains classes and functions for communicating with
the Infoblox API.  Currently, it is focused on searching Infoblox
extensible attributes and their k,v pairs.


Todo: -

Documentation: pydoc ./infoblox.py

Implementation Examples: infoblox_test.py

Contact: DCole
         dudecole@outlook.com
"""
import requests
import sys
import logging
requests.packages.urllib3.disable_warnings()

logger = logging.getLogger(__name__)


class InfoBlox:
    def __init__(self, ib_host, user, pw, vrf=None, environment=None, ip_address=None, site=None, network_zone=None):
        """ Searches Infoblox WAPI for vrf and environment variables

        Todo: -add in user,password parameters

        Sets vrf and environment variables for full_url.get_bu_network
        (cf. get_bu_network())

        Args:
            vrf (string) (required) A ServiceNow business Unit used to
                      create the InfoBlox object with.

            environment (string) (required) A ServiceNow environment used to
                      create the InfoBlox object with.

            site (string) (required) A ServiceNow datacenter used to
                      create the InfoBlox object with.
        """
        self.ib_host = ib_host
        self.user = user
        self.pw = pw
        self.vrf = vrf
        self.environment = environment
        self.ip_address = ip_address
        self.site = site
        self.network_zone = network_zone
        self.ib_host_url = 'https://'+ib_host+'/wapi/'
        self.wapi_version = self._get_wapi_version()

    def get_bu_network(self, vrf='Common Services(SSI)', site='WDC', env='Non Prod', zone='Internal', version='SSI2.0'):
        """ Calls the ib_http_request() function which passes the extensible Attributes
         of vrf and environment in a attr_url string.  VRF is the snow_business Unit and snow_env is
         the environment; 'prod','dev','test'.  This then returns vlan_id, subnet, gateway.

        :return subnet:

        url example:
        https://10.60.208.83/wapi/v1.0/network?*VRF=IST&*Site=WDC&*Environment=dev
        """

        # define search character to keep things clean
        character = "&*"

        # Infoblox extensible attribute search url
        attr_url = self.ib_host_url + self.wapi_version + '/network?*VRF:=' + vrf +\
                   character + 'Site:=' + site +\
                   character + 'Environment:=' + env +\
                   character + 'Zone:=' + zone +\
                   character + 'Network Ver:=' + version

        # call function to do the rest call with the attr_url
        response = self.ib_http_request('GET', attr_url)
        return response

    def create_host_record(self, network, fqdn):
        """
        REST call to create host record AND use 'next_available' infoblox method

        https://community.infoblox.com/t5/API-Integration/Get-Next-Available-IP-and-Reserve/td-p/8548


        Caution:
        After a little bit more digging I've noticed that the IP addresses that are being picked up
        from the WAPI call have a Lease state of 'Free' where as all of the other unused IP addresses
        have a Lease state of 'Abandoned'.

        POST URL: https://gm.example.com/wapi/v2.0/record:host

        :param network: 10.x.x.x/24 format
        :param fqdn:
        :return: ip address
        """

        # lowercase fqdn
        fqdn = str(fqdn).lower()

        # remove the slash and second index of '/24'
        remove_slash = network.split('/')
        remove_slash.pop(-1)

        # join back as a string
        my_str = ''.join(remove_slash)

        # split string to parse out host portion of the IP address
        # and remove last index
        my_list = my_str.split('.')
        my_list.pop(-1)

        # join back as string to prep for char add of '.0' - '.10'
        new_string = '.'.join(my_list)

        # generate list of exclude network portion of address + the host portion (1-10) to exclude
        final_list = []
        for i in range(11):  # starting available IP count at .11
            final_list.append(new_string + '.' + str(i))

        # exclude the broadcast address
        final_list.append(new_string + '.' + '255')
        # joining list as a string and putting '"' (quotes) at beginning and end
        exclude_join = '", "'.join(final_list)
        exclude_string = ''.join(('"', exclude_join, '"'))

        data = '{"name": "' + fqdn + '", "ipv4addrs": [{"ipv4addr": ' + \
               '{"_object_function": "next_available_ip", "_object": "network", ' + \
               '"_object_parameters": {"network": ' + '"' + network + '"}, "_result_field": ' + \
               '"ips", "_parameters": {"num": 1, "exclude": [' + exclude_string + ']}}}]}'

        # url format example:   https://10.60.208.78/wapi/v2.6.1/record:host
        url = self.ib_host_url + self.wapi_version + '/record:host'

        # call function to do the rest call with the attr_url
        response = self.ib_http_request('POST', url, data=data)

        # call to get the IP address just assigned.
        ip_address = self.ib_http_request('GET', url + '?name~=' + fqdn)

        return ip_address

    def get_subnet_details(self, network):
        """calls the ib_http_request() function and passes the url with the network/subnet
        This is the URI that contains the VLAN ID...

        url example:
        https://10.60.208.83/wapi/v1.2/network?network=192.168.1.0&_return_fields%2b=extattrs

        :param network:
        :return Network details in list, with dictionary of extattrs{VLAN,VRF, Environemnt,Site}:

            Return example:
            "extattrs":{VRF":{value":IST"}, "environment":{"value":"prod"},"site":{"value":"wdc"},
            "VLAN":{"value":9999}

        """

        # Infoblox extensible attribute search url
        attr_url = self.ib_host_url + self.wapi_version + '/network?network=' + network + '&_return_fields%2b=extattrs'

        # call function to do the rest call with the attr_url
        response = self.ib_http_request('GET', attr_url)
        return response

    def get_network_details(self, network):
        """
        Calls the ib_http_request() function and passes the url with a network.

        url example:
        https://10.60.208.83/wapi/v1.2/ipv4address?network=192.168.1.0&_return_fields%2b=extattrs

        :param ip:
        :return Returns a list of dictionaries of all IP addresses in the subnet.
        The Extensible Attributes aren't inherited correctly from the parent Network so the data
        that is available for this is IP 'Status', and DNS 'Names':
        """
        attr_url = self.ib_host_url + self.wapi_version + '/ipv4address?network=' + network + '&_return_fields%2b=extattrs'

        # call function to do the rest call with the attr_url
        response = self.ib_http_request('GET', attr_url)
        return response

    def ib_http_request(self, request_type, url, data=None):
        """ Handler for generic HTTP requests to the InfoBlox API.
        """
        # Set headers
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        if request_type == 'GET':
            # GET response from Infoblox API
            response = requests.get(url, auth=(self.user, self.pw),
                                    headers=headers, verify=False)

        elif request_type == 'PUT':
            # PUT response from Infoblox API
            if data is not None:
                response = requests.put(url, auth=(self.user, self.pw),
                                        headers=headers, data=data)
            else:
                response = requests.put(url, auth=(self.user, self.pw),
                                        headers=headers, data='{}')

        elif request_type == 'POST':
            if data is not None:
                response = requests.post(url,auth=(self.user, self.pw),
                                         data=data, headers=headers, verify=False)
            else:
                response = requests.put(url, auth=(self.user, self.pw),
                                        headers=headers, data='{}')

        if response.status_code >= 200 and response.status_code < 300:
            if request_type == 'GET' or request_type == 'POST':
                result = response.json()
            else:
                result = response.json()
        else:
            sys.exit("HTTP Code: %s \n response text: %s" % (response.status_code, response.text))

        return result
    
    def _get_wapi_version(self):
        """
        This gets the current API version for Infoblox and chooses the last in the returned list.
        This sets the v1.x of the URL

        url example:
        https://10.60.208.83/wapi/v1.0/?_schema

        :return Returns the last item in the 'supported_versions' list:

        "supported_versions": [
        "1.0",
        "1.1",
        "1.2",
        "1.2.1",
        "2.6..",
        <-- returns the last from the schema list

        After the value is returned the letter 'v'
        is added to the front to make v1.x format

        """

        wapi_url = self.ib_host_url + "v1.0/?_schema"

        version = self.ib_http_request('GET',wapi_url)
        wapi_version = (version['supported_versions'][-1])

        # setting the final version to include a 'v' as the api looks for that
        final_version = 'v' + wapi_version
        return final_version

    def get_ip_properties(self, ip_address):
        """
        This queries infoblox for an IP address and returns the network
        properties.

            https://10.60.208.78/wapi/v1.2/ipv4address?ip_address=10.52.95.12

        :param ip_address:
        :return XX.XX.XX.X/24 format of the network:
        """

        if not ip_address:
            sys.exit("No IP Address passed: {}".format(1))
        else:
            url = self.ib_host_url + self.wapi_version + '/ipv4address?ip_address=' + ip_address
            r = self.ib_http_request('GET', url)
            return r
