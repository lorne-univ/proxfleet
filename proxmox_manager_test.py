import os
import logging
import dotenv
from ProxmoxManager import ProxmoxManager
import yaml


def test_create_user(
    proxmox_user="root@pam",
    proxmox_pass="password",
    serveur_name="pm-serv20.local.univ-savoie.fr",
    user="florn",
    group="admins",
):
    proxmox_manager = ProxmoxManager(serveur_name, proxmox_user, proxmox_pass)
    proxmox_manager.create_user(user, comment="Professeur USMB 2024-2025")


def test_add_user_to_group(
    proxmox_user="root@pam",
    proxmox_pass="password",
    serveur_name="pm-serv20.local.univ-savoie.fr",
    user="florn",
    group="admins",
):
    proxmox_manager = ProxmoxManager(serveur_name, proxmox_user, proxmox_pass)
    proxmox_manager.add_user_to_group(user, group)


def test_create_group(
    proxmox_user="root@pam",
    proxmox_pass="password",
    serveur_name="pm-serv20.local.univ-savoie.fr",
    group="admins",
):
    proxmox_manager = ProxmoxManager(serveur_name, proxmox_user, proxmox_pass)
    proxmox_manager.create_group(group, comment="Groupe des administrateurs")


def test_add_permission(
    proxmox_user="root@pam",
    proxmox_pass="password",
    serveur_name="pm-serv20.local.univ-savoie.fr",
    group="admins",
    path="/",
    roles=["PVEAdmin"],
):
    proxmox_manager = ProxmoxManager(serveur_name, proxmox_user, proxmox_pass)
    proxmox_manager.add_permission(ugid=group, path=path, roles=roles)


def test_add_role(
    proxmox_user="root@pam",
    proxmox_pass="password",
    serveur_name="pm-serv20.local.univ-savoie.fr",
    role="EtuPoolAdmin",
    privs=[
        "VM.Allocate",
        "VM.Audit",
        "VM.Clone",
        "VM.Backup",
        "VM.Clone",
        "VM.Config.CDROM",
        "VM.Config.CPU",
        "VM.Config.Cloudinit",
        "VM.Config.Disk",
        "VM.Config.HWType",
        "VM.Config.Memory",
        "VM.Config.Network",
        "VM.Config.Options",
        "VM.Console",
        "VM.Migrate",
        "VM.Monitor",
        "VM.PowerMgmt",
        "VM.Snapshot",
        "Datastore.AllocateSpace",
        "Datastore.Audit",
        "Sys.Modify",
        "Sys.Audit",
        "Pool.Allocate",
        "Pool.Audit",
    ],
):
    proxmox_manager = ProxmoxManager(serveur_name, proxmox_user, proxmox_pass)
    proxmox_manager.add_role(role, privs)


def test_add_pool_and_storage(
    proxmox_user="root@pam",
    proxmox_pass="password",
    serveur_name="pm-serv20.local.univ-savoie.fr",
    pool_id="florn",
    storage="data",
):
    proxmox_manager = ProxmoxManager(serveur_name, proxmox_user, proxmox_pass)
    proxmox_manager.add_pool_and_storage(pool_id, storage)


def test_get_network_interfaces(
    proxmox_user="root@pam",
    proxmox_pass="password",
    serveur_name="pm-serv16.local.univ-savoie.fr",
    vlan="170",
):
    proxmox_manager = ProxmoxManager(serveur_name, proxmox_user, proxmox_pass)
    interfaces = proxmox_manager.get_network_interfaces(vlan=vlan)
    logging.info(f"Network interfaces: {interfaces}")


def test_display_network_interfaces(
    proxmox_user="root@pam",
    proxmox_pass="password",
    serveur_name="pm-serv16.local.univ-savoie.fr",
):
    proxmox_manager = ProxmoxManager(serveur_name, proxmox_user, proxmox_pass)
    proxmox_manager.display_network_interfaces()


def test_add_net_interface(
    proxmox_user="root@pam",
    proxmox_pass="password",
    serveur_name="pm-serv16.local.univ-savoie.fr",
    interface_name="ens15f1np1",
    vlan_id=170,
):

    proxmox_manager = ProxmoxManager(serveur_name, proxmox_user, proxmox_pass)
    proxmox_manager.add_net_interface(interface_name=interface_name, vlan_id=vlan_id)


def test_add_net_vmbr(
    proxmox_user="root@pam",
    proxmox_pass="password",
    serveur_name="pm-serv20.local.univ-savoie.fr",
    vlan_id=140,
):
    proxmox_manager = ProxmoxManager(serveur_name, proxmox_user, proxmox_pass)
    proxmox_manager.add_net_vlan_vmbr(vlan_id)


