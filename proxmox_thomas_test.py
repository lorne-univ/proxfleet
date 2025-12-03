from proxmox_thomas import *
from dotenv import load_dotenv
import logging
import os
import sys


# Load environment variables from the .env file
load_dotenv()

# Configuration file paths
CONFIG_YAML = "config.yaml"
INPUT_CSV = "test.csv"

# Retrieve information from the .env file
proxmox_user = os.getenv('PROXMOX_USER')
proxmox_password = os.getenv('PROXMOX_PASSWORD')

def test_full_deployment():
    """Full deployement : validation → clone → network → start → IPs → stop → delete"""
    print("\n" + "="*70)
    print("FULL DEPLOYMENT TEST")
    print("="*70 + "\n")

    # 1. Validate
    print("STEP 1/8: Validating CSV")
    valid, errors = check_csv(INPUT_CSV, CONFIG_YAML, proxmox_user, proxmox_password)
    if not valid:
        logging.error(f"Validation failed: {errors}")
        return False
    print("Validation OK\n")

    # 2. Clone
    print("STEP 2/8: Cloning VMs")
    clone_results = clone_csv(INPUT_CSV, CONFIG_YAML, proxmox_user, proxmox_password)
    if not all(clone_results):
        logging.warning("Some clones failed")
    print("Cloning OK\n")

    # 3. Network
    print("STEP 3/8: Configuring network bridges")
    network_results = networkbridge_csv(INPUT_CSV, CONFIG_YAML, proxmox_user, proxmox_password)
    if not all(network_results):
        logging.warning("Some network configs failed")
    print("Configuring OK\n")

    # 4. Start
    print("STEP 4/8: Starting VMs")
    start_results = start_csv(INPUT_CSV, CONFIG_YAML, proxmox_user, proxmox_password)
    if not all(start_results):
        logging.warning("Some VMs failed to start")
    print("Starting OK\n")

    # 5. Get IPs
    print("STEP 5/8: Getting management IPs")
    ip_results = managementip_csv(INPUT_CSV, CONFIG_YAML, proxmox_user, proxmox_password)
    if not all(ip_results):
        logging.warning("Some IPs not retrieved")
    print("IPs OK\n")

    # 6. Display IPs and wait for user validation
    print("STEP 6/8: Verification of IPs")
    from proxmox_csv import ProxmoxCSV
    csv_handler = ProxmoxCSV(INPUT_CSV)
    delimiter = csv_handler.detect_delimiter()
    rows = csv_handler.read_csv(delimiter)

    print(f"{'VMID':<5} {'IPv4 Address':<20} {'Status':<15}")
    print("-"*40)
    for row in rows:
        newid = row.get('newid', 'N/A')
        ipv4 = row.get('ipv4', 'N/A')
        status = row.get('status', 'N/A')
        print(f"{newid:<5} {ipv4:<20} {status:<15}")
    print("\n")

    # 7. Stop VMs
    print("STEP 7/8: Stopping VMs")
    stop_results = stop_csv(INPUT_CSV, CONFIG_YAML, proxmox_user, proxmox_password)
    if not all(stop_results):
        logging.warning("Some VMs failed to stop")
    print("Stopping OK\n")

    # 8. Delete VMs
    print("STEP 8/8: Deleting VMs")
    delete_results = delete_csv(INPUT_CSV, CONFIG_YAML, proxmox_user, proxmox_password)
    if not all(delete_results):
        logging.warning("Some VMs failed to delete")
    print("Deleting OK\n")

    print("="*70)
    print("FULL DEPLOYMENT TEST COMPLETED")
    print("="*70 + "\n")
    return True

def test_validation_only():
    """Test uniquement la validation du CSV"""
    print("\n" + "="*70)
    print("TEST VALIDATION ONLY")
    print("="*70 + "\n")
    
    valid, errors = check_csv(INPUT_CSV, CONFIG_YAML, proxmox_user, proxmox_password)
    if valid:
        print("CSV is valid!")
        return True
    else:
        print(f"CSV validation failed:")
        for error in errors:
            print(f"  Line {error['line']}: {error['errors']}")
        return False

def test_clone_only():
    """Test uniquement le clonage"""
    print("\n" + "="*70)
    print("TEST CLONE ONLY")
    print("="*70 + "\n")
    
    results = clone_csv(INPUT_CSV, CONFIG_YAML, proxmox_user, proxmox_password)
    success_count = sum(1 for r in results if r)
    print(f"\nClone completed: {success_count}/{len(results)} VMs cloned successfully")
    return all(results)

