from bulk_vm_management import *
from dotenv import load_dotenv
import argparse
import logging
import os
import sys


def get_args(argv=None):
    """
    Parse command-line arguments.
    return: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(prog="Proxmox VM Bulk Management", description="Manage Proxmox VMs from CSV file.", epilog="For more information, visit: https://github.com/lorne-univ/proxfleet")
    parser.add_argument("-f", "--file", dest="csv_file", required=True, help="Path to the CSV file containing VM configurations")
    parser.add_argument(
        "-a", "--action",
        dest="action",
        required=True,
        choices=["validation", "clone", "start", "stop", "delete", "network_bridge", "management_ip", "deployment"],
        help="""Action to perform:
  validation     : Validate CSV file before operations
  clone          : Clone VMs from templates
  start          : Start VMs
  stop           : Stop VMs
  delete         : Delete VMs (must be stopped first)
  network_bridge : Configure network bridges
  management_ip  : Retrieve management IP addresses
  deployment     : Full deployment (validation + clone + network_bridge + start + management_ip)""")
    auth_group = parser.add_argument_group('Authentication (Password or Token)')
    auth_group.add_argument("-u", "--user", dest="proxmox_user", help="Proxmox username (e.g., root@pam). Can also use PROXMOX_USER environment variable")
    auth_group.add_argument("-p", "--password", dest="proxmox_password", help="Proxmox password (for password authentication). Can also use PROXMOX_PASSWORD environment variable")
    auth_group.add_argument("--use-token", dest="use_token", action="store_true", default=False, help="Use token authentication instead of password. Can also use PROXMOX_USE_TOKEN=true environment variable")
    auth_group.add_argument("--token-name", dest="token_name", help="API token name (required if --use-token is set). Can also use PROXMOX_TOKEN_NAME environment variable")
    auth_group.add_argument("--token-value", dest="token_value", help="API token value (required if --use-token is set). Can also use PROXMOX_TOKEN_VALUE environment variable")
    parser.add_argument("--debug", dest="debug", choices=["info", "debug", "none"], default="info", help="Debug level: info (default), debug (verbose), none (quiet)")
    return parser

def get_credentials_from_env_or_args(args):
    """
    Get authentication credentials from command-line arguments or environment variables.
    Command-line arguments take precedence over environment variables.
    args: Parsed command-line arguments
    return: Authentication parameters
    """
    proxmox_user = args.get("proxmox_user") or os.getenv("PROXMOX_USER")
    use_token = args.get("use_token", False) or os.getenv("PROXMOX_USE_TOKEN", "false").lower() == "true"
    if use_token:
        token_name = args.get("token_name") or os.getenv("PROXMOX_TOKEN_NAME")
        token_value = args.get("token_value") or os.getenv("PROXMOX_TOKEN_VALUE")
        return {
            "proxmox_user": proxmox_user,
            "proxmox_password": None,
            "use_token": True,
            "token_name": token_name,
            "token_value": token_value}
    else:
        proxmox_password = args.get("proxmox_password") or os.getenv("PROXMOX_PASSWORD")
        return {
            "proxmox_user": proxmox_user,
            "proxmox_password": proxmox_password,
            "use_token": False,
            "token_name": None,
            "token_value": None}

def validate_credentials(creds):
    """
    Validate that all required credentials are present.
    creds: Authentication credentials
    return: (tuple) is_valid, error_message
    """
    if not creds["proxmox_user"]:
        return False, "Missing Proxmox user. Provide via -u/--user or PROXMOX_USER environment variable"
    if creds["use_token"]:
        if not creds["token_name"]:
            return False, "Token mode enabled but token name missing. Provide via --token-name or PROXMOX_TOKEN_NAME"
        if not creds["token_value"]:
            return False, "Token mode enabled but token value missing. Provide via --token-value or PROXMOX_TOKEN_VALUE"
        logging.info(f"Using TOKEN authentication (user: {creds['proxmox_user']}, token: {creds['token_name']})")
    else:
        if not creds["proxmox_password"]:
            return False, "Password mode but password missing. Provide via -p/--password or PROXMOX_PASSWORD"
        logging.info(f"Using PASSWORD authentication (user: {creds['proxmox_user']})")
    return True, None

def validate_files(csv_file, config_yaml):
    """
    Validate that required files exist.
    csv_file: Path to CSV file
    config_yaml: Path to YAML config file
    return: (tuple) is_valid, error_message
    """
    if not os.path.exists(csv_file):
        return False, f"CSV file not found: {csv_file}"
    if not os.path.exists(config_yaml):
        return False, f"Config file not found: {config_yaml}"
    return True, None

def execute_action(action, csv_file, config_yaml, creds):
    """
    Execute the specified action.
    action: Action to perform
    csv_file: Path to CSV file
    config_yaml: Path to YAML config
    creds: Authentication credentials
    return: True if action succeeded, False otherwise
    """
    logging.info(f"Executing action: {action.upper()}")
    logging.info(f"CSV file: {csv_file}")
    logging.info(f"Config file: {config_yaml}")
    print("=" * 50)
    try:
        if action == "validation":
            logging.info("Validating CSV file...")
            valid, errors = check_csv(csv_file, config_yaml, **creds)
            if valid:
                print("\nCSV validation SUCCESSFUL")
                logging.info("CSV validation passed")
                return True
            else:
                print("\nCSV validation FAILED")
                logging.error(f"CSV validation failed with {len(errors)} error(s):")
                for error in errors:
                    logging.error(f"Line {error['line']}: {error['errors']}")
                return False
        
        elif action == "clone":
            logging.info("Cloning VMs...")
            results = clone_csv(csv_file, config_yaml, **creds)
            success_count = sum(1 for r in results if r)
            print(f"\nCloned {success_count}/{len(results)} VMs successfully")
            logging.info(f"Clone operation completed: {success_count}/{len(results)} successful")
            return all(results)
        
        elif action == "start":
            logging.info("Starting VMs...")
            results = start_csv(csv_file, config_yaml, **creds)
            success_count = sum(1 for r in results if r)
            print(f"\nStarted {success_count}/{len(results)} VMs successfully")
            logging.info(f"Start operation completed: {success_count}/{len(results)} successful")
            return all(results)
        
        elif action == "stop":
            logging.info("Stopping VMs...")
            results = stop_csv(csv_file, config_yaml, **creds)
            success_count = sum(1 for r in results if r)
            print(f"\nStopped {success_count}/{len(results)} VMs successfully")
            logging.info(f"Stop operation completed: {success_count}/{len(results)} successful")
            return all(results)
        
        elif action == "delete":
            logging.info("Deleting VMs...")
            results = delete_csv(csv_file, config_yaml, **creds)
            success_count = sum(1 for r in results if r)
            print(f"\nDeleted {success_count}/{len(results)} VMs successfully")
            logging.info(f"Delete operation completed: {success_count}/{len(results)} successful")
            return all(results)
        
        elif action == "network_bridge":
            logging.info("Configuring network bridges...")
            results = networkbridge_csv(csv_file, config_yaml, **creds)
            success_count = sum(1 for r in results if r)
            print(f"\nConfigured {success_count}/{len(results)} VMs successfully")
            logging.info(f"Network bridge configuration completed: {success_count}/{len(results)} successful")
            return all(results)
        
        elif action == "management_ip":
            logging.info("Retrieving management IPs...")
            results = managementip_csv(csv_file, config_yaml, **creds)
            success_count = sum(1 for r in results if r)
            print(f"\nRetrieved IPs for {success_count}/{len(results)} VMs successfully")
            logging.info(f"IP retrieval completed: {success_count}/{len(results)} successful")
            return all(results)
        
        elif action == "deployment":
            logging.info("Starting FULL DEPLOYMENT...")
            print("\nFULL DEPLOYMENT: validation → clone → network → start → IPs\n")
            print("=" * 70 + "\n")
            all_success = True

            # Step 1: Validation
            print("STEP 1/5: Validating CSV")
            valid, errors = check_csv(csv_file, config_yaml, **creds)
            if not valid:
                print("Validation FAILED - Stopping deployment")
                logging.error("Deployment stopped: CSV validation failed")
                return False
            print("Validation OK\n")
            
            # Step 2: Clone
            print("STEP 2/5: Cloning VMs")
            clone_results = clone_csv(csv_file, config_yaml, **creds)
            if not all(clone_results):
                print("Some clones failed")
                all_success = False
            else:
                print("Cloning OK\n")
            
            # Step 3: Network
            print("STEP 3/5: Configuring network bridges")
            network_results = networkbridge_csv(csv_file, config_yaml, **creds)
            if not all(network_results):
                print("Some network configs failed")
                all_success = False
            else:
                print("Network configuration OK\n")
            
            # Step 4: Start
            print("STEP 4/5: Starting VMs")
            start_results = start_csv(csv_file, config_yaml, **creds)
            if not all(start_results):
                print("Some VMs failed to start")
                all_success = False
            else:
                print("Starting OK\n")
            
            # Step 5: Get IPs
            print("STEP 5/5: Retrieving management IPs")
            ip_results = managementip_csv(csv_file, config_yaml, **creds)
            if not all(ip_results):
                print("Some IPs not retrieved")
                all_success = False
            else:
                print("IP retrieval OK\n")
            
            # Summary
            print("=" * 70)
            if all_success:
                print("FULL DEPLOYMENT COMPLETED SUCCESSFULLY")
            else:
                print("DEPLOYMENT COMPLETED WITH SOME WARNINGS")
            print("=" * 70)
            return all_success
        
        else:
            logging.error(f"Unknown action: {action}")
            return False
    
    except Exception as e:
        logging.error(f"Error executing action '{action}': {e}", exc_info=True)
        print(f"\nERROR: {e}")
        return False

def setup_logging(debug_level):
    """
    Configure logging based on debug level.
    debug_level (str): Debug level (info, debug, none)
    """
    if debug_level == "debug":
        logging.basicConfig(level=logging.DEBUG)
    elif debug_level == "info":
        logging.basicConfig(level=logging.INFO)
    else:  # none
        logging.basicConfig(level=logging.WARNING)

def main():
    """
    Main entry point for the CLI application.
    """
    # Server names used in the CSV file
    config_yaml = "config.yaml"

    # Load environment variables from the .env file
    load_dotenv()

    # Parse arguments
    parser = get_args()
    args = vars(parser.parse_args())
    
    # Setup logging first
    debug_level = args.get("debug", "info")
    setup_logging(debug_level)
    
    # Extract parameters
    csv_file = args["csv_file"]
    action = args["action"]
    
    # Get credentials from args or environment
    creds = get_credentials_from_env_or_args(args)
    
    # Validate credentials
    valid_creds, creds_error = validate_credentials(creds)
    if not valid_creds:
        logging.error(f"Credential validation failed: {creds_error}")
        print(f"\nERROR: {creds_error}")
        print("\nFor help, use: python bulk_vm_management_main.py --help")
        sys.exit(1)
    
    # Validate files
    valid_files, files_error = validate_files(csv_file, config_yaml)
    if not valid_files:
        logging.error(f"File validation failed: {files_error}")
        print(f"\nERROR: {files_error}")
        sys.exit(1)
    
    # Execute action
    success = execute_action(action, csv_file, config_yaml, creds)
    
    # Exit with appropriate code
    if success:
        logging.info("Operation completed successfully")
        sys.exit(0)
    else:
        logging.error("Operation completed with errors")
        sys.exit(1)

if __name__ == "__main__":
    main()