def test_restore_backup(
    proxmox_user="root@pam",
    proxmox_pass="password",
    serveur_name="pm-serv20.local.univ-savoie.fr",
    backup_file="vzdump-qemu-100-2024_10_01-12_00_00.vma.zst",
    vm_id="",
    path="/mnt/pve/nas-tri/dump/",
):
    proxmox_manager = ProxmoxManager(serveur_name, proxmox_user, proxmox_pass)
    proxmox_manager.restore_backup(backup_file, vm_id, path=path)


def test_network_apply(
    proxmox_user="root@pam",
    proxmox_pass="password",
    serveur_name="pm-serv20.local.univ-savoie.fr",
):
    proxmox_manager = ProxmoxManager(serveur_name, proxmox_user, proxmox_pass)
    proxmox_manager.network_apply()


def test_add_net_vmbr(
    proxmox_user="root@pam",
    proxmox_pass="password",
    serveur_name="pm-serv20.local.univ-savoie.fr",
    vmbr_name="vmbr170",
    comment="Bridge for VLAN 170",
):
    proxmox_manager = ProxmoxManager(serveur_name, proxmox_user, proxmox_pass)
    proxmox_manager.add_net_vmbr(vmbr_name)


def test_delete_vm(
    proxmox_user="root@pam",
    proxmox_pass="password",
    serveur_name="pm-serv20.local.univ-savoie.fr",
    vmid=None,
):
    proxmox_manager = ProxmoxManager(serveur_name, proxmox_user, proxmox_pass)
    proxmox_manager.delete_vm(vmid=vmid)


if __name__ == "__main__":
    dotenv.load_dotenv()
    logging.basicConfig(level=logging.DEBUG)
    proxmox_user = os.getenv("PROXMOX_USER")
    proxmox_pass = os.getenv("PROXMOX_PASSWORD")
    target_host = "pm-serv20.local.univ-savoie.fr"

    # with open("config.yaml", "r") as f:
    #     config = yaml.safe_load(f)
    #

    #     vlan_interface = next(
    #         (
    #             srv["vlan_interface"]
    #             for srv in config["servers"]
    #             if srv["local"] == target_host
    #         ),
    #         None,
    #     )
    # test_create_user(proxmox_user=proxmox_user, proxmox_pass=proxmox_pass)
    # test_create_group(proxmox_user=proxmox_user, proxmox_pass=proxmox_pass)
    # test_add_user_to_group(proxmox_user=proxmox_user, proxmox_pass=proxmox_pass)
    # test_add_permission_to_group(proxmox_user=proxmox_user, proxmox_pass=proxmox_pass)
    # test_add_role(proxmox_user=proxmox_user, proxmox_pass=proxmox_pass)
    # test_add_pool_and_storage(proxmox_user=proxmox_user, proxmox_pass=proxmox_pass)
    # test_get_network_interfaces(proxmox_user=proxmox_user, proxmox_pass=proxmox_pass)
    # test_display_network_interfaces(
    #     proxmox_user=proxmox_user, proxmox_pass=proxmox_pass
    # )
    # test_add_net_interface(
    #     proxmox_user=proxmox_user,
    #     proxmox_pass=proxmox_pass,
    #     serveur_name=target_host,
    #     interface_name=vlan_interface,
    #     vlan_id=170,
    # )

    test_get_network_interfaces(
        proxmox_user=proxmox_user,
        proxmox_pass=proxmox_pass,
        serveur_name=target_host,
        vlan="140",
    )

    # test_add_net_vmbr(
    #     proxmox_user=proxmox_user,
    #     proxmox_pass=proxmox_pass,
    #     serveur_name=target_host,
    #     vlan_id=170,
    # )

    # test_restore_backup(
    #     proxmox_user=proxmox_user,
    #     proxmox_pass=proxmox_pass,
    #     serveur_name=target_host,
    #     backup_file="vzdump-qemu-101-2025_08_27-16_53_09.vma.zst",
    # )

    # test_network_apply(
    #     proxmox_user=proxmox_user, proxmox_pass=proxmox_pass, serveur_name=target_host
    # )
    # test_add_net_vmbr(
    #     proxmox_user=proxmox_user,
    #     proxmox_pass=proxmox_pass,
    #     serveur_name=target_host,
    #     vmbr_name="vmbrflorn1",
    #     comment="Bridge for florn",
    # )

    # test_restore_backup(
    #     proxmox_user=proxmox_user,
    #     proxmox_pass=proxmox_pass,
    #     serveur_name=target_host,
    #     backup_file="vzdump-qemu-500-2025_09_21-19_49_24.vma.zst",
    #     vm_id=500,
    #     path="/mnt/pve/nas-tri/dump/",
    # )

    # test_delete_vm(
    #     proxmox_user=proxmox_user,
    #     proxmox_pass=proxmox_pass,
    #     serveur_name=target_host,
    #     vmid=103,
    # )
