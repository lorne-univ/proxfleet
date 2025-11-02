import os
from dotenv import load_dotenv
from proxmox_vm import ProxmoxVM

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Chemins des fichiers de config
CONFIG_YAML = "config.yaml"
INPUT_CSV = "test.csv"

# Récupérer les informations du fichier .env
proxmox_user = os.getenv('PROXMOX_USER')
proxmox_password = os.getenv('PROXMOX_PASSWORD')

# Lance la clonage de VMs
ProxmoxVM.clone_from_csv(CONFIG_YAML, INPUT_CSV, proxmox_user, proxmox_password)