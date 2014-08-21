#
# Copyright I.T. Dev Ltd 2014
# http://www.itdev.co.uk
#
import libvirt
import xml.etree.ElementTree as ET
import re
from subprocess import call
import os
import shutil

from mcvirt.mcvirt import McVirt, McVirtException
from mcvirt.virtual_machine.hard_drive import HardDrive
from mcvirt.virtual_machine.disk_drive import DiskDrive
from mcvirt.virtual_machine.network_adapter import NetworkAdapter
from mcvirt.virtual_machine.virtual_machine_config import VirtualMachineConfig
from mcvirt.auth import Auth

class VirtualMachine:
  """Provides operations to manage a libvirt virtual machine"""

  def __init__(self, mcvirt_object, name):
    """Sets member variables and obtains libvirt domain object"""
    self.auth = mcvirt_object.getAuthObject()
    self.connection = mcvirt_object.getLibvirtConnection()
    self.name = name

    # Ensure that the connection is alive
    if (not self.connection.isAlive()):
      raise McVirtException('Error: Connection not alive')

    # Check that the domain exists
    if (not VirtualMachine._checkExists(self.connection, self.name)):
      raise McVirtException('Error: Virtual Machine does not exist')

    # Get config object
    self.config = VirtualMachineConfig(self)
    self.mcvirt_config = mcvirt_object.getConfigObject()

    # Create a libvirt domain object
    self.domain_object = self._getDomainObject()

  def getConfigObject(self):
    """Returns the configuration object for the VM"""
    return self.config

  def getName(self):
    """Returns the name of the VM"""
    return self.name

  def _getDomainObject(self):
    """Looks up libvirt domain object, based on VM name,
    and return object"""
    # Get the domain object.
    return self.connection.lookupByName(self.name)


  def stop(self):
    """Stops the VM"""
    # Check the user has permission to start/stop VMs
    self.auth.checkPermission(Auth.PERMISSIONS.CHANGE_VM_POWER_STATE, self)

    # Determine if VM is running
    if (self.isRunning()):

      # Stop the VM
      self.domain_object.destroy()
      print 'Successfully stopped VM'

    else:
      raise McVirtException('The VM is already shutdown')


  def start(self):
    """Starts the VM"""
    # Check the user has permission to start/stop VMs
    self.auth.checkPermission(Auth.PERMISSIONS.CHANGE_VM_POWER_STATE, self)

    # Determine if VM is stopped
    if (not self.isRunning()):

      # Start the VM
      self.domain_object.create()
      print 'Successfully started VM'

    else:
      raise McVirtException('The VM is already running')


  def isRunning(self):
    return (self.domain_object.state()[0] == libvirt.VIR_DOMAIN_RUNNING)

  def getInfo(self):
    print 'Name: ' + self.getName()

  def delete(self, delete_disk = False):
    """Delete the VM - removing it from libvirt and from the filesystem"""
    # Check the user has permission to modify VMs
    self.auth.checkPermission(Auth.PERMISSIONS.MODIFY_VM, self)

    # Determine if VM is running
    if (self.domain_object.state()[0] == libvirt.VIR_DOMAIN_RUNNING):
      raise McVirtException('Error: Can\'t delete running VM')

    # If 'delete_disk' has been passed as True, delete disks associated
    # with VM
    if (delete_disk):
      for disk_object in self.getDiskObjects():
        disk_object.delete()

    # Undefine object from libvirt
    try:
      self.domain_object.undefine()
    except:
      raise McVirtException('Failed to delete VM from libvirt')
    print 'Successfully unregistered VM'

    # If 'delete_disk' has been passed as True, delete directory
    # from VM storage
    if (delete_disk):
      shutil.rmtree(VirtualMachine.getVMDir(self.name))
      print 'Successfully removed VM data from host'


  def updateRAM(self, memory_allocation):
    """Updates the amount of RAM alloocated to a VM"""
    # Check the user has permission to modify VMs
    self.auth.checkPermission(Auth.PERMISSIONS.MODIFY_VM, self)

    def updateXML(domain_xml):
      # Capture original allocation
      old_ram_allocation = domain_xml.find('./memory').text

      # Convert original allocation from KiB to MB
      old_ram_allocation_mb = ((int(old_ram_allocation) * 1024) / 1000000)

      # Update RAM allocation and unit measurement
      domain_xml.find('./memory').text = str(memory_allocation)
      domain_xml.find('./memory').set('unit', 'MB')
      domain_xml.find('./currentMemory').text = str(memory_allocation)
      domain_xml.find('./currentMemory').set('unit', 'MB')
      print 'RAM allocation will be changed from %sMB to %sMB.' % (old_ram_allocation_mb, memory_allocation)

    self.editConfig(updateXML)


  def updateCPU(self, cpu_count):
    """Updates the number of CPU cores attached to a VM"""
    # Check the user has permission to modify VMs
    self.auth.checkPermission(Auth.PERMISSIONS.MODIFY_VM, self)

    def updateXML(domain_xml):
      # Capture original settings
      old_cpu_count = domain_xml.find('./vcpu').text

      # Update RAM allocation and unit measurement
      domain_xml.find('./vcpu').text = str(cpu_count)
      print 'Number of virtual cores will be changed from %s to %s.' % (old_cpu_count, cpu_count)

    self.editConfig(updateXML)


  def getDiskObjects(self):
    """Returns an array of disk objects for the disks attached to the VM"""
    disks = self.config.getConfig()['disks']
    disk_objects = []
    for disk_id in disks:
      disk_objects.append(HardDrive(self, disk_id))
    return disk_objects


  @staticmethod
  def _checkExists(libvirt_connection, name):
    """Check if a domain exists"""

    # Obtain array of all domains from libvirt
    all_domains = libvirt_connection.listAllDomains()

    # Determine if the name of any of the domains returned
    # matches the requested name
    if (any(domain.name() == name for domain in all_domains)):
      return True
    else:
      # VM does not exist
      return False


  @staticmethod
  def getVMDir(name):
    """Returns the storage directory for a given VM"""
    return McVirt.BASE_VM_STORAGE_DIR + '/' + name


  def editConfig(self, callback_function):
    """Provides an interface for updating the libvirt configuration, by obtaining
    the configuration, performing a callback function to perform changes on the configuration
    and pushing the configuration back into LibVirt"""
    # Obtain VM XML
    domain_flags = (libvirt.VIR_DOMAIN_XML_INACTIVE + libvirt.VIR_DOMAIN_XML_SECURE)
    domain_xml = ET.fromstring(self.domain_object.XMLDesc(domain_flags))

    # Perform callback function to make changes to the XML
    callback_function(domain_xml)

    # Push XML changes back to libvirt
    domain_xml_string = ET.tostring(domain_xml, encoding = 'utf8', method = 'xml')

    try:
      self.connection.defineXML(domain_xml_string)
    except:
      raise McVirtException('Error: An error occured whilst updating the VM')


  @staticmethod
  def create(mcvirt_instance, name, cpu_cores, memory_allocation, disk_size, network_interfaces):
    """Creates a VM and returns the virtual_machine object for it"""
    # Check the user has permission to create VMs
    mcvirt_instance.getAuthObject().checkPermission(Auth.PERMISSIONS.CREATE_VM)

    # Validate the VM name
    valid_name_re = re.compile(r'[^a-z^0-9^A-Z-]').search
    if (bool(valid_name_re(name))):
      raise McVirtException('Error: Invalid VM Name - VM Name can only contain 0-9 a-Z and dashes')

    # Determine if VM already exists
    if (VirtualMachine._checkExists(mcvirt_instance.getLibvirtConnection(), name)):
      raise McVirtException('Error: VM already exists')

    # Import domain XML template
    domain_xml = ET.parse(McVirt.TEMPLATE_DIR + '/domain.xml')

    # Convert memory size from megabytes into kilobytes
    memory_allocation_kb = memory_allocation * 1024

    # Add Name, RAM and CPU variables to XML
    domain_xml.find('./name').text = str(name)
    domain_xml.find('./memory').text = str(memory_allocation_kb)
    domain_xml.find('./vcpu').text = str(cpu_cores)

    # Create directory for VM
    if (not os.path.exists(VirtualMachine.getVMDir(name))):
      os.makedirs(VirtualMachine.getVMDir(name))
    else:
      raise McVirtException('Error: VM directory already exists')

    # Create VM configuration file
    VirtualMachineConfig.create(name)

    # Register VM with LibVirt
    print 'Registering VM wth libvirt'
    domain_xml_string = ET.tostring(domain_xml.getroot(), encoding = 'utf8', method = 'xml')

    try:
      mcvirt_instance.getLibvirtConnection().defineXML(domain_xml_string)
    except:
      raise McVirtException('Error: An error occured whilst registering VM')

    # Obtain an object for the new VM, to use to create disks/network interfaces
    vm_object = VirtualMachine(mcvirt_instance, name)

    # Create disk image
    print 'Creating disk image'
    HardDrive.create(vm_object, disk_size)

    # If any have been specified, add a network configuration for each of the
    # network interfaces to the domain XML
    if (network_interfaces != None):
      devices_xml = domain_xml.find('./devices')
      for network in network_interfaces:
        NetworkAdapter.create(vm_object, network)


  def getVncPort(self):
    """Returns the port used by the VNC display for the VM"""
    # Check the user has permission to view the VM console
    self.auth.checkPermission(Auth.PERMISSIONS.VIEW_VNC_CONSOLE, self)

    if (not self.isRunning()):
      raise McVirtException('The VM is not running')
    domain_xml = ET.fromstring(self.domain_object.XMLDesc(libvirt.VIR_DOMAIN_XML_SECURE))

    if (domain_xml.find('./devices/graphics[@type="vnc"]') == None):
      raise McVirtException('VNC is not emabled on the VM')
    else:
      return domain_xml.find('./devices/graphics[@type="vnc"]').get('port')


  def setBootOrder(self, boot_devices):
    """Sets the boot devices and the order in which devices are booted from"""

    def updateXML(domain_xml):
      old_boot_objects = domain_xml.findall('./os/boot')
      os_xml = domain_xml.find('./os')

      # Remove old boot XML configuration elements
      for old_boot_object in old_boot_objects:
        os_xml.remove(old_boot_object)

      # Add new boot XML configuration elements
      for new_boot_device in boot_devices:
        new_boot_xml_object = ET.Element('boot')
        new_boot_xml_object.set('dev', new_boot_device)

        # Appened new XML configuration onto OS section of domain XML
        os_xml.append(new_boot_xml_object)

    self.editConfig(updateXML)
