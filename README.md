# PROXFLEET

A set of tools to manage Proxmox Servers that are in a clusterless configuration.

## Informations

The Python library used is **proxmoxer**.  
The Proxmox API documentation is available here: [Proxmox API Documentation](https://pve.proxmox.com/pve-docs/api-viewer/index.html)

## Project Description

### Classes

- **ProxmoxCSV** - Handles CSV file parsing and writing
- **ProxmoxManager** - Handles connection and cluster-level operations (pools, storage, bridges, tasks)
- **ProxmoxVM** - Handles VM-level operations (clone, start, stop, delete, network, QEMU agent)

### Bulk Operations

- **bulk_vm_management** - High-level functions to manage multiple VMs from a CSV file
- **bulk_vm_management_main** - CLI interface for bulk operations

### Virtual environment

In proxfleet directory
```bash
python -m venv venv
```

Windows (PowerShell)
```powershell
.\venv\scripts\activate.ps1
```

Linux / macOS
```bash
source venv/bin/activate
```

Librairies for the projet
```bash
pip install -r requirements.txt
```

### CSV Template

The program detects the delimiter (`;` by default, or `,`).
```
student_name;student_firstname;student_login;target_host;vm_name;template_name;pool;storage;newid;net0;net1;ipv4;status
```

## How to use

### Environment Variables Authentication

Create a `.env` file:

**For Password:**
```bash
export PROXMOX_USER=root@pam
export PROXMOX_PASSWORD=myPassword123
```

**For Token:**
```bash
export PROXMOX_USER=root@pam
export PROXMOX_USE_TOKEN=true
export PROXMOX_TOKEN_NAME=token
export PROXMOX_TOKEN_VALUE=123456789ABCDEF
```

### Basic syntax

```bash
python bulk_vm_management_main.py -f 'file.csv' -a 'action' [options]
```

## Docker Reference

### Prerequisites

- Docker installed on your system

- All project files in the proxfleet/ directory

### Build the Docker Image

Navigate to the project directory and build the image:

```bash
cd proxfleet/
docker build --platform linux/amd64 -t proxfleet:latest .
```

### Verify the Build

Check that the image was created successfully:

```bash
docker images | grep proxfleet
```

### Test the Image

```bash
docker run --rm proxfleet:latest --help
```

### Running with Docker

```bash
docker run --rm \
  --platform linux/amd64 \
  --network host \
  -v $(pwd)/YOUR_FILE.csv:/app/YOUR_FILE.csv:rw \
  -e PROXMOX_USER=your_user@pam \
  -e PROXMOX_USE_TOKEN=true \
  -e PROXMOX_TOKEN_NAME=your_token_name \
  -e PROXMOX_TOKEN_VALUE=your_token_value \
  proxfleet:latest \
  -f YOUR_FILE.csv -a ACTION --debug LEVEL
```

**Explanation of flags:**

- **--rm** : *Automatically remove container after execution*
- **--platform linux/amd64** : *Ensure AMD64 architecture compatibility*
- **--network host** : *Use host network (required to access Proxmox servers)*
- **-v $(pwd)/file.csv:/app/file.csv:rw** : *Mount CSV file with read-write permissions*
- **-e VARIABLE=value** : *Set environment variables for authentication*
- **-f file.csv** : *CSV file to process (inside container path)*
- **-a ACTION** : *Action to perform*
- **--debug LEVEL** : *Debug level (none, info, debug)*

### Docker Examples

**Example 1: Validate CSV**

```bash
docker run --rm --platform linux/amd64 --network host -v $(pwd)/test.csv:/app/test.csv:rw -e PROXMOX_USER=root@pam -e PROXMOX_USE_TOKEN=true -e PROXMOX_TOKEN_NAME=token -e PROXMOX_TOKEN_VALUE=xxx-xxx-xxx proxfleet:latest -f test.csv -a validation
```

**Example 2: Full Deployment Workflow**

```bash
docker run --rm --platform linux/amd64 --network host -v $(pwd)/test.csv:/app/test.csv:rw -e PROXMOX_USER=root@pam -e PROXMOX_USE_TOKEN=true -e PROXMOX_TOKEN_NAME=token -e PROXMOX_TOKEN_VALUE=xxx-xxx-xxx proxfleet:latest -f test.csv -a deployment
```

**Example 3: Stop VMs**

```bash
docker run --rm --platform linux/amd64 --network host -v $(pwd)/test.csv:/app/test.csv:rw -e PROXMOX_USER=root@pam -e PROXMOX_USE_TOKEN=true -e PROXMOX_TOKEN_NAME=token -e PROXMOX_TOKEN_VALUE=xxx-xxx-xxx proxfleet:latest -f test.csv -a stop
```

**Example 4: Delete VMs**

```bash
docker run --rm --platform linux/amd64 --network host -v $(pwd)/test.csv:/app/test.csv:rw -e PROXMOX_USER=root@pam -e PROXMOX_USE_TOKEN=true -e PROXMOX_TOKEN_NAME=token -e PROXMOX_TOKEN_VALUE=xxx-xxx-xxx proxfleet:latest -f test.csv -a delete
```

## CLI Arguments Reference

### Required Arguments

| Argument | Short | Description | Example |
|----------|-------|-------------|---------|
| `--file` | `-f` | Path to the CSV file | `-f students.csv` |
| `--action` | `-a` | Action to perform (see table below) | `-a validation` |

### Optional Arguments

| Argument | Short | Description | Default | Example |
|----------|-------|-------------|---------|---------|
| `--debug` | - | Debug level: `none`, `info`, `debug` | `info` | `--debug debug` |

### Authentication Arguments

#### Common

| Argument | Short | Description | Env Variable | Example |
|----------|-------|-------------|--------------|---------|
| `--user` | `-u` | Proxmox username (e.g., `root@pam`) | `PROXMOX_USER` | `-u root@pam` |

#### Password Authentication

| Argument | Short | Description | Env Variable | Example |
|----------|-------|-------------|--------------|---------|
| `--password` | `-p` | Proxmox password | `PROXMOX_PASSWORD` | `-p myPassword123` |

#### Token Authentication

| Argument | Short | Description | Env Variable | Example |
|----------|-------|-------------|--------------|---------|
| `--use-token` | - | Enable token authentication (flag) | `PROXMOX_USE_TOKEN` | `--use-token` |
| `--token-name` | - | API token name (only part after `!`) | `PROXMOX_TOKEN_NAME` | `--token-name token` |
| `--token-value` | - | API token secret value | `PROXMOX_TOKEN_VALUE` | `--token-value xxx-xxx-xxx` |

### Available Actions

| Action | Description | CSV Updates | Required VM State |
|--------|-------------|-------------|-------------------|
| `validation` | Validate CSV format and configuration | None | N/A |
| `clone` | Clone VMs from templates | status, vm_name, newid | N/A |
| `network_bridge` | Configure network bridges (net0, net1) | None | Any |
| `start` | Start stopped VMs | status | stopped |
| `stop` | Stop running VMs (hard power-off) | status | running |
| `delete` | Delete VMs permanently | status, ipv4, newid | stopped |
| `management_ip` | Retrieve management IP addresses | ipv4 | running |
| `deployment` | Full workflow (validation → clone → network → start → IPs) | All | N/A |

### Password Authentication

```bash
python bulk_vm_management_main.py \
  -f students.csv \
  -u root@pam \
  -p myPassword123 \
  -a validation
```

### Token Authentication

```bash
python bulk_vm_management_main.py \
  -f students.csv \
  -u root@pam \
  --use-token \
  --token-name token \
  --token-value xxx-xxx-xxx \
  -a validation
```
 
## Python Library Usage

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
from bulk_vm_management import check_csv

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
from bulk_vm_management import clone_csv

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
from bulk_vm_management import networkbridge_csv

results = networkbridge_csv(INPUT_CSV, CONFIG_YAML, user, password)
```

**Result:** VMs configured with specified bridges.

### 4. start_csv()

Starts stopped VMs.

**Code:**
```python
from bulk_vm_management import start_csv

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
from bulk_vm_management import stop_csv

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
from bulk_vm_management import delete_csv

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
from bulk_vm_management import managementip_csv

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
from bulk_vm_management import *

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
2. Click **"Pull requests"**.  
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