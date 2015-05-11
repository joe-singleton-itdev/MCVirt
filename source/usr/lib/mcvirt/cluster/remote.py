#
# Copyright I.T. Dev Ltd 2014
# http://www.itdev.co.uk
#
import json
from paramiko.client import SSHClient, AutoAddPolicy
from paramiko.ssh_exception import AuthenticationException

from mcvirt.mcvirt import McVirtException
from cluster import Cluster
from mcvirt.auth import Auth

class RemoteCommandExecutionFailedException(McVirtException):
  """A remote command execution fails"""
  pass

class UnknownRemoteCommandException(McVirtException):
  """An unknown command was passed to the remote machine"""
  pass

class NodeAuthenticationException(McVirtException):
  """Incorrect password supplied for remote node"""
  pass

class CouldNotConnectToNodeException(McVirtException):
  """Could not connect to remove cluster node"""
  pass

class Remote:
  """A class to perform remote commands on McVirt nodes"""

  REMOTE_MCVIRT_COMMAND = '/usr/lib/mcvirt/mcvirt-remote.py'

  @staticmethod
  def receiveRemoteCommand(mcvirt_instance, data):
    """Handles incoming data from the remote host"""
    from cluster import Cluster
    from mcvirt.virtual_machine.virtual_machine import VirtualMachine
    received_data = json.loads(data)
    action = received_data['action']
    arguments = received_data['arguments']

    return_data = []
    end_connection = False

    if (action == 'cluster-cluster-addNodeRemote'):
      # Adds a remote node to the local cluster configuration
      cluster_instance = Cluster(mcvirt_instance)
      return_data = cluster_instance.addNodeRemote(arguments['node'], arguments['ip_address'], arguments['public_key'])

    elif (action == 'cluster-cluster-addHostKey'):
      # Connect to the remote machine, saving the host key
      cluster_instance = Cluster(mcvirt_instance)
      remote = Remote(cluster_instance, arguments['node'], save_hostkey=True, initialise_node=False)
      remote = None

    elif (action == 'cluster-cluster-removeNodeConfiguration'):
      # Removes a remove McVirt node from the local configuration
      cluster_instance = Cluster(mcvirt_instance)
      cluster_instance.removeNodeConfiguration(arguments['node'])

    elif (action == 'auth-addUserPermissionGroup'):
      auth_object = mcvirt_instance.getAuthObject()
      if ('vm_name' in arguments and arguments['vm_name']):
        vm_object = VirtualMachine(mcvirt_instance, arguments['vm_name'])
      else:
        vm_object = None

      if ('ignore_duplicate' in arguments and arguments['ignore_duplicate']):
        ignore_duplicate = arguments['ignore_duplicate']
      else:
        ignore_duplicate = False

      auth_object.addUserPermissionGroup(mcvirt_object=mcvirt_instance,
                                         permission_group=arguments['permission_group'],
                                         username=arguments['username'],
                                         vm_object=vm_object,
                                         ignore_duplicate=ignore_duplicate)

    elif (action == 'auth-deleteUserPermissionGroup'):
      auth_object = mcvirt_instance.getAuthObject()
      vm_object = VirtualMachine(mcvirt_instance, arguments['vm_name'])
      auth_object.deleteUserPermissionGroup(mcvirt_object=mcvirt_instance,
                                            permission_group=arguments['permission_group'],
                                            username=arguments['username'],
                                            vm_object=vm_object)

    elif (action == 'auth-addSuperuser'):
      auth_object = mcvirt_instance.getAuthObject()
      if ('ignore_duplicate' in arguments and arguments['ignore_duplicate']):
        ignore_duplicate = arguments['ignore_duplicate']
      else:
        ignore_duplicate = False
      auth_object.addSuperuser(arguments['username'],
                               ignore_duplicate=ignore_duplicate)

    elif (action == 'virtual_machine-create'):
      VirtualMachine.create(mcvirt_instance, arguments['vm_name'], arguments['cpu_cores'],
                            arguments['memory_allocation'], node=arguments['node'],
                            available_nodes=arguments['available_nodes'])

    elif (action == 'virtual_machine-delete'):
      vm_object = VirtualMachine(mcvirt_instance, arguments['vm_name'])
      vm_object.delete(remove_data=arguments['remove_data'])

    elif (action == 'virtual_machine-register'):
      vm_object = VirtualMachine(mcvirt_instance, arguments['vm_name'])
      vm_object.register(set_node=False)

    elif (action == 'virtual_machine-unregister'):
      vm_object = VirtualMachine(mcvirt_instance, arguments['vm_name'])
      vm_object.unregister()

    elif (action == 'virtual_machine-start'):
      vm_object = VirtualMachine(mcvirt_instance, arguments['vm_name'])
      vm_object.start()

    elif (action == 'virtual_machine-stop'):
      vm_object = VirtualMachine(mcvirt_instance, arguments['vm_name'])
      vm_object.stop()

    elif (action == 'network_adapter-create'):
      from mcvirt.virtual_machine.network_adapter import NetworkAdapter
      vm_object = VirtualMachine(mcvirt_instance, arguments['vm_name'])
      NetworkAdapter.create(vm_object, arguments['network_name'], arguments['mac_address'])

    elif (action == 'virtual_machine-getState'):
      vm_object = VirtualMachine(mcvirt_instance, arguments['vm_name'])
      return_data = vm_object.getState()

    elif (action == 'virtual_machine-getInfo'):
      vm_object = VirtualMachine(mcvirt_instance, arguments['vm_name'])
      return_data = vm_object.getInfo()

    elif (action == 'virtual_machine-getAllVms'):
      from mcvirt.virtual_machine.virtual_machine import VirtualMachine
      return_data = VirtualMachine.getAllVms(mcvirt_instance)

    elif (action == 'virtual_machine-setNode'):
      from mcvirt.virtual_machine.virtual_machine import VirtualMachine
      vm_object = VirtualMachine(mcvirt_instance, arguments['vm_name'])
      vm_object._setNode(arguments['node'])

    elif (action == 'virtual_machine-hard_drive-createLogicalVolume'):
      from mcvirt.virtual_machine.hard_drive.factory import Factory as HardDriveFactory
      hard_drive_config_object = HardDriveFactory.getRemoteConfigObject(mcvirt_instance, arguments['config'])
      HardDriveFactory.getClass(hard_drive_config_object._getType())._createLogicalVolume(hard_drive_config_object,
                                                                                          name=arguments['name'],
                                                                                          size=arguments['size'])

    elif (action == 'virtual_machine-hard_drive-removeLogicalVolume'):
      from mcvirt.virtual_machine.hard_drive.factory import Factory as HardDriveFactory
      hard_drive_config_object = HardDriveFactory.getRemoteConfigObject(mcvirt_instance, arguments['config'])
      HardDriveFactory.getClass(hard_drive_config_object._getType())._removeLogicalVolume(hard_drive_config_object,
                                                                                          name=arguments['name'],
                                                                                          ignore_non_existent=arguments['ignore_non_existent'])

    elif (action == 'virtual_machine-hard_drive-activateLogicalVolume'):
      from mcvirt.virtual_machine.hard_drive.factory import Factory as HardDriveFactory
      hard_drive_config_object = HardDriveFactory.getRemoteConfigObject(mcvirt_instance, arguments['config'])
      HardDriveFactory.getClass(hard_drive_config_object._getType())._activateLogicalVolume(hard_drive_config_object,
                                                                                            name=arguments['name'])

    elif (action == 'virtual_machine-hard_drive-zeroLogicalVolume'):
      from mcvirt.virtual_machine.hard_drive.factory import Factory as HardDriveFactory
      hard_drive_config_object = HardDriveFactory.getRemoteConfigObject(mcvirt_instance, arguments['config'])
      HardDriveFactory.getClass(hard_drive_config_object._getType())._zeroLogicalVolume(hard_drive_config_object,
                                                                                        name=arguments['name'],
                                                                                        size=arguments['size'])

    elif (action == 'virtual_machine-hard_drive-drbd-generateDrbdConfig'):
      from mcvirt.virtual_machine.hard_drive.factory import Factory as HardDriveFactory
      hard_drive_config_object = HardDriveFactory.getRemoteConfigObject(mcvirt_instance, arguments['config'])
      hard_drive_config_object._generateDrbdConfig()

    elif (action == 'virtual_machine-hard_drive-drbd-removeDrbdConfig'):
      from mcvirt.virtual_machine.hard_drive.factory import Factory as HardDriveFactory
      hard_drive_config_object = HardDriveFactory.getRemoteConfigObject(mcvirt_instance, arguments['config'])
      hard_drive_config_object._removeDrbdConfig()

    elif (action == 'virtual_machine-hard_drive-drbd-initialiseMetaData'):
      from mcvirt.virtual_machine.hard_drive.factory import Factory as HardDriveFactory
      hard_drive_config_object = HardDriveFactory.getRemoteConfigObject(mcvirt_instance, arguments['config'])
      HardDriveFactory.getClass(hard_drive_config_object._getType())._initialiseMetaData(hard_drive_config_object._getResourceName())

    elif (action == 'virtual_machine-hard_drive-addToVirtualMachine'):
      from mcvirt.virtual_machine.hard_drive.factory import Factory as HardDriveFactory
      hard_drive_config_object = HardDriveFactory.getRemoteConfigObject(mcvirt_instance, arguments['config'])
      HardDriveFactory.getClass(hard_drive_config_object._getType())._addToVirtualMachine(hard_drive_config_object)

    elif (action == 'virtual_machine-hard_drive-removeFromVirtualMachine'):
      from mcvirt.virtual_machine.hard_drive.factory import Factory as HardDriveFactory
      hard_drive_config_object = HardDriveFactory.getRemoteConfigObject(mcvirt_instance, arguments['config'])
      HardDriveFactory.getClass(hard_drive_config_object._getType())._removeFromVirtualMachine(hard_drive_config_object)

    elif (action == 'virtual_machine-hard_drive-drbd-drbdUp'):
      from mcvirt.virtual_machine.hard_drive.factory import Factory as HardDriveFactory
      hard_drive_config_object = HardDriveFactory.getRemoteConfigObject(mcvirt_instance, arguments['config'])
      HardDriveFactory.getClass(hard_drive_config_object._getType())._drbdUp(hard_drive_config_object)

    elif (action == 'virtual_machine-hard_drive-drbd-drbdDown'):
      from mcvirt.virtual_machine.hard_drive.factory import Factory as HardDriveFactory
      hard_drive_config_object = HardDriveFactory.getRemoteConfigObject(mcvirt_instance, arguments['config'])
      HardDriveFactory.getClass(hard_drive_config_object._getType())._drbdDown(hard_drive_config_object)

    elif (action == 'virtual_machine-hard_drive-drbd-drbdSetSecondary'):
      from mcvirt.virtual_machine.hard_drive.factory import Factory as HardDriveFactory
      vm_object = VirtualMachine(mcvirt_instance, arguments['vm_name'])
      hard_drive_object = HardDriveFactory.getObject(vm_object, arguments['disk_id'])
      hard_drive_object._drbdSetSecondary()

    elif (action == 'virtual_machine-hard_drive-drbd-drbdConnect'):
      from mcvirt.virtual_machine.hard_drive.factory import Factory as HardDriveFactory
      vm_object = VirtualMachine(mcvirt_instance, arguments['vm_name'])
      hard_drive_object = HardDriveFactory.getObject(vm_object, arguments['disk_id'])
      hard_drive_object._drbdConnect()

    elif (action == 'virtual_machine-hard_drive-drbd-drbdDisconnect'):
      from mcvirt.virtual_machine.hard_drive.factory import Factory as HardDriveFactory
      vm_object = VirtualMachine(mcvirt_instance, arguments['vm_name'])
      hard_drive_object = HardDriveFactory.getObject(vm_object, arguments['disk_id'])
      hard_drive_object._drbdDisconnect()

    elif (action == 'node-network-create'):
      from mcvirt.node.network import Network
      Network.create(mcvirt_instance, arguments['network_name'], arguments['physical_interface'])

    elif (action == 'node-network-delete'):
      from mcvirt.node.network import Network
      network_object = Network(mcvirt_instance, arguments['network_name'])
      network_object.delete()

    elif (action == 'node-network-checkExists'):
      from mcvirt.node.network import Network
      return_data = Network._checkExists(arguments['network_name'])

    elif (action == 'node-network-getConfig'):
      from mcvirt.node.network import Network
      return_data = Network.getConfig()

    elif (action == 'node-drbd-enable'):
      from mcvirt.node.drbd import DRBD
      DRBD.enable(mcvirt_instance, arguments['secret'])

    elif (action == 'virtual_machine-hard_drive-drbd-setSyncState'):
      from mcvirt.virtual_machine.hard_drive.factory import Factory as HardDriveFactory
      vm_object = VirtualMachine(mcvirt_instance, arguments['vm_name'])
      hard_drive_object = HardDriveFactory.getObject(vm_object, arguments['disk_id'])
      hard_drive_object.setSyncState(arguments['sync_state'])

    elif (action == 'close'):
      # Delete McVirt instance, which removes the lock and force mcvirt-remote
      # to close
      end_connection = True

    elif (action == 'checkStatus'):
      return_data = ['0']

    else:
      raise UnknownRemoteCommandException('Unknown command: %s' % action)

    return (json.dumps(return_data), end_connection)

  def __init__(self, cluster_instance, name, save_hostkey=False, initialise_node=True, remote_ip=None, password=None):
    """Sets member variables"""
    self.name = name
    self.connection = None
    self.password = password
    self.save_hostkey = save_hostkey
    self.initialise_node = initialise_node

    # Ensure the node exists
    if (not self.save_hostkey):
      cluster_instance.ensureNodeExists(self.name)

    # If the user has not specified a remote IP address, get it from the node configuration
    if (remote_ip):
      self.remote_ip = remote_ip
    else:
      self.remote_ip = cluster_instance.getNodeConfig(name)['ip_address']

    self.__connect()

  def __del__(self):
    """Stop the SSH connection when the object is deleted"""
    if (self.connection):
      # Save the known_hosts file if specified
      if (self.save_hostkey):
        self.connection.save_host_keys(Cluster.SSH_KNOWN_HOSTS_FILE)

      if (self.initialise_node):
        # Tell remote script to close
        self.runRemoteCommand('close', None)

      # Close the SSH connection
      self.connection.close()

  def __connect(self):
    """Connect the SSH session"""
    if (self.connection is None):
      ssh_client = SSHClient()

      # Loads the user's known hosts file
      ssh_client.load_host_keys(Cluster.SSH_KNOWN_HOSTS_FILE)

      # If the hostkey is to be saved, allow unknown hosts
      if (self.save_hostkey):
        ssh_client.set_missing_host_key_policy(AutoAddPolicy())

      # Attempt to connect to the host
      try:
        if (self.password is not None):
          ssh_client.connect(self.remote_ip, username=Cluster.SSH_USER, password=self.password, timeout=10)
        else:
          ssh_client.connect(self.remote_ip, username=Cluster.SSH_USER, key_filename=Cluster.SSH_PRIVATE_KEY, timeout=10)
      except AuthenticationException:
        raise NodeAuthenticationException('Could not authenticate to node: %s' % self.name)
      except Exception, e:
        raise CouldNotConnectToNodeException('Could not connect to node: %s' % self.name)

      # Save the SSH client object
      self.connection = ssh_client

      if (self.initialise_node):
        # Run McVirt command
        (self.stdin, self.stdout, self.stderr) = self.connection.exec_command(self.REMOTE_MCVIRT_COMMAND)

        # Check the remote lock
        if (self.runRemoteCommand('checkStatus', None) != ['0']):
          raise McVirtException('Remote node locked: %s' % self.name)

  def runRemoteCommand(self, action, arguments):
    """Prepare and run a remote command on a cluster node"""
    # Ensure connection is alive
    if (self.connection is None):
      self.__connect()

    # Generate a JSON of the command and arguments
    command_json = json.dumps({'action': action, 'arguments': arguments}, sort_keys=True)

    # Perform the remote command
    self.stdin.write("%s\n" % command_json)
    self.stdin.flush()
    stdout = self.stdout.readline()

    # Attempt to convert stdout to JSON
    try:
      # Obtains the first line of output and decode JSON
      return json.loads(str.strip(stdout))
    except ValueError, e:
    # If the exit code was not 0, close the SSH session and throw an exception
      stderr = self.stderr.readlines()
      if (stderr):
        exit_code = self.stdout.channel.recv_exit_status()
        self.connection.close()
        self.connection = None
        raise RemoteCommandExecutionFailedException("Exit Code: %s\nCommand: %s\nStdout: %s\nStderr: %s" % (exit_code, command_json, ''.join(stdout), ''.join(stderr)))
