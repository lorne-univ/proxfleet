import csv
import logging
import os
import shutil


class ProxmoxCSV:
    def __init__(self, csv_path: str):
        """
        Handles CSV file operations (read, write, copy).
        csv_path: path to the CSV file
        """
        self.csv_path = csv_path

    def detect_delimiter(self):
        """
        Detects the delimiter used in the CSV file (',' or ';').
        return: str
        """
        logging.debug(f"Detecting delimiter for CSV file: {self.csv_path}")
        try:
            with open(self.csv_path, newline="", encoding="utf-8-sig") as f:
                sample = f.read(2048)
                dialect = csv.Sniffer().sniff(sample, delimiters=";,")
                logging.debug(f"Detected delimiter '{dialect.delimiter}' for {self.csv_path}")
                return dialect.delimiter
        except Exception as e:
            logging.error(f"Unable to detect delimiter for {self.csv_path}: {e}. Defaulting to ';'")
            return ";"

    def create_csv(self) -> bool:
        """
        Create an empty CSV file at the specified path.
        If the file already exists, the operation will fail.
        return: bool
        """
        logging.debug(f"Attempting to create CSV file: {self.csv_path}")
        
        if os.path.exists(self.csv_path):
            logging.error(f"Cannot create CSV {self.csv_path}: file already exists")
            return False
        
        try:
            with open(self.csv_path, "w", newline="", encoding="utf-8-sig") as f:
                pass  # Create empty file
            logging.debug(f"CSV file successfully created: {self.csv_path}")
            return True
        except Exception as e:
            logging.error(f"Failed to create CSV {self.csv_path}: {e}")
            return False
    
    def delete_csv(self) -> bool:
        """
        Delete the CSV file at the specified path.
        return: bool
        """
        logging.debug(f"Attempting to delete CSV file: {self.csv_path}")
        
        if not os.path.exists(self.csv_path):
            logging.error(f"Cannot delete CSV {self.csv_path}: file does not exist")
            return False
        
        try:
            os.remove(self.csv_path)
            logging.debug(f"CSV file successfully deleted: {self.csv_path}")
            return True
        except Exception as e:
            logging.error(f"Failed to delete CSV {self.csv_path}: {e}")
            return False

    def copy_csv(self, new_name: str | None = None):
        """
        Create a copy of the CSV file.
        If 'new_name' is provided, use it as the destination filename.
        Otherwise, append '_clone' before the '.csv' extension.
        return: str | None
        """
        if new_name:
            output_csv = new_name
        else:
            if self.csv_path.lower().endswith(".csv"):
                output_csv = self.csv_path[:-4] + "_clone.csv"
            else:
                output_csv = self.csv_path + "_clone"
        logging.debug(f"Copying CSV from {self.csv_path} to {output_csv}")
        try:
            shutil.copyfile(self.csv_path, output_csv)
            return output_csv
        except Exception as e:
            logging.error(f"Failed to copy CSV {self.csv_path}: {e}")
            return None

    def count_rows(self, delimiter: str = ";"):
        """
        Count how many data rows the CSV contains (excluding header).
        return: int
        """
        logging.debug(f"Counting rows in CSV file: {self.csv_path} (delimiter='{delimiter}')")
        try:
            with open(self.csv_path, newline="", encoding="utf-8-sig") as f:
                reader = csv.reader(f, delimiter=delimiter)
                next(reader, None)
                return sum(1 for _ in reader)
        except Exception as e:
            logging.error(f"Unable to count rows in {self.csv_path}: {e}")
            return 0

    def read_header(self, delimiter: str = ";"):
        """
        Returns the header (column names) of the CSV file.
        return: list[str]
        """
        logging.debug(f"Getting header from CSV file: {self.csv_path} (delimiter='{delimiter}')")
        try:
            with open(self.csv_path, newline="", encoding="utf-8-sig") as f:
                reader = csv.reader(f, delimiter=delimiter)
                header = next(reader)
                return header
        except Exception as e:
            logging.error(f"Failed to read header from {self.csv_path}: {e}")
            return []

    def read_csv(self, delimiter: str = ";"):
        """
        Reads the CSV file using the specified delimiter.
        return: list[dict]
        """
        logging.debug(f"Reading CSV file: {self.csv_path} (delimiter='{delimiter}')")
        try:
            with open(self.csv_path, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                rows = list(reader)
                logging.debug(f"Read {len(rows)} rows from {self.csv_path}")
                return rows
        except Exception as e:
            logging.error(f"Failed to read CSV {self.csv_path}: {e}")
            return []

    def write_csv(self, rows: list[dict], fieldnames: list[str], delimiter: str = ";") -> bool:
        """
        Writes rows to the CSV file using the specified delimiter.
        return: bool
        """
        logging.debug(f"Writing {len(rows)} rows to CSV file: {self.csv_path} (delimiter='{delimiter}')")
        try:
            with open(self.csv_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
                writer.writeheader()
                writer.writerows(rows)
            logging.debug(f"CSV successfully written: {self.csv_path}")
            return True
        except Exception as e:
            logging.error(f"Failed to write CSV {self.csv_path}: {e}")
            return False