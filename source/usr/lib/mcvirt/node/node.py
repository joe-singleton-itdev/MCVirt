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

import re

from mcvirt.mcvirt import MCVirtException
from mcvirt.mcvirt_config import MCVirtConfig


class InvalidVolumeGroupNameException(MCVirtException):
    """The specified name of the volume group is invalid"""
    pass


class InvalidIPAddressException(MCVirtException):
    """The specified IP address is invalid"""
    pass


class Node(object):

    @staticmethod
    def setStorageVolumeGroup(mcvirt_instance, volume_group):
        """Update the MCVirt configuration to set the volume group for VM storage"""
        # Ensure volume_group name is valid
        pattern = re.compile("^[A-Z0-9a-z_-]+$")
        if (not pattern.match(volume_group)):
            raise InvalidVolumeGroupNameException('%s is not a valid volume group name' %
                                                  volume_group)

        # Update global MCVirt configuration
        def updateConfig(config):
            config['vm_storage_vg'] = volume_group
        mcvirt_config = MCVirtConfig(mcvirt_instance=mcvirt_instance)
        mcvirt_config.updateConfig(updateConfig, 'Set virtual machine storage volume group to %s' %
                                                 volume_group)

    @staticmethod
    def setClusterIpAddress(mcvirt_instance, ip_address):
        """Updates the cluster IP address for the node"""
        # Check validity of IP address (mainly to ensure that )
        pattern = re.compile(r"^((([01]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])[ (\[]?(\.|dot)"
                             "[ )\]]?){3}([01]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5]))$")
        if not pattern.match(ip_address):
            raise InvalidIPAddressException('%s is not a valid IP address' % ip_address)

        # Update global MCVirt configuration
        def updateConfig(config):
            config['cluster']['cluster_ip'] = ip_address
        mcvirt_config = MCVirtConfig(mcvirt_instance=mcvirt_instance)
        mcvirt_config.updateConfig(updateConfig, 'Set node cluster IP address to %s' %
                                                 ip_address)
