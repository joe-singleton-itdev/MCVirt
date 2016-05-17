# Copyright (c) 2014 - I.T. Dev Ltd
#
# This file is part of MCVirt.
#
# MCVirt is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# MCVirt is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MCVirt.  If not, see <http://www.gnu.org/licenses/>

import Pyro4
import libvirt
import xml.etree.ElementTree as ET

from mcvirt.exceptions import NetworkAdapterDoesNotExistException
from mcvirt.auth.auth import Auth
from mcvirt.auth.permissions import PERMISSIONS
from mcvirt.rpc.lock import lockingMethod


class NetworkAdapter(object):
    """Provides operations to network interfaces attached to a VM"""

    def __init__(self, mac_address, vm_object):
        """Sets member variables and obtains libvirt domain object"""
        self.vm_object = vm_object
        self.mac_address = mac_address

        if (not self._checkExists()):
            raise NetworkAdapterDoesNotExistException(
                'No interface with MAC address \'%s\' attached to VM' %
                self.getMacAddress())

    def _generateLibvirtXml(self):
        """Creates a basic XML configuration for a network interface,
        encorporating the name of the network"""
        interface_xml = ET.Element('interface')
        interface_xml.set('type', 'network')

        # Create 'source'
        interface_source_xml = ET.SubElement(interface_xml, 'source')
        interface_source_xml.set('network', self.getConnectedNetwork())

        # Create 'model'
        interface_model_xml = ET.SubElement(interface_xml, 'model')
        interface_model_xml.set('type', 'virtio')

        mac_address_xml = ET.SubElement(interface_xml, 'mac')
        mac_address_xml.set('address', self.getMacAddress())

        return interface_xml

    def _checkExists(self):
        """Determines if the network interface is present on the VM"""
        vm_config = self.vm_object.getConfigObject().getConfig()
        return (self.getMacAddress() in vm_config['network_interfaces'])

    def getLibvirtConfig(self):
        """Returns a dict of the LibVirt configuration for the network interface"""
        domain_config = self.vm_object.getLibvirtConfig()
        interface_config = domain_config.find(
            './devices/interface[@type="network"]/mac[@address="%s"]/..' %
            self.mac_address)

        if (interface_config is None):
            raise NetworkAdapterDoesNotExistException(
                'Interface does not exist: %s' % self.mac_address
            )

        return interface_config

    def getConfig(self):
        """Returns a dict of the MCVirt configuration for the network interface"""
        vm_config = self.vm_object.getConfigObject().getConfig()
        network_config = \
            {
                'mac_address': self.getMacAddress(),
                'network': vm_config['network_interfaces'][self.getMacAddress()]
            }
        return network_config

    @Pyro4.expose()
    def getConnectedNetwork(self):
        """Returns the network that a given interface is connected to"""
        interface_config = self.getConfig()
        return interface_config['network']

    @staticmethod
    def generateMacAddress():
        """Generates a random MAC address for new VM network interfaces"""
        import random
        mac = [0x00, 0x16, 0x3e,
               random.randint(0x00, 0x7f),
               random.randint(0x00, 0xff),
               random.randint(0x00, 0xff)]

        return ':'.join(map(lambda x: "%02x" % x, mac))

    @Pyro4.expose()
    def getMacAddress(self):
        """Returns the MAC address of the current network object"""
        return self.mac_address

    @Pyro4.expose()
    @lockingMethod()
    def delete(self):
        """Remove the given interface from the VM, based on the given MAC address"""
        self.vm_object.mcvirt_object.getAuthObject().assertPermission(
            PERMISSIONS.MODIFY_VM,
            self.vm_object
        )

        def updateXML(domain_xml):
            device_xml = domain_xml.find('./devices')
            interface_xml = device_xml.find(
                './interface[@type="network"]/mac[@address="%s"]/..' %
                self.getMacAddress())

            if (interface_xml is None):
                raise NetworkAdapterDoesNotExistException(
                    'No interface with MAC address \'%s\' attached to VM' %
                    self.getMacAddress())

            device_xml.remove(interface_xml)

        self.vm_object.editConfig(updateXML)

        # Update the VM configuration
        def updateVmConfig(config):
            del config['network_interfaces'][self.getMacAddress()]
        self.vm_object.getConfigObject().updateConfig(
            updateVmConfig, 'Removed network adapter from \'%s\' on \'%s\' network: %s' %
            (self.vm_object.getName(), self.getConnectedNetwork(), self.getMacAddress()))