"""
This library contains classes and functions for communicating with
the Commvault API.

Since some responses are returned in a blend of XML and JSON,
I figured it was easiest done in python.


Todo: - Function to get a VM uuid
      - Log file functionality
            - Try/Catch blocks, with errors written to log file

Documentation: pydoc ./solarwinds.py

Contact: DCole
         dudecole@outlook.com

"""
import requests
import sys
import xml.etree.ElementTree as ET
import base64
requests.packages.urllib3.disable_warnings()


class CommvaultClient:

    def __init__(self, hostname,
                 username,
                 password):

        self.hostname = hostname
        self.username = username
        self.password = password
        self.base_url = 'http://' + hostname + '/webconsole/api/'
        self.token = self._get_auth_token()
        self.headers = {'Authtoken': self.token}

    def _get_auth_token(self):
        """
        This token is required to do any REST calls.

        todo:
            1. find a way to specify python3 interpreter
                for a specific playbook/role.  I know there
                is a way to specify within the hosts/host_vars,
                but would be cool if there was a to be more
                granular, i.e. playbook/role.

        :return: Returns the token in a string format
        """

        #####FOR PYTHON 3##############################
        # this is for python 3.  Since ansible is using
        # python 2 it doesn't allow 'str' to have more than
        # 1 argument
        #
        # pwd = bytes(self.password, encoding='utf8')
        # pwd = str(base64.b64encode(pwd), encoding='utf-8')
        ################################################

        #####FOR PYTHON 2##############################
        # will use this for ansible - need
        pwd = base64.b64encode(self.password)
        ################################################

        loginReq = '<DM2ContentIndexing_CheckCredentialReq username="' + \
                   self.username + '" password="' + pwd + '"' + '/>'

        r = requests.post(self.base_url + 'Login', data=loginReq)
        if r.status_code == 200:
            root = ET.fromstring(r.text)
            if 'token' in root.attrib:
                token = root.attrib['token']
            else:
                sys.exit("Login Failed: {}".format(1))
        else:
            sys.exit("There was an error "
                     "logging in: {}".format(1))
        return token

    def get_client_list(self):
        """
        This gets a list of all clients.

            todo: need to validate if pagination is a factor in this list

        :return: Returns a string of the full list of clients.
        """
        url = self.base_url + 'Client'
        r = requests.get(url, headers=self.headers)
        r.raise_for_status()
        return r.text

    def search_client_name(self, client_name):
        """
        This is to search for a client computer by the client name.

        Example of URI
            http://self.base_url/Client/byName(clientName='client_name')
        :param client_name:
        :return:
        """
        url = self.base_url + "Client/byName(clientName='" + \
                        client_name + "')"
        r = requests.get(url, headers=self.headers)
        r.raise_for_status()
        return r.text

    def search_client_id(self, client_id):
        """
        This searches for the Client Name.

        URI example:
            http://self.base_url/Client/client_id

        :param client_id: String
        :return: Returns r.text which appears like an XML string
        """
        url = self.base_url + "Client/" + client_id
        r = requests.get(url, headers=self.headers)
        r.raise_for_status()
        return r.text

    def get_client_license(self, client_id):
        """
        This searches for the license assigned to the client.
        This is used before a client has its license removed.

        URI example:
            http://self.base_url/Client/client_id/License

        :param client_id:
        :return: Returns r.text which appears like an XML string
        """
        url = self.base_url + "Client/" + client_id + "/License"
        r = requests.get(url, headers=self.headers)
        r.raise_for_status()
        return r.text

    def unlicense_client(self, client, app_type,
                         platform_type, license_name):
        """
        This removes the license from a client.  The required body
        is specified in the 'data' variable below:


        URI example:
            http://self.base_url/Client/License/Release

        :param client:
        :param app_type: Integer
        :param platform_type: Integer
        :param license_name:
        :return Response from license release request:
        """
        json_body = {"isClientLevelOperation": True,
                "licensesInfo": [{
                    "platformType": platform_type,
                    "license": {
                        "appType": app_type,
                        "licenseName": license_name
                    }
                }],
                "clientEntity": {
                    "clientName": client
                }
                }

        # add k,v 'accept':'application/json' to headers dict
        self.headers['Accept'] = "application/json"
        url = self.base_url + "Client/License/Release"
        r = requests.post(url, headers=self.headers, json=json_body)
        r.raise_for_status()
        return r.json()
