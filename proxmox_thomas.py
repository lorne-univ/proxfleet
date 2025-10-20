import os
from dotenv import load_dotenv
from proxmox_vm import ProxmoxVM

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Récupérer les informations du fichier .env
proxmox_host = os.getenv('PROXMOX_HOST')
proxmox_user = os.getenv('PROXMOX_USER')
proxmox_password = os.getenv('PROXMOX_PASSWORD')

# Connexion à l'API Proxmox via la classe ProxmoxVM
vm = ProxmoxVM(proxmox_host, proxmox_user, proxmox_password, vmid=109)

print(f"VM {vm.vmid} → état : {vm.status()}")
print("-"*70)
print(vm.address('ipv4'))
print(vm.address('ipv6'))
print(vm.address('mac'))
print("-"*70)
print(vm.address())
print("-"*70)
print(vm.address()['ens18']['ip'][0])