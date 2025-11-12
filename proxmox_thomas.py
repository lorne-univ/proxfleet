import logging
import os
import yaml
from dotenv import load_dotenv
from proxmox_manager import ProxmoxManager
from proxmox_vm import ProxmoxVM
from proxmox_csv import ProxmoxCSV


# Load environment variables from the .env file
load_dotenv()

# Configuration file paths
CONFIG_YAML = "config.yaml"
INPUT_CSV = "test.csv"

# Retrieve information from the .env file
proxmox_user = os.getenv('PROXMOX_USER')
proxmox_password = os.getenv('PROXMOX_PASSWORD')

def check_csv(input_csv: str, config_yaml: str, proxmox_user: str, proxmox_password: str):
    """
    Validate the content of a CSV file (before cloning VMs).
    input_csv: file path (csv file)
    config_yaml: file path (proxmox server hostname)
    proxmox_user: user@pam // admin: 'root@pam'
    proxmox_password: password
    return: tuple[bool, list[dict]] → if OK (True, []), else (False, [{"line": X, "errors": [list of failed fields]}])
    """
    logging.debug(f"Starting CSV validation for file: {input_csv}")

    # 1: Load the configuration file (YAML)
    logging.debug(f"[STEP 1] Loading configuration file: {config_yaml}")
    try:
        with open(config_yaml, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            servers = config.get("servers", [])
        logging.debug(f"Config loaded successfully with {len(servers)} Proxmox servers.")
    except Exception as e:
        logging.error(f"Unable to load YAML config '{config_yaml}': {e}")
        return False, [{"line": 0, "errors": ["config_yaml"]}]

    # 2: Read and parse the CSV file
    logging.debug(f"[STEP 2] Opening and reading CSV file: {input_csv}")
    csv_handler = ProxmoxCSV(input_csv)
    delimiter = csv_handler.detect_delimiter()
    logging.debug(f"Detected delimiter: '{delimiter}'")

    header = csv_handler.read_header(delimiter)
    logging.debug(f"Detected header: {header}")

    expected_columns = ["student_name","student_firstname","student_login","target_host","vm_name","template_name","pool","storage","newid","net0","net1","ipv4","status"]

    # Check that the header matches the expected structure
    if header != expected_columns:
        logging.error(f"Invalid CSV header. Expected: {expected_columns}, Found: {header}")
        return False, [{"line": 0, "errors": ["header"]}]

    rows = csv_handler.read_csv(delimiter)
    if not rows:
        logging.error("CSV is empty or unreadable.")
        return False, [{"line": 0, "errors": ["empty_csv"]}]

    logging.debug(f"CSV file contains {len(rows)} data rows.")

    # 3: Prepare Proxmox connections per target host
    logging.debug("[STEP 3] Preparing Proxmox connections per target host.")
    connections = {}
    errors = []

    # 4: Validate each CSV line
    logging.debug("[STEP 4] Starting per-line validation.")
    for i, row in enumerate(rows, start=2):  # line 2 = first data row
        line_errors = []
        logging.debug(f"--- Validating CSV line {i}: {row}")

        target_host = (row.get("target_host") or "").strip()
        student_name = (row.get("student_name") or "").strip()
        student_firstname = (row.get("student_firstname") or "").strip()
        student_login = (row.get("student_login") or "").strip()

        # Validate student identity
        if not ((student_name and student_firstname) or student_login):
            line_errors.append("student_identity")

        # Validate target host
        if not target_host:
            line_errors.append("target_host")
            errors.append({"line": i, "errors": line_errors})
            continue

        try:
            # Retrieve the matching host entry from config.yaml
            server_entry = next((s for s in servers if s.get("host") == target_host), None)
            if not server_entry:
                line_errors.append("target_host")
                errors.append({"line": i, "errors": line_errors})
                continue
            proxmox_host = server_entry.get("usmb-tri")
        except Exception as e:
            logging.error(f"Error retrieving host info for '{target_host}': {e}")
            line_errors.append("target_host")
            errors.append({"line": i, "errors": line_errors})
            continue

        # Reuse or create new Proxmox connection for the given host
        if target_host not in connections:
            try:
                logging.debug(f"Connecting to {proxmox_host} as {proxmox_user}")
                manager = ProxmoxManager(proxmox_host, proxmox_user, proxmox_password)
                vm_helper = ProxmoxVM(proxmox_host, proxmox_user, proxmox_password, 0)
                connections[target_host] = {"manager": manager, "vm": vm_helper}
                logging.debug(f"Connection established for host {target_host}")
            except Exception as e:
                logging.error(f"Unable to connect to {proxmox_host}: {e}")
                line_errors.append("connection_failed")
                errors.append({"line": i, "errors": line_errors})
                continue

        manager = connections[target_host]["manager"]
        vm_helper = connections[target_host]["vm"]

        # Validate template_name
        template_name = (row.get("template_name") or "").strip()
        if not template_name:
            line_errors.append("template_name")
        else:
            found, _ = vm_helper.search_name(template_name, template=True)
            if not found:
                line_errors.append("template_name")

        # Validate pool
        pool = (row.get("pool") or "").strip()
        if not pool or not manager.check_pool_exists(pool):
            line_errors.append("pool")

        # Validate storage
        storage = (row.get("storage") or "").strip()
        if not storage or not manager.check_storage_exists(storage):
            line_errors.append("storage")

        # Validate newid (optional)
        newid = (row.get("newid") or "").strip()
        if newid:
            try:
                newid_int = int(newid)
                exists, _ = vm_helper.search_vmid(newid_int)
                if exists:
                    line_errors.append("newid_conflict")
            except ValueError:
                line_errors.append("newid_invalid")

        # Validate network bridges (net0, net1…)
        for net_key in [k for k in row.keys() if k.startswith("net")]:
            bridge = (row.get(net_key) or "").strip()
            if bridge and not manager.check_bridge_exists(bridge):
                line_errors.append(net_key)

        # Store validation result for this line
        if line_errors:
            logging.debug(f"Line {i} invalid → {line_errors}")
            errors.append({"line": i, "errors": line_errors})
        else:
            logging.debug(f"Line {i} valid ✓")

    # 5: Final summary
    logging.debug("[STEP 5] CSV validation completed. Summarizing results.")
    if errors:
        logging.error(f"CSV validation failed with {len(errors)} invalid line(s).")
        for err in errors:
            logging.error(f"Line {err['line']}: {err['errors']}")
        return False, errors
    else:
        logging.info("CSV validation successful. All entries are valid.")
        return True, []

if __name__ == "__main__":
    result, errors = check_csv(INPUT_CSV, CONFIG_YAML, proxmox_user, proxmox_password)
    if result:
        print("CSV successfully validated")
    else:
        print("CSV contains errors:")
        for err in errors:
            print(f"  - Ligne {err['line']}: {', '.join(err['errors'])}")