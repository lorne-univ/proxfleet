import logging
from proxmoxer import ProxmoxAPI


class ProxmoxVM:
    def __init__(self, host, proxmox_admin, proxmox_admin_password, vmid):
        """
        user: user@pam //admin user 'root@pam'
        password: password
        host: proxmox server hostname or IP
        """
        self.host = host
        self.vmid = int(vmid)
        self.proxmox = ProxmoxAPI(host, user=proxmox_admin, password=proxmox_admin_password, verify_ssl=True)

    def start(self):
        node = self.proxmox.nodes.get()[0]["node"]
        return self.proxmox.nodes(node).qemu(self.vmid).status.start.post()
        
    def shutdown(self):
        """Arrêt propre (ACPI)."""
        node = self.proxmox.nodes.get()[0]["node"]
        return self.proxmox.nodes(node).qemu(self.vmid).status.shutdown.post()

    def stop(self):
        """Arrêt forcé (équiv. power off)."""
        node = self.proxmox.nodes.get()[0]["node"]
        return self.proxmox.nodes(node).qemu(self.vmid).status.stop.post()

    def reboot(self):
        """Reboot via ACPI (soft)."""
        node = self.proxmox.nodes.get()[0]["node"]
        return self.proxmox.nodes(node).qemu(self.vmid).status.reboot.post()

    def delete(self):
        node = self.proxmox.nodes.get()[0]["node"]
        return self.proxmox.nodes(node).qemu(self.vmid).delete()
        
    def status(self):
        """
        Retourne l’état actuel de la VM (ex: 'running', 'stopped', 'paused').
        Utilise l’endpoint /nodes/{node}/qemu/{vmid}/status/current.
        """
        node = self.proxmox.nodes.get()[0]["node"]
        try:
            info = self.proxmox.nodes(node).qemu(self.vmid).status.current.get()
            return info.get("status", "unknown")
        except Exception as e:
            logging.error(f"Impossible de récupérer le statut de la VM {self.vmid}: {e}")
            return "unknown"

    def address(self, ip_type=None):
        """
        Retourne un dict {iface: {'mac': mac_address, 'ips': [ip, ...]}} via qemu-guest-agent si disponible.
        Si l'agent n'est pas actif, retourne {}.
        Le paramètre ip_type peut être 'ipv4', 'ipv6', 'mac' ou None.
        Si None est passé, toutes les informations (IP et MAC) sont retournées.
        """
        node = self.proxmox.nodes.get()[0]["node"]
        try:
            data = self.proxmox.nodes(node).qemu(self.vmid).agent("network-get-interfaces").get()
        except Exception as e:
            logging.debug(f"Agent non disponible pour {self.vmid} : {e}")
            return {}

        result = {}
        for iface in data.get("result", []):
            name = iface.get("name")
            mac_address = iface.get("hardware-address")
            addrs = []

            # Si ip_type est défini, filtrer par le type d'adresse (ipv4, ipv6, mac)
            if ip_type is None or ip_type == 'mac':
                # Si l'argument demandé est 'mac', on ajoute l'adresse MAC à l'interface
                if mac_address:
                    result[name] = {'mac': mac_address}
        
            # Récupérer les adresses IP de type spécifié si 'ipv4' ou 'ipv6' est passé
            if ip_type in ['ipv4', 'ipv6'] or ip_type is None:
                for addr in iface.get("ip-addresses", []):
                    if addr.get("ip-address-type") == ip_type or ip_type is None:
                        ip = addr.get("ip-address")
                        addrs.append(ip)

                if addrs:
                    if name not in result:
                        result[name] = {}

                    # Si on a trouvé des adresses IP, on les ajoute à la clé 'ip'
                    result[name]['ip'] = addrs

        return result