#!/usr/bin/env python3
"""
Script to clean status column from CSV files since status is now inferred
"""

import csv
import shutil
from pathlib import Path


def clean_csv_status(csv_file_path: Path, backup: bool = True):
    """Remove status column from CSV file"""
    if not csv_file_path.exists():
        print(f"File not found: {csv_file_path}")
        return False

    # Create backup if requested
    if backup:
        backup_path = csv_file_path.with_suffix(csv_file_path.suffix + '.backup')
        shutil.copy2(csv_file_path, backup_path)
        print(f"Created backup: {backup_path}")

    # Read the CSV and remove status column
    rows = []
    fieldnames = []

    try:
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = [field for field in reader.fieldnames if field != 'status']

            for row in reader:
                # Remove status field if it exists
                row.pop('status', None)
                rows.append(row)

        # Write back without status column
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as f:
            if fieldnames:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

        print(f"Cleaned {csv_file_path}: removed status column, kept {len(rows)} rows")
        return True

    except Exception as e:
        print(f"Error cleaning {csv_file_path}: {e}")
        return False


def main():
    """Clean status from known CSV files"""
    script_dir = Path(__file__).parent

    # Define CSV files to clean
    csv_files = [
        script_dir / "varchiver" / "inventory" / "data" / "tech_terms_queue.csv",
        script_dir.parent / "loreum" / "data" / "world_glossary.csv",
    ]

    print("Cleaning status columns from CSV files...")
    print("(Status will now be inferred dynamically from item database)")
    print()

    cleaned_count = 0
    for csv_file in csv_files:
        if csv_file.exists():
            if clean_csv_status(csv_file, backup=True):
                cleaned_count += 1
        else:
            print(f"Skipping (not found): {csv_file}")

    print()
    print(f"Cleaned {cleaned_count} CSV files")
    print("Status column removed - status will now be inferred from:")
    print("  - JSON item database (implemented/partial)")
    print("  - Glossary entry completeness (conceptual/pending)")
    print()
    print("Use 'Set Item Database' button in glossary manager to enable inference")


if __name__ == "__main__":
    main()
