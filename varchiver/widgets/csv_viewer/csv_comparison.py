#!/usr/bin/env python3
"""
CSV Comparison Module - Compare different CSV files with flexible mapping

Provides functionality to compare CSV files with different structures,
find differences, and export results.
"""

from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
import csv

from .csv_data_model import CsvStructureDetector, CsvRow


class CsvComparisonResult:
    """Results of CSV file comparison"""

    def __init__(self, file1_path: Path, file2_path: Path,
                 comparison_key: str, key_column1: str, key_column2: str):
        self.file1_path = file1_path
        self.file2_path = file2_path
        self.comparison_key = comparison_key
        self.key_column1 = key_column1
        self.key_column2 = key_column2

        # Comparison results
        self.only_in_file1: Dict[str, Dict[str, str]] = {}
        self.only_in_file2: Dict[str, Dict[str, str]] = {}
        self.common_keys: Set[str] = set()
        self.different_values: Dict[str, Tuple[Dict[str, str], Dict[str, str]]] = {}

        # Statistics
        self.total_file1_records = 0
        self.total_file2_records = 0
        self.total_unique_keys = 0

    def get_summary(self) -> Dict[str, Any]:
        """Get comparison summary statistics"""
        return {
            'file1_name': self.file1_path.name,
            'file2_name': self.file2_path.name,
            'comparison_key': self.comparison_key,
            'total_file1_records': self.total_file1_records,
            'total_file2_records': self.total_file2_records,
            'only_in_file1_count': len(self.only_in_file1),
            'only_in_file2_count': len(self.only_in_file2),
            'common_records_count': len(self.common_keys),
            'different_values_count': len(self.different_values),
            'total_unique_keys': self.total_unique_keys
        }


