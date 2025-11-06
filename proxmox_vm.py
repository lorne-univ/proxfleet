import ipaddress
import logging
from proxmox_manager import ProxmoxManager


class ProxmoxVM:
    def __init__(self, proxmox_host, proxmox_user, proxmox_password, vmid):
        """
        user: user@pam // admin: 'root@pam'
        password: password
        host: proxmox server hostname or IP
        vmid: id of the VM
        ipv4_vm: detected management IPv4 address
        net0_vm / net1_vm: network bridges (e.g. vmbr140)
        """
        self.vmid = int(vmid)
        self.name_vm = str()
        self.pool_vm = str()
        self.template_vm = int()
        self.status_vm = str()
        self.storage_vm = str()
        self.ipv4_vm = str()
        self.manager = ProxmoxManager(proxmox_host, proxmox_user, proxmox_password)

    def start(self):
        """
        Start a virtual machine.
        vmid: self.vmid
        return: bool
        """
        node = self.manager.proxmox.nodes.get()[0]["node"]
        logging.debug(f"Attempting to start VM {self.vmid} on node {node}.")
        try:
            self.manager.proxmox.nodes(node).qemu(self.vmid).status.start.post()
            return True
        except Exception as e:
            logging.error(f"Unable to start VM {self.vmid}: {e}")
            return False

    def shutdown(self):
        """
        Shutdown virtual machine (ACPI event).
        vmid: self.vmid
        return: bool
        """
        node = self.manager.proxmox.nodes.get()[0]["node"]
        logging.debug(f"Attempting to shutdown VM {self.vmid} on node {node}.")
        try:
            self.manager.proxmox.nodes(node).qemu(self.vmid).status.shutdown.post()
            return True
        except Exception as e:
            logging.error(f"Unable to shutdown VM {self.vmid}: {e}")
            return False

    def stop(self):
        """
        Stop virtual machine (hard power-off).
        vmid: self.vmid
        return: bool
        """
        node = self.manager.proxmox.nodes.get()[0]["node"]
        logging.debug(f"Attempting to stop VM {self.vmid} on node {node}.")
        try:
            self.manager.proxmox.nodes(node).qemu(self.vmid).status.stop.post()
            return True
        except Exception as e:
            logging.error(f"Unable to stop VM {self.vmid}: {e}")
            return False

    def reboot(self):
        """
        Reboot the VM (soft reboot via ACPI).
        vmid: self.vmid
        return: bool
        """
        node = self.manager.proxmox.nodes.get()[0]["node"]
        logging.debug(f"Attempting to reboot VM {self.vmid} on node {node}.")
        try:
            self.manager.proxmox.nodes(node).qemu(self.vmid).status.reboot.post()
            return True
        except Exception as e:
            logging.error(f"Unable to reboot VM {self.vmid}: {e}")
            return False

    def delete(self):
        """
        Destroy the VM and all used/owned volumes.
        vmid: self.vmid
        return: bool
        """
        node = self.manager.proxmox.nodes.get()[0]["node"]
        logging.debug(f"Attempting to delete VM {self.vmid} on node {node}.")
        try:
            self.manager.proxmox.nodes(node).qemu(self.vmid).delete()
            return True
        except Exception as e:
            logging.error(f"Unable to delete VM {self.vmid}: {e}")
            return False

    def search_name(self, vm_name: str | None = None, template: bool = False):
        """
        Search for a virtual machine by name.
        vm_name: name of the VM to search (default: self.name_vm)
        template: if True, only search templates
        return: tuple (found [bool], vmid [int | None])
        """
        node = self.manager.proxmox.nodes.get()[0]["node"]
        target_name = str(vm_name or self.name_vm)
        logging.debug(f"Searching for VM by name '{target_name}' on node {node}, template={template}.")
        for vm in self.manager.proxmox.nodes(node).qemu.get():
            if vm.get("name") == target_name:
                if template and not vm.get("template"):
                    continue
                return True, vm.get("vmid")
        return False, None

    def search_vmid(self, vm_vmid: int | None = None, template: bool = False):
        """
        Search for a virtual machine by VMID.
        vm_vmid: VMID of the VM to search (default: self.vmid)
        template: if True, only search templates
        return: tuple (found [bool], name [str | None])
        """
        node = self.manager.proxmox.nodes.get()[0]["node"]
        target_vmid = int(vm_vmid or self.vmid)
        logging.debug(f"Searching for VM by VMID {target_vmid} on node {node}, template={template}.")
        for vm in self.manager.proxmox.nodes(node).qemu.get():
            if int(vm.get("vmid")) == target_vmid:
                if template and not vm.get("template"):
                    continue
                return True, vm.get("name")
        return False, None

    def status(self):
        """
        Get virtual machine status.
        vmid: self.vmid
        return: str ('stopped' | 'running' | 'unknown')
        """
        node = self.manager.proxmox.nodes.get()[0]["node"]
        logging.debug(f"Attempting to check status for VM {self.vmid} on node {node}.")
        try:
            return self.manager.proxmox.nodes(node).qemu(self.vmid).status.current.get().get("status")
        except Exception as e:
            logging.error(f"Unable to retrieve status for VM {self.vmid}: {e}")
            return "unknown"

    def status_agent(self):
        """
        Check if QEMU Guest Agent is enabled.
        vmid: self.vmid
        return: bool | str ('unknown')
        """
        node = self.manager.proxmox.nodes.get()[0]["node"]
        logging.debug(f"Attempting to check agent status for VM {self.vmid} on node {node}.")
        try:
            info_agent = self.manager.proxmox.nodes(node).qemu(self.vmid).status.current.get().get("agent")
            if info_agent == 1:
                return True
            else:
                return False
        except Exception as e:
            logging.error(f"Unable to retrieve agent status for VM {self.vmid}: {e}")
            return "unknown"

    def ping_agent(self):
        """
        Ping the QEMU Guest Agent inside the VM.
        vmid: self.vmid
        return: bool
        """
        node = self.manager.proxmox.nodes.get()[0]["node"]
        logging.debug(f"Pinging QEMU Guest Agent for VM {self.vmid} on node {node}.")
        try:
            self.manager.proxmox.nodes(node).qemu(self.vmid).agent("ping").post()
            return True
        except Exception as e:
            logging.warning(f"Unable to ping agent for VM {self.vmid}: {e}")
            return False

    def address(self, addr_type=None):
        """
        Get the network interfaces using the qemu-guest-agent.
        vmid: self.vmid
        addr_type: 'ipv4', 'ipv6', 'mac', or None (if None, both MAC and IP addresses will be returned)
        return: dict
            A dictionary in the form {interface: {'mac': mac_address, 'ip': [ip, ...]}}.
            If the agent is not active, return an empty dictionary {}.
        """
        node = self.manager.proxmox.nodes.get()[0]["node"]
        logging.debug(f"Attempting to retrieve network interfaces (addr_type={addr_type}) for VM {self.vmid} on node {node}.")
        try:
            interfaces = self.manager.proxmox.nodes(node).qemu(self.vmid).agent("network-get-interfaces").get().get("result", [])
        except Exception as e:
            logging.error(f"QEMU agent is not responding for VM {self.vmid}: {e}")
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

    def management_ip(self):
        """
        Get the management IPv4 address for the VM.
        The subnet priority follows the order defined in the `subnets` list below.
        vmid: self.vmid
        return: str
        """
        subnets = [
            ipaddress.ip_network("192.168.140.0/23"),
            ipaddress.ip_network("192.168.170.0/24"),
            ipaddress.ip_network("192.168.176.0/24"),]

        logging.debug(f"Searching for management IPv4 address (subnets: {subnets}) for VM {self.vmid}.")
        interfaces = self.address("ipv4")
        if not interfaces:
            logging.warning(f"No network interfaces detected for VM {self.vmid}.")
            return ""

        for subnet in subnets:
            for _, info in interfaces.items():
                for ip in info.get("ip", []):
                    try:
                        ip_obj = ipaddress.ip_address(ip)
                        if ip_obj in subnet:
                            self.ipv4_vm = str(ip_obj)
                            return self.ipv4_vm
                    except ValueError:
                        continue
        logging.warning(f"No management IPv4 found for VM {self.vmid}.")
        return ""

    def add_network_interface(self, model: str | None = None, bridge: str | None = None, firewall: bool | None = None):
        """
        Add a new network interface to the virtual machine.
        If model, bridge, and firewall are not specified, the method will copy
        the configuration (model, bridge, firewall) from the last existing interface.
        Should be called while the VM is powered off.
        model: Optional. Network card model (e.g. 'virtio', 'e1000').
        bridge: Optional. Bridge to attach (e.g. 'vmbr140').
        firewall: Optional. Enable firewall (True | False).
        return: bool
        """
        node = self.manager.proxmox.nodes.get()[0]["node"]
        logging.debug(f"Attempting to add network interface (model={model}, bridge={bridge}, firewall={firewall}) for VM {self.vmid} on node {node}.")

        try:
            cfg = self.manager.proxmox.nodes(node).qemu(self.vmid).config.get()
            next_index = 0
            while f"net{next_index}" in cfg:
                next_index += 1

            if model is None and bridge is None and firewall is None:
                last_index = next_index - 1
                last_net = cfg.get(f"net{last_index}")
                if not last_net:
                    logging.error(f"No existing network interface found to copy for VM {self.vmid}.")
                    return False
                parts = last_net.split(",")
                model = "virtio"
                bridge = None
                firewall = None

                for part in parts:
                    if part.startswith("virtio=") or part.startswith("e1000="):
                        model = part.split("=")[0]
                    elif part.startswith("bridge="):
                        bridge = part.split("=")[1]
                    elif part.startswith("firewall="):
                        firewall = part.split("=")[1] == "1"

            model = model or "virtio"
            bridge = bridge or "vmbr0"
            new_net = f"model={model},bridge={bridge}"
            if firewall:
                new_net += ",firewall=1"
            self.manager.proxmox.nodes(node).qemu(self.vmid).config.post(**{f"net{next_index}": new_net})
            return True

        except Exception as e:
            logging.error(f"Unable to add network interface to VM {self.vmid}: {e}")
            return False

    def set_network_bridge(self, net_name: str, new_bridge: str):
        """
        Update the bridge for a specific network interface (e.g., "net0", "net1", ...).
        Only the bridge is modified; all other parameters (model, MAC, firewall, etc.) remain unchanged.
        Should be called while the VM is powered off.
        net_name: Interface name (e.g., "net0", "net1")
        new_bridge: New bridge name (e.g., "vmbr140")
        return: bool
        """
        node = self.manager.proxmox.nodes.get()[0]["node"]
        logging.debug(f"Attempting to update bridge for {net_name} → {new_bridge} on VM {self.vmid} (node: {node}).")
        try:
            cfg = self.manager.proxmox.nodes(node).qemu(self.vmid).config.get()
            current_net = cfg.get(net_name)
            if not current_net:
                logging.error(f"Network interface {net_name} not found for VM {self.vmid}.")
                return False
            parts = current_net.split(",")
            updated_parts = []
            bridge_found = False

            for p in parts:
                if p.strip().startswith("bridge="):
                    updated_parts.append(f"bridge={new_bridge}")
                    bridge_found = True
                else:
                    updated_parts.append(p)

            if not bridge_found:
                logging.error(f"No bridge found in {net_name} configuration for VM {self.vmid}. Nothing was changed.")
                return False

            new_net_config = ",".join(updated_parts)
            self.manager.proxmox.nodes(node).qemu(self.vmid).config.post(**{net_name: new_net_config})
            logging.info(f"Bridge for {net_name} successfully updated to '{new_bridge}' on VM {self.vmid}.")
            return True

        except Exception as e:
            logging.error(f"Error while updating bridge for {net_name} on VM {self.vmid}: {e}")
            return False