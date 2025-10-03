import ProxmoxEtu
import os
import dotenv
import logging


def test_create_etu(proxmox_user="root@pam", proxmox_pass="password"):
    proxmox_etu = ProxmoxEtu.ProxmoxEtu(
        proxmox_host="pm-serv20.local.univ-savoie.fr",
        proxmox_admin=proxmox_user,
        proxmox_admin_password=proxmox_pass,
        etu_login="etu_test2",
        etu_nom="etudiant2",
        realm="pam",
        promotion="24-25 test",
    )
    proxmox_etu.create()


## Creating local user :
# export user=etu_test2
# adduser --gecos "" --disabled-password ${user}
# echo "${user}:${user}" | chpasswd

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dotenv.load_dotenv(dotenv.find_dotenv())
    proxmox_user = os.getenv("PROXMOX_USER")
    proxmox_pass = os.getenv("PROXMOX_PASSWORD")
    test_create_etu(proxmox_user=proxmox_user, proxmox_pass=proxmox_pass)