class CsvComparison:
    """Utility class for comparing CSV files"""

    @staticmethod
    def compare_files(file1_path: Path, file2_path: Path,
                     file1_mapping: Dict[str, str], file2_mapping: Dict[str, str],
                     comparison_key: str = 'auto') -> Tuple[bool, str, Optional[CsvComparisonResult]]:
        """
        Compare two CSV files with flexible column mapping

        Args:
            file1_path: Path to first CSV file
            file2_path: Path to second CSV file
            file1_mapping: Column mapping for file1 {internal_name: csv_column}
            file2_mapping: Column mapping for file2 {internal_name: csv_column}
            comparison_key: Which mapped column to use as comparison key

        Returns:
            (success, message, comparison_result)
        """
        try:
            # Detect structures
            structure1 = CsvStructureDetector.detect_structure(file1_path)
            structure2 = CsvStructureDetector.detect_structure(file2_path)

            if structure1['error']:
                return False, f"Error reading {file1_path.name}: {structure1['error']}", None
            if structure2['error']:
                return False, f"Error reading {file2_path.name}: {structure2['error']}", None

            # Determine comparison key columns
            key_col1, key_col2 = CsvComparison._determine_key_columns(
                file1_mapping, file2_mapping, comparison_key, structure1, structure2
            )

            if not key_col1 or not key_col2:
                return False, "Could not determine comparison key columns", None

            # Load data from both files
            data1 = CsvComparison._load_csv_data(file1_path, structure1, key_col1)
            data2 = CsvComparison._load_csv_data(file2_path, structure2, key_col2)

            # Create comparison result
            result = CsvComparisonResult(file1_path, file2_path, comparison_key, key_col1, key_col2)
            result.total_file1_records = len(data1)
            result.total_file2_records = len(data2)

            # Find differences
            keys1 = set(data1.keys())
            keys2 = set(data2.keys())

            result.only_in_file1 = {k: data1[k] for k in keys1 - keys2}
            result.only_in_file2 = {k: data2[k] for k in keys2 - keys1}
            result.common_keys = keys1 & keys2
            result.total_unique_keys = len(keys1 | keys2)

            # Find records with different values (optional, for common keys)
            result.different_values = CsvComparison._find_different_values(
                data1, data2, result.common_keys, file1_mapping, file2_mapping
            )

            success_msg = f"Compared {result.total_file1_records} vs {result.total_file2_records} records"
            return True, success_msg, result

        except Exception as e:
            return False, f"Comparison failed: {str(e)}", None

    @staticmethod
    def _determine_key_columns(file1_mapping: Dict[str, str], file2_mapping: Dict[str, str],
                              comparison_key: str, structure1: Dict, structure2: Dict) -> Tuple[str, str]:
        """Determine which columns to use as comparison keys"""

        if comparison_key == 'auto':
            # Try to find a suitable key column
            potential_keys = ['id', 'name', 'term', 'title', 'key']
            for key in potential_keys:
                col1 = file1_mapping.get(key)
                col2 = file2_mapping.get(key)
                if (col1 and col1 in structure1['headers'] and
                    col2 and col2 in structure2['headers']):
                    return col1, col2

            # Fallback to first mapped column that exists in both files
            for internal_name in file1_mapping:
                if internal_name in file2_mapping:
                    col1 = file1_mapping[internal_name]
                    col2 = file2_mapping[internal_name]
                    if (col1 in structure1['headers'] and col2 in structure2['headers']):
                        return col1, col2
        else:
            # Use specified comparison key
            col1 = file1_mapping.get(comparison_key)
            col2 = file2_mapping.get(comparison_key)
            if (col1 and col1 in structure1['headers'] and
                col2 and col2 in structure2['headers']):
                return col1, col2

        return None, None

    @staticmethod
    def _load_csv_data(file_path: Path, structure: Dict, key_column: str) -> Dict[str, Dict[str, str]]:
        """Load CSV data using specified key column"""
        data = {}

        with open(file_path, 'r', encoding=structure['encoding']) as f:
            reader = csv.DictReader(f, delimiter=structure['delimiter'])
            for row in reader:
                key_value = row.get(key_column, '').strip()
                if key_value:
                    # Use lowercase key for case-insensitive comparison
                    normalized_key = key_value.lower()
                    data[normalized_key] = row

        return data

    @staticmethod
    def _find_different_values(data1: Dict[str, Dict[str, str]],
                              data2: Dict[str, Dict[str, str]],
                              common_keys: Set[str],
                              file1_mapping: Dict[str, str],
                              file2_mapping: Dict[str, str]) -> Dict[str, Tuple[Dict[str, str], Dict[str, str]]]:
        """Find records with different values for common keys"""
        different = {}

        # Only compare mapped columns that exist in both files
        comparable_columns = []
        for internal_name in file1_mapping:
            if internal_name in file2_mapping:
                comparable_columns.append((internal_name, file1_mapping[internal_name], file2_mapping[internal_name]))

        for key in common_keys:
            if key in data1 and key in data2:
                row1 = data1[key]
                row2 = data2[key]

                # Check if any comparable columns have different values
                has_differences = False
                for internal_name, col1, col2 in comparable_columns:
                    val1 = row1.get(col1, '').strip()
                    val2 = row2.get(col2, '').strip()
                    if val1 != val2:
                        has_differences = True
                        break

                if has_differences:
                    different[key] = (row1, row2)

        return different

    @staticmethod
    def export_missing_records(result: CsvComparisonResult,
                              output_path: Path,
                              export_type: str = 'file1_missing') -> Tuple[bool, str]:
        """
        Export missing records to CSV file

        Args:
            result: Comparison result
            output_path: Where to save the exported CSV
            export_type: 'file1_missing', 'file2_missing', or 'both'
        """
        try:
            if export_type == 'file1_missing':
                data_to_export = result.only_in_file2
                source_structure = CsvStructureDetector.detect_structure(result.file2_path)
            elif export_type == 'file2_missing':
                data_to_export = result.only_in_file1
                source_structure = CsvStructureDetector.detect_structure(result.file1_path)
            else:
                return False, "Export type 'both' not yet implemented"

            if source_structure['error']:
                return False, f"Error reading source structure: {source_structure['error']}"

            if not data_to_export:
                return False, f"No missing records to export for {export_type}"

            # Write CSV file
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                fieldnames = source_structure['headers']
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=source_structure['delimiter'])
                writer.writeheader()

                for key in sorted(data_to_export.keys()):
                    row_data = data_to_export[key]
                    # Ensure all fields are present
                    clean_row = {}
                    for field in fieldnames:
                        clean_row[field] = row_data.get(field, '')
                    writer.writerow(clean_row)

            count = len(data_to_export)
            return True, f"Exported {count} missing records to {output_path.name}"

        except Exception as e:
            return False, f"Export failed: {str(e)}"

    @staticmethod
    def create_comparison_report(result: CsvComparisonResult) -> str:
        """Create a text report of the comparison results"""
        summary = result.get_summary()

        report_lines = [
            "=== CSV Comparison Report ===",
            "",
            f"File 1: {summary['file1_name']} ({summary['total_file1_records']} records)",
            f"File 2: {summary['file2_name']} ({summary['total_file2_records']} records)",
            f"Comparison Key: {summary['comparison_key']}",
            "",
            "=== Results ===",
            f"Records only in {summary['file1_name']}: {summary['only_in_file1_count']}",
            f"Records only in {summary['file2_name']}: {summary['only_in_file2_count']}",
            f"Common records: {summary['common_records_count']}",
            f"Records with different values: {summary['different_values_count']}",
            f"Total unique records: {summary['total_unique_keys']}",
            ""
        ]

        # Add details for missing records
        if result.only_in_file1:
            report_lines.extend([
                f"=== Records only in {summary['file1_name']} ===",
                ""
            ])
            for key in sorted(result.only_in_file1.keys())[:10]:  # Show first 10
                row = result.only_in_file1[key]
                first_few_values = list(row.values())[:3]  # Show first 3 column values
                report_lines.append(f"- {key}: {', '.join(first_few_values)}")

            if len(result.only_in_file1) > 10:
                report_lines.append(f"... and {len(result.only_in_file1) - 10} more")
            report_lines.append("")

        if result.only_in_file2:
            report_lines.extend([
                f"=== Records only in {summary['file2_name']} ===",
                ""
            ])
            for key in sorted(result.only_in_file2.keys())[:10]:  # Show first 10
                row = result.only_in_file2[key]
                first_few_values = list(row.values())[:3]  # Show first 3 column values
                report_lines.append(f"- {key}: {', '.join(first_few_values)}")

            if len(result.only_in_file2) > 10:
                report_lines.append(f"... and {len(result.only_in_file2) - 10} more")
            report_lines.append("")

        return "\n".join(report_lines)
