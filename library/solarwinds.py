"""
This library contains classes and functions for communicating with
the Solarwinds/Orion API.

It uses the orionsdk as a client that serializes the data into
recognizable SWQL queries.

Todo: - Function to get a VM uuid
      - Log file functionality
            - Try/Catch blocks, with errors written to log file

Documentation: pydoc ./solarwinds.py

Contact: DCole
         dudecole@outlook.com

"""

import orionsdk
import re
import requests
requests.packages.urllib3.disable_warnings()


class Solarwinds:

    def __init__(self, hostname='default',
                 username='gus',
                 password='chiggins',
                 verify=False):

        self.hostname = hostname
        self.username = username
        self.password = password
        self.verify = verify
        self.swis = orionsdk.SwisClient(hostname=hostname,
                                        username=username,
                                        password=password,
                                        verify=verify)

    def get_node(self, ip_address):
        """
        :return: JSON dictionary of all nodes
        """
        if not ip_address:
            return_value = "No IP Address entered!"

        else:
            return_value = self.swis.query("SELECT Caption, "
                                       "SysName, Uri, NodeID, "
                                       "IPAddress "
                                       "from Orion.Nodes "
                                       "WHERE IPAddress = @ip_address",
                                       ip_address=ip_address)

        return return_value

    def add_node(self, node_name, ip_address):
        community = 'public'

        # set up property bag for the new node
        props = {
            'IPAddress': ip_address,
            'EngineID': 1,
            'ObjectSubType': 'SNMP',
            'SNMPVersion': 2,
            'Community': community,
            'Caption': node_name,
            'DNS': node_name,
            'SysName': node_name
        }

        results = self.swis.create('Orion.Nodes', **props)

        # extract the nodeID from the result
        nodeid = re.search(r'(\d+)$', results).group(0)

        pollers_enabled = {
            'N.Status.ICMP.Native': True,
            'N.Status.SNMP.Native': False,
            'N.ResponseTime.ICMP.Native': True,
            'N.ResponseTime.SNMP.Native': False,
            'N.Details.SNMP.Generic': True,
            'N.Uptime.SNMP.Generic': True,
            'N.Cpu.SNMP.HrProcessorLoad': True,
            'N.Memory.SNMP.NetSnmpReal': True,
            'N.AssetInventory.Snmp.Generic': True,
            'N.Topology_Layer3.SNMP.ipNetToMedia': False,
            'N.Routing.SNMP.Ipv4CidrRoutingTable': False
        }

        pollers = []
        for k in pollers_enabled:
            pollers.append(
                {
                    'PollerType': k,
                    'NetObject': 'N:' + nodeid,
                    'NetObjectType': 'N',
                    'NetObjectID': nodeid,
                    'Enabled': pollers_enabled[k]
                }
            )

        for poller in pollers:
            # print("  Adding poller type: {} with status {}... ".format(poller['PollerType'], poller['Enabled']),
            #       end="")
            return_value = self.swis.create('Orion.Pollers', **poller)

        return return_value

    def get_pollers(self):
        """
        :return: JSON dictionary of all nodes
        """

        return_value = self.swis.query("SELECT Uri from Orion.Nodes")
        return return_value

    def get_poller(self, poller_id='0'):
        """
        :return: JSON dictionary of all nodes
        """
        return_value = self.swis.query("SELECT Uri from Orion.Nodes WHERE PollerID="
                                       + "'" + poller_id + "'")
        return return_value

    def delete_node(self, ip_address):
        """
        This queries for the node ip address and node name then deletes the record
        from solarwinds/orion

        :param ip_address:
        :return: results of API node delete method
        """

        if not ip_address:
            return "No IP address passed"
        else:
            search_return = self.swis.query("SELECT Caption, "
                                           "SysName, Uri, NodeID, "
                                           "IPAddress "
                                           "from Orion.Nodes "
                                           "WHERE IPAddress = @ip_address",
                                           ip_address=ip_address)

        if search_return:
            for i in range(len(search_return['results'])):
                self.swis.delete(search_return['results'][i]['Uri'])

        else:
            return search_return

