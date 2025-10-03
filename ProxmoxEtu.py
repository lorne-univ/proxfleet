from ProxmoxManager import ProxmoxManager


class ProxmoxEtu:
    """
    Privs to be placed on the student's pool
    This privs are used to create the EtuPoolAdmin role
    """

    ETUPOOLADMINPRIVS = [
        "VM.Allocate",
        "VM.Audit",
        "VM.Clone",
        "VM.Backup",
        "VM.Clone",
        "VM.Config.CDROM",
        "VM.Config.CPU",
        "VM.Config.Cloudinit",
        "VM.Config.Disk",
        "VM.Config.HWType",
        "VM.Config.Memory",
        "VM.Config.Network",
        "VM.Config.Options",
        "VM.Console",
        "VM.Migrate",
        "VM.Monitor",
        "VM.PowerMgmt",
        "VM.Snapshot",
        "Datastore.Audit",
        "Datastore.Allocate",
        "Datastore.AllocateSpace",
        "Datastore.AllocateTemplate",
        "Sys.Modify",
        "Sys.Audit",
        "Pool.Allocate",
        "Pool.Audit",
    ]
    """
    Privs to be placed on /
    These privs are used to create the EtuRoot role
    Privs corresponding to PVETEmpateUser + PVEAuditor on /
    """
    ETUROOTPRIVS = [
        "VM.Audit",
        "VM.Clone",
        "Datastore.Audit",
        "Mapping.Audit",
        "Sys.Audit",
        # "Pool.Audit", Non nécessaire
    ]

    def __init__(
        self,
        proxmox_host,
        proxmox_admin,
        proxmox_admin_password,
        etu_nom,
        etu_login,
        realm,
        promotion,
    ):
        self.proxmoxManager = ProxmoxManager(
            host=proxmox_host,
            proxmox_admin=proxmox_admin,
            proxmox_admin_password=proxmox_admin_password,
        )
        self.proxmox_host = proxmox_host
        self.etu_nom = etu_nom
        self.etu_login = etu_login
        self.promotion = promotion
        if realm == "":
            self.realm = "pam"
        else:
            self.realm = realm

    def create(self):
        """
        Create a student user, group, role, permission and pool on the Proxmox server.
        login: student login (e.g. "jdoe")
        promotion: student promotion (e.g. "m1tri-2024-2025")
        Student are in a group students with role PVETemplateUser and PVEAuditor on /
        Student have a pool.
        Student have EtuPoolAdmin role on their pool."""
        self.proxmoxManager.create_group("etudiants", comment="Group of all students")
        self.proxmoxManager.add_role("EtuPoolAdmin", self.ETUPOOLADMINPRIVS)
        self.proxmoxManager.add_role("EtuRoot", self.ETUROOTPRIVS)
        self.proxmoxManager.create_user(
            userid=self.etu_login,
            realm=self.realm,
            comment=f"{self.etu_nom} {self.promotion}",
        )
        self.proxmoxManager.add_pool_and_storage(
            poolid=self.etu_login, storage="data", comment="Pool of " + self.etu_login
        )
        self.proxmoxManager.add_permission(
            type="user",
            ugid=f"{self.etu_login}@{self.realm}",
            path=f"/pool/{self.etu_login}",
            roles="EtuPoolAdmin",
        )
        self.proxmoxManager.add_permission(
            type="group", ugid="etudiants", path="/", roles="EtuRoot"
        )
        self.proxmoxManager.add_permission(
            type="group", ugid="etudiants", path="/sdn", roles="PVESDNUser"
        )
        self.proxmoxManager.add_user_to_group(
            userid=self.etu_login, group="etudiants", realm=self.realm
        )
        self.proxmoxManager.add_net_vmbr(
            f"vmbr{self.etu_login}1",
            comments="Bridge for {self.etu_login}",
            apply=False,
        )
        self.proxmoxManager.add_net_vmbr(
            f"vmbr{self.etu_login}2",
            comments="Bridge for {self.etu_login}",
            apply=False,
        )
        self.proxmoxManager.add_net_vmbr(
            f"vmbr{self.etu_login}3",
            comments="Bridge for {self.etu_login}",
            apply=False,
        )
        self.proxmoxManager.add_net_vmbr(
            f"vmbr{self.etu_login}4",
            comments=f"Bridge for {self.etu_login}",
            apply=False,
        )
        self.proxmoxManager.network_apply()
