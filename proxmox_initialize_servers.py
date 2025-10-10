import yaml
import logging
from proxmox_manager import ProxmoxManager
import os
import dotenv

dotenv.load_dotenv()
proxmox_user = os.getenv("PROXMOX_USER")
proxmox_password = os.getenv("PROXMOX_PASSWORD")

"""
Initialize servers config but not STUDENT see manage_users_server.py

"""


def initialize_vlan_interfaces():
    """Create interfaces and bridges on all servers listed in config.yaml"""
    logging.info(f"Initializing network interfaces for all servers")
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
        servers_list = [srv["local"] for srv in config["servers"]]
        logging.debug("Servers_lists : {}".format(servers_list))
        for server in servers_list:

            logging.info("Initializing network interfaces for server: %s", server)
            proxmox_manager = ProxmoxManager(server, proxmox_user, proxmox_password)

            trunk_interface = next(
                (
                    srv["vlan_interface"]
                    for srv in config["servers"]
                    if srv["local"] == proxmox_manager.host
                ),
            )
            logging.debug(
                f"Trunk interface for {proxmox_manager.host}: {trunk_interface}"
            )
            proxmox_manager.add_net_interface(
                interface_name=trunk_interface, vlan_id=140
            )
            proxmox_manager.add_net_interface(
                interface_name=trunk_interface, vlan_id=170
            )
            proxmox_manager.add_net_vlan_vmbr(vlan_id=140)
            proxmox_manager.add_net_vlan_vmbr(vlan_id=170)
            proxmox_manager.network_apply()
            logging.info("Completed initialization for server: %s", server)


def initialize_vmbr_etu():
    logging.info(f"Initializing network interfaces for all servers")
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
        servers_list = [srv["local"] for srv in config["servers"]]
        logging.debug("Servers_lists : {}".format(servers_list))
        for server in servers_list:

            logging.info("Initializing network interfaces for server: %s", server)
            proxmox_manager = ProxmoxManager(server, proxmox_user, proxmox_password)

            proxmox_manager.add_net_vmbr(vmbr_name="vmbretu")
            proxmox_manager.network_apply()
            logging.info("Completed initialization for server: %s", server)


def restore_template_from_backup(backup_file, path="/mnt/pve/nas-tri/dump/"):
    """Restore a VM template from a backup
    baclup_file format :  vzdump-qemu-500-2025_09_21-19_49_24.vma.zst
    500 -> id du backup
    """
    logging.info("Initializing VM template from backup")

    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
        servers_list = [srv["local"] for srv in config["servers"]]

    try:
        parts = backup_file.split("-")
        if len(parts) < 2:
            raise ValueError("Format de chaîne inattendu")
        vm_id = int(parts[2])
    except ValueError:
        print(f"Error during extracting vm_id")
        exit(2)

    for server in servers_list:
        logging.info("Restoring template on server: %s", server)
        proxmox_manager = ProxmoxManager(server, proxmox_user, proxmox_password)
        proxmox_manager.restore_backup(
            backup_file, vmid=vm_id, path="/mnt/pve/nas-tri/dump/"
        )
        logging.info("Completed template creation for server: %s", server)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # initialize_vlan_interfaces()
    # initialize_vmbr_etu()
    # restore_template_from_backup("vzdump-qemu-501-2025_09_25-10_08_26.vma.zst")
    restore_template_from_backup("vzdump-qemu-502-2025_09_26-16_19_12.vma.zst")
