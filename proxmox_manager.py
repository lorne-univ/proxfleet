import logging
import time
from proxmoxer import ProxmoxAPI


class ProxmoxManager:
    def __init__(self, host, proxmox_admin, proxmox_admin_password):
        """
        user: user@pam //admin user 'root@pam'
        password: password
        host: proxmox server hostname or IP
        """
        self.host = host
        self.proxmox = ProxmoxAPI(
            host, user=proxmox_admin, password=proxmox_admin_password, verify_ssl=True
        )

    def list_vms(self):
        """
        List all VMs on the Proxmox server.
        Each server has only one node.
        """
        node = self.proxmox.nodes.get()[0]["node"]
        return self.proxmox.nodes(node).qemu.get()

    def list_users(self):
        """
        List all users on the Proxmox server.
        """
        return self.proxmox.access.users.get()

    def delete_usmb_users(self):
        """
        Delete all users containing "univ-smb" in their userid.
        This function was used during the first deployment of the Proxmox servers.
        """
        users = [u["userid"] for u in self.proxmox.access.users.get()]
        for user in users:
            if "univ-smb" in user:
                logging.debug("Delete user: {}".format(user))
                self.proxmox.access.users(user).delete()
                logging.info("User %s deleted.", user)

    def add_user_to_group(self, userid, group, realm="pam"):
        """
        Add an existing user to an existing group on the Proxmox server.
        userid: user id (e.g. "jdoe@pam")
        group: group id (e.g. "admins")
        """
        existing_users = self.proxmox.access.users.get()
        if not any(u["userid"] == f"{userid}@{realm}" for u in existing_users):
            logging.debug(f"User {userid}@{realm} does not exist on {self.host}.")
            return

        existing_groups = self.proxmox.access.groups.get()
        logging.debug("existing_groups: {}".format(existing_groups))
        if not any(g["groupid"] == group for g in existing_groups):
            logging.info(f"Group {group} does not exist on {self.host}.")
            return

        # Ajouter l'utilisateur au groupe
        self.proxmox.access.users(f"{userid}@{realm}").put(groups=[group])
        logging.info(f"User {userid}@{realm} added to group {group}.")

    def create_user(self, userid, realm="pam", comment=""):
        """
        Create a new user on the Proxmox server.
        userid: user id (e.g. "jdoe@pam")
        password: user password
        comment: optional comment
        """
        existing_users = self.proxmox.access.users.get()
        logging.debug("existing_users: {}".format(existing_users))
        if any(u["userid"] == f"{userid}@{realm}" for u in existing_users):
            logging.info(f"User {userid}@{realm} already exists on {self.host}.")
            return
        else:
            logging.info("Creating user: {}@{}".format(userid, realm))
            self.proxmox.access.users.post(userid=f"{userid}@{realm}", comment=comment)

    def create_group(self, groupid, comment=""):
        """
        Create a new group on the Proxmox server.
        groupid: group id (e.g. "admins")
        comment: optional comment
        """
        existing_groups = self.proxmox.access.groups.get()
        if any(g["groupid"] == groupid for g in existing_groups):
            logging.info(f"Group {groupid} already exists on {self.host}.")
            return
        else:
            logging.info("Creating group: {}".format(groupid))
            self.proxmox.access.groups.post(groupid=groupid, comment=comment)

    def get_network_interfaces(self, vlan="all"):
        """
        Get the network interfaces of the Proxmox server.
        If vlan is specified, return only the interfaces corresponding to the vlan.
        """
        node = self.proxmox.nodes.get()[0]["node"]
        interfaces = self.proxmox.nodes(node).network.get()
        if vlan == "all":
            logging.debug("Network interfaces: {}".format(interfaces))
            return interfaces
        else:
            vlan_interfaces = [
                iface for iface in interfaces if iface["iface"].endswith(f".{vlan}")
            ]
            logging.debug("VLAN {} Network interfaces: {}".format(vlan, vlan_interfaces))
            return vlan_interfaces

    def add_net_vmbr(self, vmbr_name, comments="", apply=True):
        """
        Add a virtual bridge interface to the Proxmox server.
        This is used to create internal bridge for student VMs.
        """
        logging.info(f"Adding virtual bridge {vmbr_name} on {self.host}")
        # Check if the bridge already exists
        interfaces_list = self.get_network_interfaces()
        if not any(iface["iface"] == vmbr_name for iface in interfaces_list):
            logging.info(f"Bridge {vmbr_name} does not exist on {self.host}.")
            node = self.proxmox.nodes.get()[0]["node"]
            self.proxmox.nodes(node).network().post(
                node=node,
                iface=vmbr_name,
                type="bridge",
                autostart=1,
                comments=comments,
            )
            if apply:
                self.network_apply()
        else:
            logging.info(f"Bridge {vmbr_name} already exists on {self.host}.")

    def add_net_vlan_vmbr(self, vlan_id, comments="", apply=True):
        """
        Add a bridge interface to the Proxmox server.
        The name of the bridge is vmbr{vlan_id}
        vlan_id: vlan id (e.g. "140")
            The bridge is connected to the interface corresponding to the vlan_id.
        The bridge is created only if it does not already exist.
        """
        bridge_name = f"vmbr{vlan_id}"

        interfaces_list = self.get_network_interfaces()

        # Check if the bridge already exists
        if not any(iface["iface"] == bridge_name for iface in interfaces_list):
            logging.info(f"Bridge {bridge_name} does not exist on {self.host}.")

            # Get the interface for the VLAN, the name of the interface ends with .{vlan_id}
            interface_vlan = self.get_network_interfaces(vlan=vlan_id)
            if len(interface_vlan) > 1 or len(interface_vlan) == 0:
                logging.error(
                    f"{len(interface_vlan)} interface(s) found for VLAN {vlan_id} on {self.host}: {interface_vlan}. Please check the configuration."
                )
                exit()

            node = self.proxmox.nodes.get()[0]["node"]

            self.proxmox.nodes(node).network.post(
                node=node,
                iface=bridge_name,
                type="bridge",
                autostart=1,
                bridge_ports=interface_vlan[0]["iface"],
            )
            logging.info(f"Bridge {bridge_name} created on {self.host}.")
            if apply:
                self.network_apply()
        else:
            logging.info(f"Bridge {bridge_name} already exists on {self.host}.")

    def add_net_interface(self, interface_name, vlan_id, apply=True):
        """
        Add a VLAN interface to the Proxmox server.
        The name of the interface is {interface_name}.{vlan_id}
        """
        logging.debug(
            f"Adding VLAN interface {interface_name}.{vlan_id} on {self.host}"
        )
        interfaces_list = self.get_network_interfaces(vlan=vlan_id)
        if len(interfaces_list) == 0:
            logging.info(f"Interface {interface_name}.{vlan_id} does not exist on {self.host}.")

            node = self.proxmox.nodes.get()[0]["node"]
            logging.debug(f"Creating interface {interface_name}.{vlan_id} on {node}")
            self.proxmox.nodes(node).network().post(
                node=node,
                iface=f"{interface_name}.{vlan_id}",
                type="vlan",
            )

            logging.info(f"VLAN interface {interface_name}.{vlan_id} created on {self.host}.")
            if apply:
                self.network_apply()
        else:
            logging.info(f"Interface {interface_name}.{vlan_id} already exists on {self.host}.")

    def network_apply(self):
        """
        Apply the network configuration on the Proxmox server.
        """
        node = self.proxmox.nodes.get()[0]["node"]
        self.proxmox.nodes(node).network().put(node=node)
        logging.info(f"Network configuration applied on {self.host}.")

    def display_network_interfaces(self):
        """
        Display the network interfaces of the Proxmox server.
        """
        interfaces = self.get_network_interfaces(vlan="all")
        for iface in interfaces:
            logging.info(f"Interface: {iface['iface']}, IP: {iface.get('cidr', 'N/A')}")

    def add_permission(self, type, ugid, path, roles):
        """
        Add permission to a group on the Proxmox server.
        type: 'group' or 'user'
        groupid: group id (e.g. "admins")
        path: path to the resource (e.g. "/vms/100")
        roles: list of roles to assign (e.g. ["PVEAdmin"])
        """
        existing_acl = self.proxmox.access.acl.get()
        logging.debug("existing_acl: {}".format(existing_acl))
        for acl in existing_acl:
            if acl["path"] == path and acl["ugid"] == ugid:
                logging.info(
                    f"ACL for {type} {ugid} on path {path} already exists on {self.host}."
                )
                return
        if type == "user":
            self.proxmox.access.acl.put(path=path, roles=roles, users=[ugid])
            logging.info(f"ACL : {roles} added for user {ugid} for path {path}.")
        elif type == "group":
            self.proxmox.access.acl.put(path=path, roles=roles, groups=[ugid])
            logging.info(f"ACL : {roles} added for group {ugid} for path {path}.")

    def add_role(self, roleid, privs):
        """
        Create a new role on the Proxmox server.
        roleid: role id (e.g. "PVEAdmin")
        privs: list of privileges (e.g. ["VM.Allocate", "VM.Audit"])
        comment: optional comment
        """
        existing_roles = self.proxmox.access.roles.get()
        if any(r["roleid"] == roleid for r in existing_roles):
            logging.info(f"Role {roleid} already exists on {self.host}.")
            return
        else:
            logging.info("Creating role: {}".format(roleid))
            self.proxmox.access.roles.post(roleid=roleid, privs=",".join(privs))

    def add_pool_and_storage(self, poolid, storage, comment=""):
        """
        Add a pool and storage

        poolid: pool id (e.g. "students")
        storageid: storage id (e.g. "local-lvm")
        """
        existing_storages = self.proxmox.storage.get()
        logging.debug(
            "Existing_storages on {}: {}".format(self.host, existing_storages)
        )
        if not any(s["storage"] == storage for s in existing_storages):
            logging.warning(f"Storage {storage} does not exist on {self.host}.")
            exit()

        existing_pools = self.proxmox.pools.get()
        logging.debug("Existing_pools on {}: {}".format(self.host, existing_pools))
        # Check if the pool already exists
        for pool in existing_pools:
            if pool["poolid"] == poolid:
                pool_members = self.proxmox.pools(poolid).get()
                logging.info(
                    f"Pool {poolid} already exists on {self.host}, members: {pool_members}."
                )

                if not any(storage in s["id"] for s in pool_members["members"]):
                    self.proxmox.pools(poolid).put(storage=[storage])
                    logging.info(f"Storage {storage} added to pool {poolid}.")
                else:
                    logging.info(f"Storage {storage} already exists on pool {poolid}.")
                    return
        # If the pool does not exist, create it and add the storage
        logging.info(f"Pool {poolid} does not exist on {self.host}.")
        logging.info("Creating pool: {}".format(poolid))
        self.proxmox.pools.post(poolid=poolid, comment=comment)
        self.proxmox.pools(poolid).put(storage=[storage])
        logging.info(f"Storage {storage} added to pool {poolid}.")

    def restore_backup(self, backup_file, vmid=None, path="/mnt/pve/nas-tri/dump/"):
        """
        Restore a backup on the Proxmox server.
        backup_id: backup id (e.g. "vzdump-qemu-100-2023_01_01-00_00_00.vma.zst")
        The backup must be present in the /var/lib/vz/dump/ directory.
        """
        # Filtpath exmaple : vzdump-qemu-105-2025_09_03-14_45_03.vma.zst
        node = self.proxmox.nodes.get()[0]["node"]

        if not vmid:
            vmid = self.proxmox.cluster.nextid.get()

        vms = self.proxmox.nodes(node).qemu.get()
        if any(vm["vmid"] == vmid for vm in vms):
            logging.info(f"VM {vmid} already exists on {node}")
            return

        self.proxmox.nodes(node).qemu.post(
            node=node,
            vmid=vmid,
            archive=f"{path}{backup_file}",
        )
        logging.info(f"Backup {backup_file} restored on {self.host}.")

    def get_task_status(self, upid: str):
        """
        Get the status of a Proxmox task (by UPID).
        upid: Task UPID, must start with "UPID:"
        return: tuple (status: str | None, exitstatus: str | None)
        """
        node = self.proxmox.nodes.get()[0]["node"]
        logging.debug(f"Checking status of task {upid} on node {node}.")
        if not isinstance(upid, str) or not upid.startswith("UPID:"):
            logging.error(f"Invalid UPID format: {upid}")
            raise ValueError(f"Invalid UPID format: {upid}")

        try:
            task_info = self.proxmox.nodes(node).tasks(upid).status.get()
            status = task_info.get("status")
            exitstatus = task_info.get("exitstatus")
            return status, exitstatus
        except Exception as e:
            logging.error(f"Unable to query the status of task {upid}: {e}")
            return None, None

    def check_task_stopped(self, upid: str, timeout_sec=300):
        """
        Check if a Proxmox task (by UPID) has stopped successfully.
        Blocks until the task is stopped or timeout is reached.
        upid: Task UPID, must start with "UPID:"
        timeout_sec: Maximum wait time in seconds (default 300)
        return: bool (True if task stopped with exitstatus == "OK", False otherwise)
        """
        node = self.proxmox.nodes.get()[0]["node"]
        logging.debug(f"Waiting for task {upid} to complete on node {node} (timeout: {timeout_sec}s).")
        if not isinstance(upid, str) or not upid.startswith("UPID:"):
            logging.error(f"Invalid UPID format: {upid}")
            raise ValueError(f"Invalid UPID format: {upid}")

        start = time.time()
        while time.time() - start < timeout_sec:
            try:
                task_info = self.proxmox.nodes(node).tasks(upid).status.get()
                status = task_info.get("status")
                exitstatus = task_info.get("exitstatus")
                if status == "stopped" and exitstatus == "OK":
                    return True
                elif status == "stopped":
                    error_msg = exitstatus or "Unknown error"
                    logging.error(f"Task {upid} failed with exitstatus: {error_msg}")
                    return False 
            except Exception as e:
                logging.error(f"Unable to query the status of task {upid}: {e}")
                return False
            time.sleep(2)
        logging.error(f"Timeout: task {upid} did not finish after {timeout_sec} seconds.")
        return False

    def check_bridge_exists(self, bridge_name: str):
        """
        Check if a network bridge exists.
        bridge_name: Name of the bridge to check
        return: bool
        """
        node = self.proxmox.nodes.get()[0]["node"]
        logging.debug(f"Checking if bridge '{bridge_name}' exists on node {node}.")
        try:
            interfaces = self.proxmox.nodes(node).network.get()
            return any(iface.get("iface") == bridge_name for iface in interfaces)
        except Exception as e:
            logging.error(f"Unable to verify bridge '{bridge_name}' on node {node}: {e}")
            return False

    def check_pool_exists(self, pool_name: str):
        """
        Check if a pool exists.
        pool_name: Name of the pool to check
        return: bool
        """
        logging.debug(f"Checking if pool '{pool_name}' exists.")
        try:
            pools = self.proxmox.pools.get()
            return any(pool.get("poolid") == pool_name for pool in pools)
        except Exception as e:
            logging.error(f"Unable to verify pool '{pool_name}': {e}")
            return False

    def check_storage_exists(self, storage_name: str):
        """
        Check if a storage exists.
        pool_name: Name of the storage to check
        return: bool
        """
        node = self.proxmox.nodes.get()[0]["node"]
        self.proxmox.nodes(node).qemu(vmid).delete()

