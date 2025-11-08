#!/usr/bin/env python3
"""
Quick comparison of complete Supabase exports.
"""

import json
import sys
from pathlib import Path


def load_export(export_dir):
    """Load export data and schema."""
    export_path = Path(export_dir)

    # Find data and schema files
    data_files = list(export_path.glob("*_data_*.json"))
    schema_files = list(export_path.glob("*_schema_*.json"))

    if not data_files or not schema_files:
        raise FileNotFoundError(f"Export files not found in {export_dir}")

    with open(data_files[0]) as f:
        data = json.load(f)

    with open(schema_files[0]) as f:
        schema = json.load(f)

    return data, schema


def compare_exports(dir1, dir2):
    """Compare two complete exports."""
    print(f"🔍 COMPARING COMPLETE DATABASE EXPORTS")
    print("=" * 60)
    print(f"Development: {dir1}")
    print(f"Production:  {dir2}")
    print()

    # Load exports
    data1, schema1 = load_export(dir1)
    data2, schema2 = load_export(dir2)

    # Get tables
    tables1 = set(data1.get("public", {}).keys())
    tables2 = set(data2.get("public", {}).keys())

    print(f"📊 TABLES SUMMARY")
    print("-" * 30)
    print(f"Development tables: {len(tables1)}")
    print(f"Production tables:  {len(tables2)}")
    print(f"Common tables:      {len(tables1 & tables2)}")
    print(f"Only in dev:        {len(tables1 - tables2)}")
    print(f"Only in prod:       {len(tables2 - tables1)}")
    print()

    # Show unique tables
    if tables1 - tables2:
        print(f"🔧 DEVELOPMENT-ONLY TABLES ({len(tables1 - tables2)}):")
        for table in sorted(tables1 - tables2):
            count = len(data1["public"].get(table, []))
            print(f"   • {table} ({count} rows)")
        print()

    if tables2 - tables1:
        print(f"🚀 PRODUCTION-ONLY TABLES ({len(tables2 - tables1)}):")
        for table in sorted(tables2 - tables1):
            count = len(data2["public"].get(table, []))
            print(f"   • {table} ({count} rows)")
        print()

    # Compare common tables
    common_tables = tables1 & tables2
    if common_tables:
        print(f"🔄 COMMON TABLES COMPARISON ({len(common_tables)}):")
        print("-" * 40)

        total_dev_rows = 0
        total_prod_rows = 0

        for table in sorted(common_tables):
            count1 = len(data1["public"].get(table, []))
            count2 = len(data2["public"].get(table, []))

            total_dev_rows += count1
            total_prod_rows += count2

            diff = count2 - count1
            if diff != 0:
                diff_str = f"({diff:+d})" if diff != 0 else ""
                print(f"   {table:<30} {count1:>4} → {count2:<4} {diff_str}")

        print(f"\n📈 TOTALS:")
        print(f"   Development total rows: {total_dev_rows}")
        print(f"   Production total rows:  {total_prod_rows}")
        print(f"   Difference:             {total_prod_rows - total_dev_rows:+d}")

    print(f"\n💡 INSIGHTS:")

    # Calculate domain coverage
    dev_domains = set()
    prod_domains = set()

    for table in tables1:
        if "_" in table:
            dev_domains.add(table.split("_")[0])

    for table in tables2:
        if "_" in table:
            prod_domains.add(table.split("_")[0])

    print(f"   • Development domains: {', '.join(sorted(dev_domains))}")
    print(f"   • Production domains:  {', '.join(sorted(prod_domains))}")

    # Data richness
    dev_with_data = sum(1 for t in tables1 if len(data1["public"].get(t, [])) > 0)
    prod_with_data = sum(1 for t in tables2 if len(data2["public"].get(t, [])) > 0)

    print(
        f"   • Tables with data - Dev: {dev_with_data}/{len(tables1)} ({dev_with_data / len(tables1) * 100:.1f}%)"
    )
    print(
        f"   • Tables with data - Prod: {prod_with_data}/{len(tables2)} ({prod_with_data / len(tables2) * 100:.1f}%)"
    )


def main():
    """Main function."""
    if len(sys.argv) != 3:
        print("Usage: python quick_comparison.py <dev_export_dir> <prod_export_dir>")
        print("\nExample:")
        print("  python quick_comparison.py complete_export_dev complete_export_prod")
        return 1

    try:
        compare_exports(sys.argv[1], sys.argv[2])
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
