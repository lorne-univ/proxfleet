# PROXFLEET

A set of tools to manage Proxmox Servers that are in a clusterless configuration.
The proxmoxer api is mainly used.

## Project Description

class ProxmoxManager

## Virtual environment
```
#In proxfleet directory
python -m venv venv
\proxfleet> .\venv\Scripts\Activate.ps1
```

## Environment variables
To set in .env file
```
PROXMOX_USER=root@pam
PROXMOX_PASSWORD=XXXX
```

## Informations

The Python library used is **proxmoxer**.  
The Proxmox API documentation is available here: [Proxmox API Documentation](https://pve.proxmox.com/pve-docs/api-viewer/index.html)