def test_start_only():
    """Test uniquement le démarrage des VMs"""
    print("\n" + "="*70)
    print("TEST START ONLY")
    print("="*70 + "\n")
    
    results = start_csv(INPUT_CSV, CONFIG_YAML, proxmox_user, proxmox_password)
    success_count = sum(1 for r in results if r)
    print(f"\nStart completed: {success_count}/{len(results)} VMs started")
    return all(results)

def test_stop_only():
    """Test uniquement l'arrêt des VMs"""
    print("\n" + "="*70)
    print("TEST STOP ONLY")
    print("="*70 + "\n")
    
    results = stop_csv(INPUT_CSV, CONFIG_YAML, proxmox_user, proxmox_password)
    success_count = sum(1 for r in results if r)
    print(f"\nStop completed: {success_count}/{len(results)} VMs stopped")
    return all(results)

def test_delete_only():
    """Test uniquement la suppression des VMs"""
    print("\n" + "="*70)
    print("TEST DELETE ONLY")
    print("="*70 + "\n")
    
    print("WARNING: This will DELETE all VMs in the CSV!")
    confirm = input("Type 'DELETE' to confirm: ")
    if confirm != "DELETE":
        print("Deletion cancelled")
        return False
    
    results = delete_csv(INPUT_CSV, CONFIG_YAML, proxmox_user, proxmox_password)
    success_count = sum(1 for r in results if r)
    print(f"\nDelete completed: {success_count}/{len(results)} VMs deleted")
    return all(results)

def test_network_only():
    """Test uniquement la configuration réseau"""
    print("\n" + "="*70)
    print("TEST NETWORK ONLY")
    print("="*70 + "\n")
    
    results = networkbridge_csv(INPUT_CSV, CONFIG_YAML, proxmox_user, proxmox_password)
    success_count = sum(1 for r in results if r)
    print(f"\nNetwork config completed: {success_count}/{len(results)} VMs configured")
    return all(results)

def test_ip_only():
    """Test uniquement la récupération des IPs"""
    print("\n" + "="*70)
    print("TEST IP RETRIEVAL ONLY")
    print("="*70 + "\n")
    
    results = managementip_csv(INPUT_CSV, CONFIG_YAML, proxmox_user, proxmox_password)
    success_count = sum(1 for r in results if r)
    print(f"\nIP retrieval completed: {success_count}/{len(results)} IPs retrieved")
    return all(results)

def show_menu():
    """Menu interactif pour choisir quel test lancer"""
    print("\n" + "="*70)
    print("PROXMOX THOMAS - MENU DE TEST")
    print("="*70)
    print(f"CSV File: {INPUT_CSV}")
    print("="*70)
    print("\nTests disponibles:")
    print("  1. Full deployment (validate → clone → network → start → IPs)")
    print("  2. Validation only")
    print("  3. Clone only")
    print("  4. Network configuration only")
    print("  5. Start VMs only")
    print("  6. Stop VMs only")
    print("  7. Get IPs only")
    print("  8. Delete VMs only")
    print("  0. Quit")
    print("="*70)
    
    choice = input("\nChoix [0-8]: ").strip()
    
    tests = {
        '1': test_full_deployment,
        '2': test_validation_only,
        '3': test_clone_only,
        '4': test_network_only,
        '5': test_start_only,
        '6': test_stop_only,
        '7': test_ip_only,
        '8': test_delete_only,
        '0': None
    }
    
    if choice == '0':
        return False
    elif choice in tests:
        tests[choice]()
        input("\n[Press Enter to continue...]")
        return True
    else:
        print("\nInvalid choice")
        input("\n[Press Enter to continue...]")
        return True

def main():   
    if not proxmox_user or not proxmox_password:
        logging.error("Missing PROXMOX_USER or PROXMOX_PASSWORD in .env file")
        sys.exit(1)
    
    # Si argument fourni, lancer le test correspondant
    if len(sys.argv) > 1:
        test_name = sys.argv[1].lower()
        tests = {
            'full': test_full_deployment,
            'validate': test_validation_only,
            'clone': test_clone_only,
            'network': test_network_only,
            'start': test_start_only,
            'stop': test_stop_only,
            'ip': test_ip_only,
            'delete': test_delete_only
        }
        
        if test_name in tests:
            tests[test_name]()
        else:
            print(f"Unknown test: {test_name}")
            print(f"Available tests: {', '.join(tests.keys())}")
            sys.exit(1)
    else:
        while show_menu():
            pass

if __name__ == "__main__":
    main()