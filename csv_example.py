import csv
import logging
import random
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def for_each_row(csv_file_name, vm_template, vm_name_prefix, vm_name_suffix, action):
    """
    Effectuate an action on a vm for each row of a csv file
    csv_file : nom;prénom;IP;login;mot de passe; default password, nom vm;serveur; login serveur (florn)
    action : create_vm, start_vm


    On ouvre un fichier csv, on crée un fichier csv temporaire, on remplace le fichier initial par le temporaire
    """
    random.seed()
    with open(csv_file_name, "r", encoding="utf-8-sig") as file:
        fieldnames = [
            "nom",
            "prénom",
            "IP",
            "login",
            "mot de passe",
            "default password",
            "nom vm",
            "serveur",
            "login serveur",
        ]
        reader = csv.DictReader(
            file, dialect="excel", delimiter=";", quotechar='"', quoting=csv.QUOTE_ALL
        )
        with open(
            csv_file_name + ".temp", "w", newline="", encoding="utf-8-sig"
        ) as file2:
            writer = csv.DictWriter(
                file2,
                dialect="excel",
                delimiter=";",
                quotechar='"',
                quoting=csv.QUOTE_ALL,
                fieldnames=fieldnames,
            )
            writer.writeheader()
            for reader_row in reader:
                writer_row = {}  # Ligne qui sera écrite dans le fichier
                # Si le nom n'est pas défini dans le fichier, on utilise le nom par défaut : Prefix_Etudiant_Suffixe
                if (
                    reader_row["nom"] != ""
                ):  # Si le nom de l'étudiant n'est pas nul, c'est une ligne à traiter
                    # Creating a new vm from template
                    vm = VirtualMachine(
                        vm_template.vm_name,
                        vm_template.ova_path,
                        vm_template.ova_filename,
                        vm_template.nics,
                        vm_template.vm_admin,
                        vm_template.vm_admin_password,
                        vm_template.vm_admin_ssh_key,
                        vm_template.on_server,
                        vm_template.for_user,
                    )

                    if (
                        reader_row["nom vm"] == ""
                    ):  # Si le nom de la vm n'est pas défini dans le fichier
                        nom_etu = reader_row.get("nom")
                        vm_name = f"{vm_name_prefix}_{nom_etu}_{vm_name_suffix}"
                    else:
                        vm_name = reader_row["nom vm"]
                    vm_name = vm_name.replace(" ", "_")
                    vm.vm_name = vm_name

                    if (
                        reader_row.get("serveur") != ""
                    ):  # Si le serveur est précisé dans le fichier, on garde cette valeur
                        server_number = reader_row.get("serveur")
                    else:  # Sinon on tire un serveur aléatoirement
                        server_min_number = int(min(servers_dict.keys()))
                        server_max_number = int(max(servers_dict.keys()))
                        server_number = random.randint(
                            server_min_number, server_max_number
                        )

                    if reader_row.get("login serveur") != "":
                        vm.for_user = reader_row.get("login serveur")
                    else:
                        print("You must provide a login serveur column in the csv file")
                        exit(1)

                    vm.on_server = servers_dict[str(server_number)]

                    # Si on change le mot de passe.
                    if action == change_vm_admin_password:
                        logging.info("Changing password on vm {}".format(vm_name))
                        # Pour se loguer à la vm, on suppose que le mot de passe est celui par défaut.
                        # vm.vm_admin_password=reader_row.get('default password') pas besoin la connexion ssh se fait par clé
                        # Si la colonne mot de passe est vide, on mettra comme mot de passe le nom de l'utilisateur en minusucule
                        if reader_row.get("mot de passe") == "":
                            new_pass = reader_row.get("nom").lower()
                            logging.debug(
                                "mot de passe column is empty. New password".format(
                                    new_pass
                                )
                            )
                            # Pour se loguer à la vm, on suppose que le mot de passe est celui par défaut.
                            action(vm, new_pass)
                            writer_row["default password"] = new_pass
                        else:  # Si la colonne password n'est pas vide, on met comme nouveau password celui de la colonne
                            logging.debug(
                                "mot de passe column is not empty. New password".format(
                                    vm_name
                                )
                            )
                            new_pass = reader_row.get("mot de passe")
                            logging.debug(
                                "mot de passe column is not empty. New password".format(
                                    new_pass
                                )
                            )
                            action(vm, new_pass)
                            writer_row["default password"] = new_pass
                        vm.vm_admin_password = new_pass
                        logging.debug(
                            "vm : {} vm.admin_password : {} ".format(
                                vm_name, vm.vm_admin_password
                            )
                        )
                    else:
                        action(vm)

                    logging.debug("for_each_row, vm : {} ".format(vm))
                    writer_row["nom"] = reader_row.get("nom")
                    writer_row["prénom"] = reader_row.get("prénom")
                    writer_row["IP"] = vm.ip_address_mgmt
                    writer_row["login"] = vm.vm_admin
                    writer_row["mot de passe"] = vm.vm_admin_password
                    writer_row["nom vm"] = vm.vm_name
                    writer_row["serveur"] = server_number
                    writer_row["login serveur"] = vm.for_user
                    logging.info(f"Line to write in csv : {writer_row}")
                    writer.writerow(writer_row)

    shutil.move(csv_file_name + ".temp", csv_file_name)
