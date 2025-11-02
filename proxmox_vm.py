import csv
import shutil
import time
import yaml
import logging
import ipaddress
from proxmox_manager import ProxmoxManager


class ProxmoxVM:
    def __init__(self, proxmox_host, proxmox_user, proxmox_password, vmid):
        """
        user: user@pam // admin: 'root@pam'
        password: password
        host: proxmox server hostname or IP
        vmid: id of the VM
        """
        self.vmid = int(vmid)
        self.nom_vm = str()
        self.pool_vm = str()
        self.template_vm = int()
        self.status_vm = str()
        self.storage_vm = str()
        self.interface_vm = dict()
        self.ipv4_address_vm = str()
        self.net0 = str()
        self.net1 = str()
        self.manager = ProxmoxManager(proxmox_host, proxmox_user, proxmox_password)

    def start(self):
        """
        Start virtual machine.
        """
        node = self.manager.proxmox.nodes.get()[0]["node"]
        try:
            self.manager.proxmox.nodes(node).qemu(self.vmid).status.start.post()
            return True
        except Exception as e:
            logging.error(f"Impossible de démarrer la VM {self.vmid}: {e}")
            return False
        
    def shutdown(self):
        """
        Shutdown virtual machine (ACPI event).
        """
        node = self.manager.proxmox.nodes.get()[0]["node"]
        try:
            self.manager.proxmox.nodes(node).qemu(self.vmid).status.shutdown.post()
            return True
        except Exception as e:
            logging.error(f"Impossible d'arrêter la VM {self.vmid}: {e}")
            return False

    def stop(self):
        """
        Stop virtual machine (hard power-off).
        """
        node = self.manager.proxmox.nodes.get()[0]["node"]
        try:
            self.manager.proxmox.nodes(node).qemu(self.vmid).status.stop.post()
            return True
        except Exception as e:
            logging.error(f"Impossible d'arrêter la VM {self.vmid}: {e}")
            return False

    def reboot(self):
        """
        Reboot the VM (soft reboot via ACPI).
        """
        node = self.manager.proxmox.nodes.get()[0]["node"]
        try:
            self.manager.proxmox.nodes(node).qemu(self.vmid).status.reboot.post()
            return True
        except Exception as e:
            logging.error(f"Impossible de redémarrer la VM {self.vmid}: {e}")
            return False

    def delete(self):
        """
        Destroy the VM and all used/owned volumes.
        """
        node = self.manager.proxmox.nodes.get()[0]["node"]
        try:
            self.manager.proxmox.nodes(node).qemu(self.vmid).delete()
            return True
        except Exception as e:
            logging.error(f"Impossible de supprimer la VM {self.vmid}: {e}")
            return False
        
    def status(self):
        """
        Get virtual machine status ('stopped' | 'running').
        """
        node = self.manager.proxmox.nodes.get()[0]["node"]
        try:
            info = self.manager.proxmox.nodes(node).qemu(self.vmid).status.current.get()
            return info.get("status")
        except Exception as e:
            logging.error(f"Impossible de récupérer le statut de la VM {self.vmid}: {e}")
            return "unknown"

    def status_agent(self):
        """
        QEMU Guest Agent is enabled in config ('1' | 'None').
        """
        node = self.manager.proxmox.nodes.get()[0]["node"]
        try:
            info_agent = self.manager.proxmox.nodes(node).qemu(self.vmid).status.current.get()
            return info_agent.get("agent")
        except Exception as e:
            logging.error(f"Impossible de récupérer le statut de l'agent de la VM {self.vmid}: {e}")
            return "unknown"

    def address(self, addr_type=None):
        """
        Return a dictionary in the form {interface: {'mac': mac_address, 'ip': [ip, ...]}} via the qemu-guest-agent.
        If the agent is not active, return {}.
        The parameter addr_type can be 'ipv4', 'ipv6', 'mac', or None.
        If None has passed, all information (mac and ip) will be returned.
        """
        node = self.manager.proxmox.nodes.get()[0]["node"]
        try:
            interfaces = self.manager.proxmox.nodes(node).qemu(self.vmid).agent("network-get-interfaces").get().get("result", [])
        except Exception as e:
            logging.error(f"Agent QEMU ne réponds pas pour la VM {self.vmid}: {e}")
            return {}
        result = {}
        for interface in interfaces:
            name = interface.get("name")
            if not name:
                continue
            mac = interface.get("hardware-address")
            if mac and addr_type in (None, "mac"):
                result[name] = {"mac": mac}
            if addr_type in (None, "ipv4", "ipv6"):
                ips = [
                    addr.get("ip-address")
                    for addr in interface.get("ip-addresses", [])
                    if addr_type is None or addr.get("ip-address-type") == addr_type]
                if ips:
                    result.setdefault(name, {})["ip"] = ips
        return result

    def set_network_bridges(self, bridge0: str | None = None, bridge1: str | None = None):
        """
        Updates the bridge configuration for network interfaces net0 and/or net1.
        Should be called while the VM is powered off.
        """
        node = self.manager.proxmox.nodes.get()[0]["node"]
        try:
            cfg = self.manager.proxmox.nodes(node).qemu(self.vmid).config.get()
        except Exception as e:
            logging.error(f"Impossible de récupérer la configuration de la VM {self.vmid}: {e}")
            return False
        def rebuild(existing: str | None, new_bridge: str) -> str:
            if not existing:
                return f"model=virtio,bridge={new_bridge}"
            parts = [p for p in existing.split(",") if not p.strip().startswith("bridge=")]
            parts.append(f"bridge={new_bridge}")
            return ",".join(parts)
        post_params = {}
        if bridge0:
            post_params["net0"] = rebuild(cfg.get("net0"), bridge0)
        if bridge1:
            post_params["net1"] = rebuild(cfg.get("net1"), bridge1)
        if post_params:
            try:
                self.manager.proxmox.nodes(node).qemu(self.vmid).config.post(**post_params)
                return True
            except Exception as e:
                logging.error(f"Erreur lors de la mise à jour des bridges de la VM {self.vmid}: {e}")
                return False

    def wait_for_task(self, node, upid: str, timeout_sec=300):
        """
        Wait for a Proxmox task (UPID) to finish, polling until completion or timeout.
        """
        if not isinstance(upid, str) or not upid.startswith("UPID:"):
            raise ValueError(f"Format d'UPID invalide: {upid}")
        start = time.time()
        while time.time() - start < timeout_sec:
            try:
                status = self.manager.proxmox.nodes(node).tasks(upid).status.get()
                if status.get("status") == "stopped":
                    return status
            except Exception as e:
                logging.error(f"Impossible d’interroger l’état de la tâche {upid}: {e}")
                return None
            time.sleep(2)
        logging.error(f"Délai dépassé : la tâche {upid} n’a pas terminé après {timeout_sec} secondes.")
        return None

    def clone_from_template(self, desired_newid=None):
        """
        Full clone from self.template_vm.
        Optionally applies custom net0/net1 bridges, starts the VM,
        waits until it's running, and retrieves the first IPv4 address
        within allowed subnets (192.168.140.0/23, 192.168.170.0/24, 192.168.176.0/24).
        If the QEMU Guest Agent is not enabled, the IP retrieval step is skipped.
        """
        allowed_subnets = [
            ipaddress.ip_network("192.168.140.0/23"),
            ipaddress.ip_network("192.168.170.0/24"),
            ipaddress.ip_network("192.168.176.0/24"),
        ]
        node = self.manager.proxmox.nodes.get()[0]["node"]
        tmpl = int(self.template_vm)
        newid = int(desired_newid) if desired_newid else int(self.manager.proxmox.cluster.nextid.get())
        params = {"newid": newid, "name": self.nom_vm, "full": 1}
        if self.pool_vm:
            params["pool"] = self.pool_vm
        if self.storage_vm:
            params["storage"] = self.storage_vm
        try:
            task = self.manager.proxmox.nodes(node).qemu(tmpl).clone.post(**params)
            self.wait_for_task(node, task)
        except Exception as e:
            logging.error(f"Erreur lors du clonage de la VM {self.nom_vm}: {e}")
            return False
        self.vmid = newid
        b0 = self.net0.strip() if isinstance(self.net0, str) else ""
        b1 = self.net1.strip() if isinstance(self.net1, str) else ""
        if b0 or b1:
            self.set_network_bridges(bridge0=b0 or None, bridge1=b1 or None)
        if not self.start():
            logging.error(f"Impossible de démarrer la VM {self.vmid}")
            return False
        for _ in range(60):  # ~120s
            time.sleep(2)
            st = self.status()
            if st == "running":
                self.status_vm = st
                break
        else:
            self.status_vm = st
            logging.warning(f"{self.nom_vm} ne semble pas 'running' après 60s")
        agent_status = self.status_agent()
        if str(agent_status) != "1":
            logging.info(f"Agent QEMU non activé sur la VM {self.nom_vm}, pas de détection IP.")
            return True
        ipv4_found = False
        for _ in range(80):  # ~240s
            time.sleep(3)
            try:
                interfaces = self.address("ipv4")
                if not interfaces:
                    continue
                for _, info in interfaces.items():
                    for ip in info.get("ip", []):
                        try:
                            ip_obj = ipaddress.ip_address(ip)
                            if any(ip_obj in net for net in allowed_subnets):
                                self.ipv4_address_vm = str(ip_obj)
                                ipv4_found = True
                                break
                        except ValueError:
                            continue
                    if ipv4_found:
                        break
                if ipv4_found:
                    break
            except Exception as e:
                logging.debug(f"IPv4 non disponible pour {self.nom_vm}: {e}")
                continue
        else:
            logging.warning(f"Aucune IPv4 détectée dans les sous-réseaux autorisés pour {self.nom_vm} après 60s.")
        return True

    @classmethod
    def clone_from_csv(cls, config_yaml, input_csv, proxmox_user, proxmox_password):
        """
        Clones all virtual machines defined in the given CSV file and writes the results
        to a new *_clone.csv file, including the VMID, IPv4 address, and status of each clone.
        """
        output_csv = input_csv.replace(".csv", "_clone.csv")
        shutil.copyfile(input_csv, output_csv)
        logging.info(f"Copie du CSV : {input_csv} → {output_csv}")
        with open(config_yaml, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        with open(output_csv, newline="", encoding="utf-8") as fin:
            rows = list(csv.DictReader(fin))
        fieldnames = ["target_host", "vm_name", "template_vmid", "pool", "storage",
            "newid", "net0", "net1", "ipv4", "status"]
        for row in rows:
            try:
                target_host   = (row.get("target_host") or "").strip()
                vm_name       = (row.get("vm_name") or "").strip()
                template_vmid = int(row.get("template_vmid") or 0)
                pool          = (row.get("pool") or "").strip()
                storage       = (row.get("storage") or "").strip()
                newid         = int(row["newid"]) if (row.get("newid") and str(row["newid"]).isdigit()) else None
                net0          = (row.get("net0") or "").strip()
                net1          = (row.get("net1") or "").strip()
                try:
                    proxmox_host = next(s["usmb-tri"] for s in config.get("servers", []) if s.get("host") == target_host)
                except StopIteration:
                    raise ValueError(f"Host '{target_host}' introuvable dans le fichier {config_yaml}")
                if not vm_name:
                    raise ValueError("Nom de VM manquant dans le CSV.")
                if template_vmid <= 0:
                    raise ValueError(f"Numéro de template invalide pour {vm_name}: {template_vmid}")
                vm = cls(proxmox_host, proxmox_user, proxmox_password, vmid=0)
                vm.nom_vm      = vm_name
                vm.pool_vm     = pool
                vm.template_vm = template_vmid
                vm.storage_vm  = storage
                vm.net0        = net0
                vm.net1        = net1
                vm.clone_from_template(desired_newid=newid)
                row["newid"]  = vm.vmid
                row["ipv4"]   = vm.ipv4_address_vm or ""
                row["status"] = vm.status_vm or ""
            except Exception as e:
                logging.error(f"Erreur avec {row.get('vm_name','?')}: {e}")
        with open(output_csv, "w", newline="", encoding="utf-8") as fout:
            writer = csv.DictWriter(fout, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                for k in fieldnames:
                    r.setdefault(k, "")
                writer.writerow({k: r.get(k, "") for k in fieldnames})
        logging.info(f"Terminé → CSV mis à jour : {output_csv}")
        return output_csv