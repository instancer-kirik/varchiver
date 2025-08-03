#!/usr/bin/env python3
"""
Script to compare CSV term files and find missing entries
"""

import csv
import sys
from pathlib import Path
from typing import Set, Dict, List


def load_csv_terms(csv_path: Path) -> Dict[str, Dict[str, str]]:
    """Load terms from CSV file, return dict of {term: row_data}"""
    terms = {}

    if not csv_path.exists():
        print(f"WARNING: File not found: {csv_path}")
        return terms

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                term = row.get('term', '').strip()
                if term:
                    terms[term.lower()] = row  # Use lowercase for comparison
        print(f"Loaded {len(terms)} terms from {csv_path.name}")
    except Exception as e:
        print(f"ERROR loading {csv_path}: {e}")

    return terms


def compare_csv_files():
    """Compare the two CSV files and report differences"""
    script_dir = Path(__file__).parent

    # Define file paths
    queue_file = script_dir / "varchiver" / "inventory" / "data" / "tech_terms_queue.csv"
    world_file = script_dir.parent / "loreum" / "data" / "world_glossary.csv"

    print("=== CSV TERM COMPARISON ===")
    print(f"Queue file: {queue_file}")
    print(f"World file: {world_file}")
    print()

    # Load terms from both files
    queue_terms = load_csv_terms(queue_file)
    world_terms = load_csv_terms(world_file)

    if not queue_terms and not world_terms:
        print("No terms loaded from either file!")
        return

    # Find missing terms
    queue_only = set(queue_terms.keys()) - set(world_terms.keys())
    world_only = set(world_terms.keys()) - set(queue_terms.keys())
    common_terms = set(queue_terms.keys()) & set(world_terms.keys())

    print(f"=== SUMMARY ===")
    print(f"Terms in QUEUE only:     {len(queue_only)}")
    print(f"Terms in WORLD only:     {len(world_only)}")
    print(f"Terms in BOTH files:     {len(common_terms)}")
    print(f"Total unique terms:      {len(queue_terms) + len(world_terms) - len(common_terms)}")
    print()

    # Show terms missing from world_glossary
    if queue_only:
        print("=== MISSING FROM WORLD_GLOSSARY ===")
        print("(These terms are in tech_terms_queue but NOT in world_glossary)")
        print()

        missing_list = []
        for term in sorted(queue_only):
            original_term = None
            for orig_key, row_data in queue_terms.items():
                if orig_key == term:
                    original_term = row_data['term']
                    break

            if original_term:
                row_data = queue_terms[term]
                missing_list.append(row_data)
                print(f"  {original_term}")
                print(f"    Type: {row_data.get('type', 'N/A')}")
                print(f"    Category: {row_data.get('category', 'N/A')}")
                print(f"    Description: {row_data.get('description', 'N/A')[:80]}...")
                print()

        # Offer to create migration file
        print(f"Found {len(missing_list)} terms to migrate.")

        # Create a CSV with missing terms
        output_file = script_dir / "missing_terms_to_migrate.csv"
        if missing_list:
            try:
                with open(output_file, 'w', newline='', encoding='utf-8') as f:
                    fieldnames = ['term', 'type', 'category', 'description', 'source', 'related_terms', 'etymology_notes']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()

                    for row in missing_list:
                        # Clean up the row for world_glossary format
                        clean_row = {
                            'term': row.get('term', ''),
                            'type': row.get('type', ''),
                            'category': row.get('category', ''),
                            'description': row.get('description', ''),
                            'source': row.get('source', 'varchiver'),
                            'related_terms': row.get('related_terms', ''),
                            'etymology_notes': row.get('etymology_notes', '')
                        }
                        writer.writerow(clean_row)

                print(f"✅ Created migration file: {output_file}")
                print("   You can review and manually add these to world_glossary.csv")
            except Exception as e:
                print(f"ERROR creating migration file: {e}")
    else:
        print("✅ All terms from tech_terms_queue are already in world_glossary!")

    # Show terms that are only in world_glossary (for info)
    if world_only:
        print("=== WORLD_GLOSSARY EXTRAS ===")
        print(f"(These {len(world_only)} terms are in world_glossary but NOT in tech_terms_queue)")
        print("This is normal - world_glossary has more comprehensive terminology.")

        # Show just the first 10 as examples
        for i, term in enumerate(sorted(world_only)):
            if i >= 10:
                print(f"  ... and {len(world_only) - 10} more")
                break
            original_term = None
            for row_data in world_terms.values():
                if row_data['term'].lower() == term:
                    original_term = row_data['term']
                    break
            print(f"  {original_term}")
        print()

    # Check for potential duplicates (case variations)
    print("=== POTENTIAL DUPLICATES ===")
    all_terms_normalized = {}
    duplicates_found = False

    for source, terms_dict in [("queue", queue_terms), ("world", world_terms)]:
        for term_key, row_data in terms_dict.items():
            original_term = row_data['term']
            normalized = original_term.lower().replace(' ', '').replace('-', '').replace('_', '')

            if normalized in all_terms_normalized:
                prev_source, prev_term = all_terms_normalized[normalized]
                if prev_term != original_term:  # Different spelling/formatting
                    print(f"  {prev_term} ({prev_source}) vs {original_term} ({source})")
                    duplicates_found = True
            else:
                all_terms_normalized[normalized] = (source, original_term)

    if not duplicates_found:
        print("  No potential duplicates found ✅")


def main():
    """Main function"""
    print("Comparing CSV term files...")
    print()

    compare_csv_files()

    print()
    print("=== RECOMMENDATIONS ===")
    print("1. Review missing_terms_to_migrate.csv (if created)")
    print("2. Manually add important missing terms to world_glossary.csv")
    print("3. Consider world_glossary.csv as your primary/master glossary")
    print("4. Use tech_terms_queue.csv for temporary/work-in-progress items")


if __name__ == "__main__":
    main()
