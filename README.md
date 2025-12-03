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

## How to use

### Setup
```python
import os
from dotenv import load_dotenv

load_dotenv()
CONFIG_YAML = "config.yaml"
INPUT_CSV = "test.csv"
user = os.getenv('PROXMOX_USER')
password = os.getenv('PROXMOX_PASSWORD')
```

### Methods

| Method | Purpose | Required VM State | Updates CSV |
|--------|---------|-------------------|-------------|
| `check_csv()` | Validate CSV before operations | N/A | No |
| `clone_csv()` | Clone VMs from templates | N/A | status, vm_name, newid |
| `networkbridge_csv()` | Configure network bridges | Any | No |
| `start_csv()` | Start VMs | stopped | status |
| `stop_csv()` | Stop VMs | running | status |
| `delete_csv()` | Delete VMs permanently | stopped | status, ipv4, newid |
| `managementip_csv()` | Retrieve management IPs | running | ipv4 |

### 1. check_csv()

Validates CSV file.

**Input:**
```python
from proxmox_thomas import check_csv

valid, errors = check_csv(INPUT_CSV, CONFIG_YAML, user, password)
```

**Output:**
```python
# Success
(True, [])

# Failure
(False, [{"line": 2, "errors": ["template_name", "pool"]}, 
         {"line": 3, "errors": ["target_host"]}])
```

### 2. clone_csv()

Clones VMs in parallel. Auto-generates vm_name and newid if empty.

**Input CSV:**
```csv
student_name;student_firstname;student_login;target_host;vm_name;template_name;pool;storage;newid;net0;net1;ipv4;status
Dupont;Jean;DupontJ;serveur;vm-test;ubuntu-template;students;local-lvm;;;;;
```

**Code:**
```python
from proxmox_thomas import clone_csv

results = clone_csv(INPUT_CSV, CONFIG_YAML, user, password)
# Returns: [True, True, False, ...]
```

**Output CSV:**
```csv
student_name;student_firstname;student_login;target_host;vm_name;template_name;pool;storage;newid;net0;net1;ipv4;status
Dupont;Jean;DupontJ;serveur;vm-test;ubuntu-template;students;local-lvm;100;;;;cloned
```

### 3. networkbridge_csv()

Configures network interfaces from net0/net1 columns.

**Input CSV:**
```csv
...;newid;net0;net1;...
...;100;bridge1;brdige2;...
```

**Code:**
```python
from proxmox_thomas import networkbridge_csv

results = networkbridge_csv(INPUT_CSV, CONFIG_YAML, user, password)
```

**Result:** VMs configured with specified bridges.

### 4. start_csv()

Starts stopped VMs.

**Code:**
```python
from proxmox_thomas import start_csv

results = start_csv(INPUT_CSV, CONFIG_YAML, user, password)
```

**CSV Update:**
```csv
...;status
...;running
```

### 5. stop_csv()

Stops running VMs (hard power-off).

**Code:**
```python
from proxmox_thomas import stop_csv

results = stop_csv(INPUT_CSV, CONFIG_YAML, user, password)
```

**CSV Update:**
```csv
...;status
...;stopped
```

### 6. delete_csv()

Deletes stopped VMs. Irreversible operation.

**Code:**
```python
from proxmox_thomas import delete_csv

# Must stop VMs first
stop_csv(INPUT_CSV, CONFIG_YAML, user, password)
results = delete_csv(INPUT_CSV, CONFIG_YAML, user, password)
```

**CSV Update:**
```csv
...;newid;ipv4;status
...;;;
```

### 7. managementip_csv()

Retrieves IPs from running VMs. Requires QEMU Guest Agent.

**Code:**
```python
from proxmox_thomas import managementip_csv

results = managementip_csv(INPUT_CSV, CONFIG_YAML, user, password)
```

**CSV Update:**
```csv
...;ipv4;status
...;192.168.1.1;running
```

**Timeout:** 3 minutes per VM.

### Complete workflow
```python
from proxmox_thomas import *

# 1. Validate
valid, errors = check_csv(INPUT_CSV, CONFIG_YAML, user, password)
if not valid:
    exit(1)

# 2. Clone
clone_csv(INPUT_CSV, CONFIG_YAML, user, password)

# 3. Configure network
networkbridge_csv(INPUT_CSV, CONFIG_YAML, user, password)

# 4. Start
start_csv(INPUT_CSV, CONFIG_YAML, user, password)

# 5. Get IPs
managementip_csv(INPUT_CSV, CONFIG_YAML, user, password)
```

Or run the automated script:
```bash
python proxmox_thomas.py
```

## Git - Github

To contribute to the project, follow this simple workflow.
If this is your first time working on the project:
```
git clone https://github.com/lorne-univ/proxfleet.git
cd proxfleet
```

If you already cloned it before, **make sure to get the latest version**:
```
git checkout main
git pull origin main
```

<ins>Do not work directly on the `main` branch.</ins>
All development must be done in a **separate branch**:
```
git checkout -b feature/<your-feature-name>
```

Edit or add your files as needed. To add a file:
```
git add <filename>
```

Always write a clear and short message explaining what was done:
```
git commit -m "<message>"
```

Push your branch to GitHub:
```
git push origin feature/<your-feature-name>
```

Create a Pull Request (PR):
1. Go to the GitHub repository page.  
2. Click **“Pull requests”**.  
3. Add a short but clear description of your changes.  
4. Submit your PR for review.

PRs must be reviewed and approved by me before merging into `main`.

After the pull request has been approved, delete the local branch:
```
git branch -d feature/<your-feature-name>
```

Delete the remote branch:
```
git push origin --delete feature/<your-feature-name>
```

Switch back to main and update it:
```
git checkout main
git pull origin main
```

### Useful Git Commands

| Command | Description | Example |
|----------|-------------|---------|
| `git status` | Check modified and staged files | `git status` |
| `git fetch origin` | Get latest info from remote | `git fetch origin` |
| `git pull origin main` | Get latest main branch | `git pull origin main` |
| `git diff` | Show unstaged differences | `git diff` |
| `git log` | Show commit history | `git log` |
| `git branch -d <branch>` | Delete a local branch | `git branch -d feature/test-api` |
| `git restore <file>` | Discard local changes | `git restore config.yaml` |