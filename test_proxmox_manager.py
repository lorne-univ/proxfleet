import os
import yaml
import pytest
from dotenv import load_dotenv
from proxmox_manager import ProxmoxManager

@pytest.fixture(scope="session")
def proxmox_auth():
    # Charge les identifiants Proxmox (une seule fois pour la session)
    load_dotenv()
    proxmox_user = os.getenv("PROXMOX_USER")
    proxmox_password = os.getenv("PROXMOX_PASSWORD")
    if not proxmox_user or not proxmox_password:
        pytest.fail("Variables d'environnement PROXMOX_USER / PROXMOX_PASSWORD manquantes.")
    return proxmox_user, proxmox_password

def pytest_generate_tests(metafunc):
    # Génère automatiquement un test pour chaque hyperviseur défini dans config.yaml
    if "proxmox_host" in metafunc.fixturenames:
        with open("config.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        proxmox_hosts = []
        for server in config.get("servers", []):
            proxmox_host = server.get("usmb-tri")
            if proxmox_host:
                proxmox_hosts.append(proxmox_host)
        if not proxmox_hosts:
            pytest.skip("Aucun hyperviseur trouvé dans config.yaml (clé 'usmb-tri').")
        metafunc.parametrize("proxmox_host", proxmox_hosts)

@pytest.mark.parametrize("vlan", ["140", "170"])
class TestProxmoxManager:

    def test_get_network_interfaces(self, proxmox_host, proxmox_auth, vlan):
        # Vérifie que les VLANs spécifiés sont présents sur chaque hyperviseur
        proxmox_user, proxmox_password = proxmox_auth
        proxmox_manager = ProxmoxManager(proxmox_host, proxmox_user, proxmox_password)
        resultat = proxmox_manager.get_network_interfaces(vlan=vlan)
        assert len(resultat) > 0, f"{proxmox_host}: aucune interface trouvée pour VLAN {vlan}"