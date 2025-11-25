import asyncio
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
        logging.debug("CSV validation successful. All entries are valid.")
        return True, []

def clone_csv(input_csv: str, config_yaml: str, proxmox_user: str, proxmox_password: str):
    """
    Clone all VMs defined in the CSV file that have an empty status.
    Updates the 'status' column with 'cloned' or 'error'.
    input_csv: file path (csv file)
    config_yaml: file path (proxmox server hostname)
    proxmox_user: user@pam // admin: 'root@pam'
    proxmox_password: password
    return: list[bool] - True if clone succeeded, False otherwise (one per CSV row)
    """  
    logging.debug(f"Starting VM cloning for file: {input_csv}")

    # 1. Load CSV data
    logging.debug(f"[STEP 1/5] Loading CSV file: {input_csv}")
    csv_handler = ProxmoxCSV(input_csv)
    delimiter = csv_handler.detect_delimiter()
    rows = csv_handler.read_csv(delimiter)
    if not rows:
        logging.error("CSV file is empty or unreadable.")
        return []

    # 2. Load YAML configuration
    logging.debug(f"[STEP 2/5] Loading configuration file: {config_yaml}")
    try:
        with open(config_yaml, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            servers = config.get("servers", [])
        logging.debug(f"Configuration loaded: {len(servers)} servers found.")
    except Exception as e:
        logging.error(f"Unable to load YAML config '{config_yaml}': {e}")
        return []

    # 3. Prepare Proxmox connections
    logging.debug("[STEP 3/5] Preparing Proxmox connections.")
    connections = {"user": proxmox_user,"password": proxmox_password}
    results_map = {}
    unique_hosts = set(row["target_host"] for row in rows if not row.get("status"))
    for target_host in unique_hosts:
        server_entry = next((s for s in servers if s["host"] == target_host), None)
        if not server_entry:
            logging.error(f"Server '{target_host}' not found in config.")
            for i, row in enumerate(rows):
                if row["target_host"] == target_host and not row.get("status"):
                    results_map[i] = {"success": False, "error": "Server not found in config", "row_index": i}
            continue
        proxmox_host = server_entry["usmb-tri"]
        try:
            manager = ProxmoxManager(proxmox_host, proxmox_user, proxmox_password)
            connections[target_host] = {"manager": manager, "proxmox_host": proxmox_host}
            logging.debug(f"Connected to {target_host} ({proxmox_host})")
        except Exception as e:
            logging.error(f"Failed to connect to {target_host}: {e}")
            for i, row in enumerate(rows):
                if row["target_host"] == target_host and not row.get("status"):
                    results_map[i] = {"success": False, "error": f"Connection failed: {e}", "row_index": i}

    # 4. Launch all clones
    logging.debug("[STEP 4/5] Launching clone operations.")
    clone_tasks = []
    results_map = {}
    for i, row in enumerate(rows):
        if row.get("status"):
            logging.debug(f"[{i+1}/{len(rows)}] Skipping '{row.get('vm_name', 'unknown')}' - already processed (status: {row['status']})")
            results_map[i] = {"success": True, "skipped": True, "row_index": i}
            continue
        target_host = row["target_host"]
        if target_host not in connections:
            logging.error(f"[{i+1}/{len(rows)}] No connection for host '{target_host}'")
            results_map[i] = {"success": False, "error": "No connection", "row_index": i}
            continue

        manager = connections[target_host]["manager"]
        proxmox_host = connections[target_host]["proxmox_host"]
        vm_name = row.get("vm_name")
        if not vm_name:
            student_login = row.get("student_login")
            if student_login:
                vm_name = student_login
            else:
                student_name = row.get("student_name", "")
                student_firstname = row.get("student_firstname", "")
                if student_name and student_firstname:
                    vm_name = f"{student_name}{student_firstname[0]}"
                else:
                    logging.error(f"[{i+1}/{len(rows)}] Unable to determine VM name for row {i+1}")
                    results_map[i] = {"success": False, "error": "No VM name", "row_index": i}
                    continue
        logging.debug(f"[{i+1}/{len(rows)}] VM name determined: {vm_name}")

        vm_temp = ProxmoxVM(proxmox_host, proxmox_user, proxmox_password, 0)
        template_name = row["template_name"]
        template_found, template_vmid = vm_temp.search_name(template_name, template=True)
        if not template_found:
            logging.error(f"[{i+1}/{len(rows)}] Template '{template_name}' not found on {target_host}")
            results_map[i] = {"success": False, "error": f"Template '{template_name}' not found", "row_index": i}
            continue
        logging.debug(f"[{i+1}/{len(rows)}] Template '{template_name}' found with VMID {template_vmid}")

        newid_str = row.get("newid", "").strip()
        if newid_str:
            try:
                newid = int(newid_str)
                logging.debug(f"[{i+1}/{len(rows)}] Using newid from CSV: {newid}")
            except ValueError:
                logging.warning(f"[{i+1}/{len(rows)}] Invalid newid '{newid_str}', using next available VMID")
                newid = manager.get_next_vmid()
        else:
            newid = manager.get_next_vmid()
            logging.debug(f"[{i+1}/{len(rows)}] Using next available VMID: {newid}")
        if newid is None:
            logging.error(f"[{i+1}/{len(rows)}] Unable to get next VMID")
            results_map[i] = {"success": False, "error": "Unable to get VMID", "row_index": i}
            continue

        vm_helper = ProxmoxVM(proxmox_host, proxmox_user, proxmox_password, template_vmid)
        vm_helper.template_vm = template_vmid
        vm_helper.newid = newid
        vm_helper.name_vm = vm_name
        vm_helper.pool_vm = row["pool"]
        vm_helper.storage_vm = row["storage"]
        logging.debug(f"[{i+1}/{len(rows)}] Launching clone: {vm_name} (template: {template_name}, newid: {newid})")
        upid = vm_helper.clone_vm()
        if upid:
            clone_tasks.append({"upid": upid, "row_index": i, "vm_name": vm_name, "manager": manager, "target_host": target_host, "vm_name_generated": vm_name, "newid_generated": newid})
            logging.debug(f"[{i+1}/{len(rows)}] Clone launched successfully → UPID: {upid}")
        else:
            logging.error(f"[{i+1}/{len(rows)}] Failed to launch clone for {vm_name}")
            results_map[i] = {"success": False, "error": "Clone launch failed", "row_index": i}
    logging.debug(f"Launch phase completed: {len(clone_tasks)} clones started")

    # 5. Monitor all clones in parallel
    if clone_tasks:
        logging.debug("[STEP 5/5] Monitoring clone progress in parallel.")   
        monitor_results = asyncio.run(_monitor_all_clones(clone_tasks))
        for result in monitor_results:
            row_index = result["row_index"]
            results_map[row_index] = result
    else:
        logging.debug("[STEP 5/5] No clones to monitor (all skipped or failed to launch)")

    # 6. Update CSV with results
    logging.debug("Updating CSV with clone results...")
    for i, row in enumerate(rows):
        result = results_map.get(i, {"success": False})
        if result.get("skipped"):
            continue
        elif result["success"]:
            row["status"] = "cloned"
            if result.get("vm_name_generated") and not row.get("vm_name"):
                row["vm_name"] = result["vm_name_generated"]
                logging.debug(f"Row {i+1}: Updated vm_name to '{result['vm_name_generated']}'")
            if result.get("newid_generated") and not row.get("newid"):
                row["newid"] = str(result["newid_generated"])
                logging.debug(f"Row {i+1}: Updated newid to '{result['newid_generated']}'")
        else:
            row["status"] = "error"
    header = csv_handler.read_header(delimiter)
    success = csv_handler.write_csv(rows, header, delimiter)
    if success:
        logging.debug(f"CSV updated successfully: {input_csv}")
    else:
        logging.error(f"Failed to update CSV: {input_csv}")

    # 7. Summary
    logging.debug("CLONE OPERATIONS COMPLETED")
    skipped = sum(1 for r in results_map.values() if r.get("skipped"))
    successes = sum(1 for r in results_map.values() if r["success"] and not r.get("skipped"))
    failures = len(rows) - skipped - successes 
    logging.debug(f"Total VMs in CSV: {len(rows)}")
    logging.debug(f"Skipped (already processed): {skipped}")
    logging.debug(f"Successfully cloned: {successes}")
    logging.debug(f"Failed: {failures}")
    if failures > 0:
        logging.debug("\nFailed VMs:")
        for i, result in results_map.items():
            if not result["success"] and not result.get("skipped"):
                vm_name = rows[i].get("vm_name", f"Row {i+1}")
                error = result.get("error", "Unknown error")
                logging.error(f"  - {vm_name}: {error}")
    return [results_map.get(i, {"success": False})["success"] for i in range(len(rows))]

async def _monitor_all_clones(clone_tasks):
    """
    Monitor all clone tasks in parallel.
    clone_tasks: list of dict (upid, row_index, vm_name, manager, target_host)
    return: list of results
    """
    monitoring_tasks = [
        _monitor_clone_task(clone_info)
        for clone_info in clone_tasks
    ]
    results = await asyncio.gather(*monitoring_tasks, return_exceptions=True)
    return results

async def _monitor_clone_task(clone_info, check_interval=5, timeout=900):
    """
    Monitor one clone task until completion.
    clone_info: dict with upid, row_index, vm_name, manager, target_host
    check_interval: seconds between status checks (default: 5)
    timeout: maximum wait time in seconds (default: 900 = 15 minutes)
    return: dict with success, row_index, error, elapsed
    """
    upid = clone_info["upid"]
    row_index = clone_info["row_index"]
    vm_name = clone_info["vm_name"]
    manager = clone_info["manager"]
    target_host = clone_info["target_host"]

    loop = asyncio.get_event_loop()
    start_time = loop.time()
    logging.debug(f"[{target_host}] Monitoring: {vm_name}")

    while True:
        elapsed = loop.time() - start_time
        if elapsed > timeout:
            logging.error(f"[{target_host}] Timeout for {vm_name} after {timeout}s")
            return {"success": False, "row_index": row_index, "error": f"Timeout after {timeout}s"}

        status, exitstatus = await loop.run_in_executor(None, manager.get_task_status, upid)
        if status is None:
            logging.error(f"[{target_host}] Unable to query status for {vm_name}")
            return {"success": False, "row_index": row_index, "error": "Unable to query task status"}
        if status == "stopped" and exitstatus == "OK":
            logging.debug(f"[{target_host}] Clone completed: {vm_name} ({int(elapsed)}s)")
            return {"success": True, "row_index": row_index, "elapsed": elapsed, "vm_name_generated": clone_info.get("vm_name_generated"), "newid_generated": clone_info.get("newid_generated")}
        elif status == "stopped":
            error_msg = exitstatus or "Unknown error"
            logging.error(f"[{target_host}] Clone failed: {vm_name} - {error_msg}")
            return {"success": False, "row_index": row_index, "error": error_msg}

        if int(elapsed) % 60 == 0 and int(elapsed) > 0:
            logging.debug(f"[{target_host}] {vm_name} still cloning... ({int(elapsed)}s)")
        await asyncio.sleep(check_interval)

def start_csv(csv_path: str, config_yaml: str, proxmox_user: str, proxmox_password: str):
    """
    Start all VMs defined in the CSV file that are stopped or cloned.
    Updates the 'status' column with 'running' or 'error'.
    
    csv_path: path to the CSV file containing VM configurations
    config_yaml: path to the YAML configuration file with server details
    proxmox_user: Proxmox username (e.g., 'root@pam')
    proxmox_password: Proxmox password
    
    return: list[bool] - True if start succeeded, False otherwise (one per CSV row)
    """
    logging.info("=" * 70)
    logging.info("STARTING VMs FROM CSV")
    logging.info("=" * 70)
    
    # 1. Load CSV data
    logging.debug(f"[STEP 1/4] Loading CSV file: {csv_path}")
    csv_handler = ProxmoxCSV(csv_path)
    delimiter = csv_handler.detect_delimiter()
    rows = csv_handler.read_csv(delimiter)
    
    if not rows:
        logging.error("CSV file is empty or unreadable.")
        return []
    
    logging.info(f"CSV file contains {len(rows)} rows.")
    
    # 2. Load YAML configuration
    logging.debug(f"[STEP 2/4] Loading configuration file: {config_yaml}")
    try:
        with open(config_yaml, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            servers = config.get("servers", [])
        logging.debug(f"Configuration loaded: {len(servers)} servers found.")
    except Exception as e:
        logging.error(f"Unable to load YAML config '{config_yaml}': {e}")
        return [False] * len(rows)
    
    # 3. Prepare Proxmox connections
    logging.debug("[STEP 3/4] Preparing Proxmox connections...")
    connections = {
        "user": proxmox_user,
        "password": proxmox_password
    }
    
    results_map = {}
    unique_hosts = set(row["target_host"] for row in rows if row.get("newid"))
    
    for target_host in unique_hosts:
        server_entry = next((s for s in servers if s["host"] == target_host), None)
        if not server_entry:
            logging.error(f"Server '{target_host}' not found in config.")
            for i, row in enumerate(rows):
                if row["target_host"] == target_host and row.get("newid"):
                    results_map[i] = False
            continue
        
        proxmox_host = server_entry["usmb-tri"]
        try:
            manager = ProxmoxManager(proxmox_host, proxmox_user, proxmox_password)
            connections[target_host] = {
                "manager": manager,
                "proxmox_host": proxmox_host
            }
            logging.info(f"Connected to {target_host} ({proxmox_host})")
        except Exception as e:
            logging.error(f"Failed to connect to {target_host}: {e}")
            for i, row in enumerate(rows):
                if row["target_host"] == target_host and row.get("newid"):
                    results_map[i] = False
    
    # 4. Start VMs
    logging.info("[STEP 4/4] Starting VMs...")
    logging.info("=" * 70)
    
    for i, row in enumerate(rows):
        newid_str = row.get("newid", "").strip()
        
        # Skip rows without newid
        if not newid_str:
            logging.debug(f"[{i+1}/{len(rows)}] Skipping row {i+1} - no newid")
            results_map[i] = True
            continue
        
        try:
            newid = int(newid_str)
        except ValueError:
            logging.error(f"[{i+1}/{len(rows)}] Invalid newid '{newid_str}'")
            results_map[i] = False
            row["status"] = "error"
            continue
        
        target_host = row["target_host"]
        vm_name = row.get("vm_name", f"VM-{newid}")
        
        # Skip if no connection
        if target_host not in connections:
            logging.error(f"[{i+1}/{len(rows)}] No connection for host '{target_host}'")
            results_map[i] = False
            row["status"] = "error"
            continue
        
        proxmox_host = connections[target_host]["proxmox_host"]
        
        # Create VM helper
        vm_helper = ProxmoxVM(proxmox_host, proxmox_user, proxmox_password, newid)
        
        # Check if VM exists
        exists, _ = vm_helper.search_vmid(newid)
        if not exists:
            logging.error(f"[{i+1}/{len(rows)}] VM {vm_name} (VMID: {newid}) not found on {target_host}")
            results_map[i] = False
            row["status"] = "error"
            continue
        
        # Check current status
        current_status = vm_helper.status()
        logging.debug(f"[{i+1}/{len(rows)}] VM {vm_name} current status: {current_status}")
        
        if current_status == "running":
            logging.info(f"[{i+1}/{len(rows)}] Skipping {vm_name} - already running")
            results_map[i] = True
            row["status"] = "running"
            continue
        
        # Start the VM
        logging.info(f"[{i+1}/{len(rows)}] Starting VM {vm_name} (VMID: {newid})...")
        success, upid = vm_helper.start()
        
        if not success or not upid:
            logging.error(f"[{i+1}/{len(rows)}] ✗ Failed to start VM {vm_name} - API call failed")
            results_map[i] = False
            row["status"] = "error"
            continue
        
        logging.debug(f"[{i+1}/{len(rows)}] Start task launched with UPID: {upid}")
        
        # Wait and check the task status
        manager = connections[target_host]["manager"]
        task_success = manager.check_task_stopped(upid, timeout_sec=60)
        
        if task_success:
            logging.info(f"[{i+1}/{len(rows)}] ✓ VM {vm_name} started successfully")
            results_map[i] = True
            row["status"] = "running"
        else:
            logging.error(f"[{i+1}/{len(rows)}] ✗ VM {vm_name} start task failed or timeout")
            results_map[i] = False
            row["status"] = "error"
    
    # 5. Save CSV
    header = csv_handler.read_header(delimiter)
    success = csv_handler.write_csv(rows, header, delimiter)
    
    if success:
        logging.info(f"CSV updated successfully: {csv_path}")
    else:
        logging.error(f"Failed to update CSV: {csv_path}")
    
    # 6. Summary
    logging.info("=" * 70)
    logging.info("START OPERATIONS COMPLETED")
    logging.info("=" * 70)
    
    total = len(rows)
    started = sum(1 for i, r in results_map.items() if r and rows[i].get("newid"))
    skipped = sum(1 for i in range(len(rows)) if not rows[i].get("newid"))
    failed = sum(1 for i, r in results_map.items() if not r)
    
    logging.info(f"Total VMs in CSV: {total}")
    logging.info(f"Successfully started: {started}")
    logging.info(f"Skipped (no newid): {skipped}")
    logging.info(f"Failed: {failed}")
    logging.info("=" * 70)
    
    return [results_map.get(i, True) for i in range(len(rows))]

def stop_csv(csv_path: str, config_yaml: str, proxmox_user: str, proxmox_password: str):
    """
    Stop all VMs defined in the CSV file that are running.
    Updates the 'status' column with 'stopped' or 'error'.
    Uses hard stop (not graceful shutdown).
    
    csv_path: path to the CSV file containing VM configurations
    config_yaml: path to the YAML configuration file with server details
    proxmox_user: Proxmox username (e.g., 'root@pam')
    proxmox_password: Proxmox password
    
    return: list[bool] - True if stop succeeded, False otherwise (one per CSV row)
    """
    logging.info("=" * 70)
    logging.info("STOPPING VMs FROM CSV")
    logging.info("=" * 70)
    
    # 1. Load CSV data
    logging.debug(f"[STEP 1/4] Loading CSV file: {csv_path}")
    csv_handler = ProxmoxCSV(csv_path)
    delimiter = csv_handler.detect_delimiter()
    rows = csv_handler.read_csv(delimiter)
    
    if not rows:
        logging.error("CSV file is empty or unreadable.")
        return []
    
    logging.info(f"CSV file contains {len(rows)} rows.")
    
    # 2. Load YAML configuration
    logging.debug(f"[STEP 2/4] Loading configuration file: {config_yaml}")
    try:
        with open(config_yaml, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            servers = config.get("servers", [])
        logging.debug(f"Configuration loaded: {len(servers)} servers found.")
    except Exception as e:
        logging.error(f"Unable to load YAML config '{config_yaml}': {e}")
        return [False] * len(rows)
    
    # 3. Prepare Proxmox connections
    logging.debug("[STEP 3/4] Preparing Proxmox connections...")
    connections = {
        "user": proxmox_user,
        "password": proxmox_password
    }
    
    results_map = {}
    unique_hosts = set(row["target_host"] for row in rows if row.get("newid"))
    
    for target_host in unique_hosts:
        server_entry = next((s for s in servers if s["host"] == target_host), None)
        if not server_entry:
            logging.error(f"Server '{target_host}' not found in config.")
            for i, row in enumerate(rows):
                if row["target_host"] == target_host and row.get("newid"):
                    results_map[i] = False
            continue
        
        proxmox_host = server_entry["usmb-tri"]
        try:
            manager = ProxmoxManager(proxmox_host, proxmox_user, proxmox_password)
            connections[target_host] = {
                "manager": manager,
                "proxmox_host": proxmox_host
            }
            logging.info(f"Connected to {target_host} ({proxmox_host})")
        except Exception as e:
            logging.error(f"Failed to connect to {target_host}: {e}")
            for i, row in enumerate(rows):
                if row["target_host"] == target_host and row.get("newid"):
                    results_map[i] = False
    
    # 4. Stop VMs
    logging.info("[STEP 4/4] Stopping VMs...")
    logging.info("=" * 70)
    
    for i, row in enumerate(rows):
        newid_str = row.get("newid", "").strip()
        
        # Skip rows without newid
        if not newid_str:
            logging.debug(f"[{i+1}/{len(rows)}] Skipping row {i+1} - no newid")
            results_map[i] = True
            continue
        
        try:
            newid = int(newid_str)
        except ValueError:
            logging.error(f"[{i+1}/{len(rows)}] Invalid newid '{newid_str}'")
            results_map[i] = False
            row["status"] = "error"
            continue
        
        target_host = row["target_host"]
        vm_name = row.get("vm_name", f"VM-{newid}")
        
        # Skip if no connection
        if target_host not in connections:
            logging.error(f"[{i+1}/{len(rows)}] No connection for host '{target_host}'")
            results_map[i] = False
            row["status"] = "error"
            continue
        
        proxmox_host = connections[target_host]["proxmox_host"]
        
        # Create VM helper
        vm_helper = ProxmoxVM(proxmox_host, proxmox_user, proxmox_password, newid)
        
        # Check if VM exists
        exists, _ = vm_helper.search_vmid(newid)
        if not exists:
            logging.error(f"[{i+1}/{len(rows)}] VM {vm_name} (VMID: {newid}) not found on {target_host}")
            results_map[i] = False
            row["status"] = "error"
            continue
        
        # Check current status
        current_status = vm_helper.status()
        logging.debug(f"[{i+1}/{len(rows)}] VM {vm_name} current status: {current_status}")
        
        if current_status == "stopped":
            logging.info(f"[{i+1}/{len(rows)}] Skipping {vm_name} - already stopped")
            results_map[i] = True
            row["status"] = "stopped"
            continue
        
        # Stop the VM (hard stop)
        logging.info(f"[{i+1}/{len(rows)}] Stopping VM {vm_name} (VMID: {newid})...")
        success, upid = vm_helper.stop()
        
        if not success or not upid:
            logging.error(f"[{i+1}/{len(rows)}] ✗ Failed to stop VM {vm_name} - API call failed")
            results_map[i] = False
            row["status"] = "error"
            continue
        
        logging.debug(f"[{i+1}/{len(rows)}] Stop task launched with UPID: {upid}")
        
        # Wait and check the task status
        manager = connections[target_host]["manager"]
        task_success = manager.check_task_stopped(upid, timeout_sec=60)
        
        if task_success:
            logging.info(f"[{i+1}/{len(rows)}] ✓ VM {vm_name} stopped successfully")
            results_map[i] = True
            row["status"] = "stopped"
        else:
            logging.error(f"[{i+1}/{len(rows)}] ✗ VM {vm_name} stop task failed or timeout")
            results_map[i] = False
            row["status"] = "error"
    
    # 5. Save CSV
    header = csv_handler.read_header(delimiter)
    success = csv_handler.write_csv(rows, header, delimiter)
    
    if success:
        logging.info(f"CSV updated successfully: {csv_path}")
    else:
        logging.error(f"Failed to update CSV: {csv_path}")
    
    # 6. Summary
    logging.info("=" * 70)
    logging.info("STOP OPERATIONS COMPLETED")
    logging.info("=" * 70)
    
    total = len(rows)
    stopped = sum(1 for i, r in results_map.items() if r and rows[i].get("newid"))
    skipped = sum(1 for i in range(len(rows)) if not rows[i].get("newid"))
    failed = sum(1 for i, r in results_map.items() if not r)
    
    logging.info(f"Total VMs in CSV: {total}")
    logging.info(f"Successfully stopped: {stopped}")
    logging.info(f"Skipped (no newid): {skipped}")
    logging.info(f"Failed: {failed}")
    logging.info("=" * 70)
    
    return [results_map.get(i, True) for i in range(len(rows))]

def delete_csv(csv_path: str, config_yaml: str, proxmox_user: str, proxmox_password: str):
    """
    Delete all VMs defined in the CSV file.
    Updates the CSV by clearing 'status' and 'ipv4' columns on success.
    
    csv_path: path to the CSV file containing VM configurations
    config_yaml: path to the YAML configuration file with server details
    proxmox_user: Proxmox username (e.g., 'root@pam')
    proxmox_password: Proxmox password
    
    return: list[bool] - True if delete succeeded, False otherwise (one per CSV row)
    """
    logging.info("=" * 70)
    logging.info("DELETING VMs FROM CSV")
    logging.info("=" * 70)
    
    # 1. Load CSV data
    logging.debug(f"[STEP 1/4] Loading CSV file: {csv_path}")
    csv_handler = ProxmoxCSV(csv_path)
    delimiter = csv_handler.detect_delimiter()
    rows = csv_handler.read_csv(delimiter)
    
    if not rows:
        logging.error("CSV file is empty or unreadable.")
        return []
    
    logging.info(f"CSV file contains {len(rows)} rows.")
    
    # 2. Load YAML configuration
    logging.debug(f"[STEP 2/4] Loading configuration file: {config_yaml}")
    try:
        with open(config_yaml, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            servers = config.get("servers", [])
        logging.debug(f"Configuration loaded: {len(servers)} servers found.")
    except Exception as e:
        logging.error(f"Unable to load YAML config '{config_yaml}': {e}")
        return [False] * len(rows)
    
    # 3. Prepare Proxmox connections
    logging.debug("[STEP 3/4] Preparing Proxmox connections...")
    connections = {
        "user": proxmox_user,
        "password": proxmox_password
    }
    
    results_map = {}
    unique_hosts = set(row["target_host"] for row in rows if row.get("newid"))
    
    for target_host in unique_hosts:
        server_entry = next((s for s in servers if s["host"] == target_host), None)
        if not server_entry:
            logging.error(f"Server '{target_host}' not found in config.")
            for i, row in enumerate(rows):
                if row["target_host"] == target_host and row.get("newid"):
                    results_map[i] = False
            continue
        
        proxmox_host = server_entry["usmb-tri"]
        try:
            manager = ProxmoxManager(proxmox_host, proxmox_user, proxmox_password)
            connections[target_host] = {
                "manager": manager,
                "proxmox_host": proxmox_host
            }
            logging.info(f"Connected to {target_host} ({proxmox_host})")
        except Exception as e:
            logging.error(f"Failed to connect to {target_host}: {e}")
            for i, row in enumerate(rows):
                if row["target_host"] == target_host and row.get("newid"):
                    results_map[i] = False
    
    # 4. Delete VMs
    logging.info("[STEP 4/4] Deleting VMs...")
    logging.info("=" * 70)
    
    for i, row in enumerate(rows):
        newid_str = row.get("newid", "").strip()
        
        # Skip rows without newid
        if not newid_str:
            logging.debug(f"[{i+1}/{len(rows)}] Skipping row {i+1} - no newid")
            results_map[i] = True
            continue
        
        try:
            newid = int(newid_str)
        except ValueError:
            logging.error(f"[{i+1}/{len(rows)}] Invalid newid '{newid_str}'")
            results_map[i] = False
            row["status"] = "error"
            continue
        
        target_host = row["target_host"]
        vm_name = row.get("vm_name", f"VM-{newid}")
        
        # Skip if no connection
        if target_host not in connections:
            logging.error(f"[{i+1}/{len(rows)}] No connection for host '{target_host}'")
            results_map[i] = False
            row["status"] = "error"
            continue
        
        proxmox_host = connections[target_host]["proxmox_host"]
        
        # Create VM helper
        vm_helper = ProxmoxVM(proxmox_host, proxmox_user, proxmox_password, newid)
        
        # Check if VM exists
        exists, _ = vm_helper.search_vmid(newid)
        if not exists:
            logging.warning(f"[{i+1}/{len(rows)}] VM {vm_name} (VMID: {newid}) not found on {target_host} - marking as success")
            results_map[i] = True
            row["status"] = ""
            row["ipv4"] = ""
            continue
        
        # Delete the VM
        logging.info(f"[{i+1}/{len(rows)}] Deleting VM {vm_name} (VMID: {newid})...")
        success, upid = vm_helper.delete()
        
        if not success or not upid:
            logging.error(f"[{i+1}/{len(rows)}] ✗ Failed to delete VM {vm_name} - API call failed")
            results_map[i] = False
            row["status"] = "error"
            continue
        
        logging.debug(f"[{i+1}/{len(rows)}] Delete task launched with UPID: {upid}")
        
        # Wait and check the task status
        manager = connections[target_host]["manager"]
        task_success = manager.check_task_stopped(upid, timeout_sec=120)
        
        if task_success:
            logging.info(f"[{i+1}/{len(rows)}] ✓ VM {vm_name} deleted successfully")
            results_map[i] = True
            row["status"] = ""
            row["ipv4"] = ""
            row["newid"] = ""
        else:
            logging.error(f"[{i+1}/{len(rows)}] ✗ VM {vm_name} delete task failed or timeout")
            results_map[i] = False
            row["status"] = "error"
    
    # 5. Save CSV
    header = csv_handler.read_header(delimiter)
    success = csv_handler.write_csv(rows, header, delimiter)
    
    if success:
        logging.info(f"CSV updated successfully: {csv_path}")
    else:
        logging.error(f"Failed to update CSV: {csv_path}")
    
    # 6. Summary
    logging.info("=" * 70)
    logging.info("DELETE OPERATIONS COMPLETED")
    logging.info("=" * 70)
    
    total = len(rows)
    deleted = sum(1 for i, r in results_map.items() if r and rows[i].get("newid"))
    skipped = sum(1 for i in range(len(rows)) if not rows[i].get("newid"))
    failed = sum(1 for i, r in results_map.items() if not r)
    
    logging.info(f"Total VMs in CSV: {total}")
    logging.info(f"Successfully deleted: {deleted}")
    logging.info(f"Skipped (no newid): {skipped}")
    logging.info(f"Failed: {failed}")
    logging.info("=" * 70)
    
    return [results_map.get(i, True) for i in range(len(rows))]

results = delete_csv(INPUT_CSV, CONFIG_YAML, proxmox_user, proxmox_password)
print(results)