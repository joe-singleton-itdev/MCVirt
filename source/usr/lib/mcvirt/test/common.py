from mcvirt.virtual_machine.virtual_machine import VirtualMachine, PowerStates, LockStates
from mcvirt.cluster.cluster import Cluster


def stop_and_delete(mcvirt_instance, vm_name):
    """Stops and removes VMs"""
    if (VirtualMachine._checkExists(mcvirt_instance.getLibvirtConnection(), vm_name)):
        vm_object = VirtualMachine(mcvirt_instance, vm_name)

        # Reset sync state for any DRBD disks
        for disk_object in vm_object.getDiskObjects():
            if disk_object.getType() == 'DRBD':
                disk_object.setSyncState(True)

        if (vm_object.isRegisteredRemotely()):
            from mcvirt.cluster.cluster import Cluster
            cluster = Cluster(mcvirt_instance)
            remote_node = cluster.getRemoteNode(vm_object.getNode())

            # Stop the VM if it is running
            if (vm_object.getState() is PowerStates.RUNNING):
                remote_node.runRemoteCommand('virtual_machine-stop',
                                             {'vm_name': vm_object.getName()})
            # Remove VM from remote node
            remote_node.runRemoteCommand('virtual_machine-unregister',
                                         {'vm_name': vm_object.getName()})
            vm_object._setNode(None)

            # Manually register VM on local node
            vm_object.register()

            # Delete VM
            vm_object.delete(True)
        else:
            if (not vm_object.isRegisteredLocally()):
                print 'Warning: VM not registered'
                vm_object.register()

            if (vm_object.getLockState() is LockStates.LOCKED):
                vm_object.setLockState(LockStates(LockStates.UNLOCKED))

            if (vm_object.getState() is PowerStates.RUNNING):
                vm_object.stop()
            vm_object.delete(True)
