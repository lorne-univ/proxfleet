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

## Git - Github

### Setup & Repository Status

| Command | Description | Example |
|--------|-------------|---------|
| `git config --global user.name "<name>"` | Set your Git username globally | `git config --global user.name "Thomas"` |
| `git config --global user.email "<email>"` | Set your Git email globally | `git config --global user.email "thomas@example.com"` |
| `git status` | Show the status of tracked/untracked files and staged changes | `git status` |
| `git fetch` | Retrieve latest changes from remote without merging | `git fetch origin` |
| `git pull` | Fetch and merge the latest changes from remote | `git pull origin main` |

### Branching & Development & Pushing Changes

| Command | Description | Example |
|--------|-------------|---------|
| `git checkout -b <branch-name>` | Create and switch to a new branch | `git checkout -b feature/api` |
| `git add <file>` | Stage file changes for commit | `git add README.md` |
| `git commit -m "<message>"` | Commit staged changes with a message | `git commit -m "Add login API"` |
| `git diff` | Show file differences before committing | `git diff` |
| `git push origin <branch-name>` | Push your branch and commits to remote | `git push origin feature/api` |

### Restoring & Maintenance

| Command | Description | Example |
|--------|-------------|---------|
| `git restore <file>` | Discard local changes to a file | `git restore config.yaml` |
| `git branch -d <branch-name>` | Delete a local branch after merging | `git branch -d feature/test-auth` |
| `git log` | Show commit history | `git log` |