import os
from dotenv import load_dotenv
from proxmox_manager import ProxmoxManager

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Récupérer les informations du fichier .env
proxmox_host = os.getenv('PROXMOX_HOST')
proxmox_user = os.getenv('PROXMOX_USER')
proxmox_password = os.getenv('PROXMOX_PASSWORD')

# Classe pour tester les méthodes ProxmoxManager
class TestProxmoxManager:

    def test_ok_get_network_interfaces(self):
        # On teste qu'on reçoive bien une liste d'interfaces réseau
        proxmox_manager = ProxmoxManager(proxmox_host, proxmox_user, proxmox_password)
        interfaces = proxmox_manager.get_network_interfaces(vlan="all")
        assert len(interfaces) > 0, "La liste des interfaces ne doit pas être vide"
    
    def test_nok_get_network_interfaces(self):
        # On teste qu'on reçoive pas de liste car le vlan 150 n'existe pas
        proxmox_manager = ProxmoxManager(proxmox_host, proxmox_user, proxmox_password)
        interfaces = proxmox_manager.get_network_interfaces(vlan="150")
        assert len(interfaces) > 0, "La liste des interfaces ne doit pas être vide"