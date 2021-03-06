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

import libvirt
import os
from lockfile import FileLock
from texttable import Texttable
import socket

from mcvirt_config import MCVirtConfig


class MCVirt(object):
    """Provides general MCVirt functions"""

    TEMPLATE_DIR = '/usr/lib/mcvirt/templates'
    BASE_STORAGE_DIR = '/var/lib/mcvirt'
    NODE_STORAGE_DIR = BASE_STORAGE_DIR + '/' + socket.gethostname()
    BASE_VM_STORAGE_DIR = NODE_STORAGE_DIR + '/vm'
    ISO_STORAGE_DIR = NODE_STORAGE_DIR + '/iso'
    LOCK_FILE_DIR = '/var/run/lock/mcvirt'
    LOCK_FILE = LOCK_FILE_DIR + '/lock'

    def __init__(self, uri=None, initialise_nodes=True, username=None,
                 ignore_failed_nodes=False, obtain_lock=True):
        """Checks lock file and performs initial connection to libvirt"""
        self.libvirt_uri = uri
        self.connection = None
        # Create an MCVirt config instance and force an upgrade
        MCVirtConfig(perform_upgrade=True, mcvirt_instance=self)

        # Configure custom username - used for unittests
        self.username = username

        # Cluster configuration
        self.initialise_nodes = initialise_nodes
        self.ignore_failed_nodes = ignore_failed_nodes
        self.remote_nodes = {}
        self.libvirt_node_connections = {}
        self.failed_nodes = []
        self.ignore_drbd = False

        self.obtained_filelock = False
        self.lockfile_object = None
        if (obtain_lock):
            self.obtainLock()

        # Create cluster instance, which will initialise the nodes
        from cluster.cluster import Cluster
        Cluster(self)

        # Connect to LibVirt
        self.getLibvirtConnection()

    def __del__(self):
        """Removes MCVirt lock file on object destruction"""
        # Disconnect from each of the nodes
        for connection in self.remote_nodes:
            self.remote_nodes[connection] = None
        self.remote_nodes = {}

        # Remove lock file
        self.releaseLock()

    def obtainLock(self, timeout=2, initialise_nodes=True):
        """Obtains the MCVirt lock file"""
        # Create lock file, if it does not exist
        if (not os.path.isfile(self.LOCK_FILE)):
            if (not os.path.isdir(self.LOCK_FILE_DIR)):
                os.mkdir(self.LOCK_FILE_DIR)
            open(self.LOCK_FILE, 'a').close()

        # Attempt to lock lockfile
        if (not self.obtained_filelock and not self.lockfile_object):
            self.lockfile_object = FileLock(self.LOCK_FILE)

        # Check if lockfile object is already locked
        if (self.obtained_filelock or self.lockfile_object.is_locked()):
            raise MCVirtException('An instance of MCVirt is already running')

        try:
            self.lockfile_object.acquire(timeout=timeout)
            if (self.initialise_nodes and initialise_nodes):
                for remote_node in self.remote_nodes:
                    self.remote_nodes[remote_node].runRemoteCommand('mcvirt-obtainLock',
                                                                    {'timeout': timeout})

            self.obtained_filelock = True
        except:
            raise MCVirtException('An instance of MCVirt is already running')

    def releaseLock(self, initialise_nodes=True):
        """Releases the MCVirt lock file"""
        if (self.obtained_filelock):
            if (self.initialise_nodes and initialise_nodes):
                for remote_node in self.remote_nodes:
                    self.remote_nodes[remote_node].runRemoteCommand('mcvirt-releaseLock', {})
            self.lockfile_object.release()
            self.lockfile_object = None
            self.obtained_filelock = False

    def getRemoteLibvirtConnection(self, remote_node):
        """Obtains and caches connections to remote libvirt daemons"""
        # Check if a connection has already been established
        if (remote_node.name not in self.libvirt_node_connections):
            # If not, establish a connection
            libvirt_url = 'qemu+ssh://%s/system' % remote_node.remote_ip
            connection = libvirt.open(libvirt_url)

            if (connection is None):
                raise ConnectionFailureToRemoteLibvirtInstance(
                    'Failed to connect to remote libvirt daemon on %s' %
                    remote_node.getName()
                )
            self.libvirt_node_connections[remote_node.name] = connection

        return self.libvirt_node_connections[remote_node.name]

    def getLibvirtConnection(self):
        """
        Obtains a libvirt connection. If one does not exist,
        connect to libvirt and store the connection as an object variable.
        Exit if an error occurs whilst connecting.
        """
        if (self.connection is None):
            self.connection = libvirt.open(self.libvirt_uri)
            if (self.connection is None):
                raise MCVirtException('Failed to open connection to the hypervisor')
        return self.connection

    def initialiseNodes(self):
        """Returns the status of the MCVirt 'initialise_nodes' flag"""
        return self.initialise_nodes

    def getAuthObject(self):
        """Returns an instance of the Auth class"""
        from auth import Auth
        return Auth(self.username)

    def getAllVirtualMachineObjects(self):
        """Obtain array of all domains from libvirt"""
        from virtual_machine.virtual_machine import VirtualMachine
        all_vms = VirtualMachine.getAllVms(self)
        vm_objects = []
        for vm_name in all_vms:
            vm_objects.append(VirtualMachine(self, vm_name))

        return vm_objects

    def listVms(self):
        """Lists the VMs that are currently on the host"""
        table = Texttable()
        table.set_deco(Texttable.HEADER | Texttable.VLINES)
        table.header(('VM Name', 'State', 'Node'))

        for vm_object in self.getAllVirtualMachineObjects():
            table.add_row((vm_object.getName(), vm_object.getState().name,
                           vm_object.getNode() or 'Unregistered'))
        print table.draw()

    def printInfo(self):
        """Prints information about the nodes in the cluster"""
        from cluster.cluster import Cluster
        from cluster.remote import CouldNotConnectToNodeException
        table = Texttable()
        table.set_deco(Texttable.HEADER | Texttable.VLINES)
        table.header(('Node', 'IP Address', 'Status'))
        cluster_object = Cluster(self)
        # Add this node to the table
        table.add_row((Cluster.getHostname(), cluster_object.getClusterIpAddress(),
                       'Local'))

        # Add remote nodes
        for node in cluster_object.getNodes(return_all=True):
            node_config = cluster_object.getNodeConfig(node)
            node_status = 'Unreachable'
            try:
                cluster_object.getRemoteNode(node)
                node_status = 'Connected'
            except CouldNotConnectToNodeException:
                pass
            table.add_row((node, node_config['ip_address'],
                           node_status))
        print table.draw()


class MCVirtException(Exception):
    """Provides an exception to be thrown for errors in MCVirt"""
    pass


class ConnectionFailureToRemoteLibvirtInstance(MCVirtException):
    """Connection failure whilst attempting to obtain a remote libvirt connection"""
    pass
