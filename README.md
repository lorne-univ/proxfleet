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
