#!/usr/bin/env python3
"""
CSV Data Model - Schema-agnostic CSV data handling

This module provides a clean data layer for CSV operations without making
assumptions about the data structure or content.
"""

import csv
import io
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum


class ColumnType(Enum):
    """Detected column data types"""
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    MIXED = "mixed"


@dataclass
class ColumnInfo:
    """Metadata about a CSV column"""
    name: str
    index: int
    data_type: ColumnType = ColumnType.TEXT
    sample_values: List[str] = field(default_factory=list)
    is_required: bool = False
    max_length: int = 0

    def __post_init__(self):
        if not self.sample_values:
            self.sample_values = []


@dataclass
class CsvRow:
    """Represents a single CSV row with flexible structure"""
    data: Dict[str, str] = field(default_factory=dict)
    row_index: Optional[int] = None

    def get_value(self, column: str, default: str = "") -> str:
        """Get value for a column with fallback"""
        return self.data.get(column, default)

    def set_value(self, column: str, value: str) -> None:
        """Set value for a column"""
        self.data[column] = str(value) if value is not None else ""

    def get_all_values(self) -> Dict[str, str]:
        """Get all column values"""
        return self.data.copy()

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary"""
        return self.data.copy()


class CsvStructureDetector:
    """Utility for detecting CSV file structure"""

    @staticmethod
    def detect_structure(file_path: Path) -> Dict[str, Any]:
        """Analyze CSV file and return structure metadata"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Read sample for analysis
                sample_size = min(8192, file_path.stat().st_size)
                sample = f.read(sample_size)
                f.seek(0)

                # Detect delimiter
                sniffer = csv.Sniffer()
                try:
                    dialect = sniffer.sniff(sample, delimiters=',;\t|')
                    delimiter = dialect.delimiter
                except csv.Error:
                    delimiter = ','  # fallback

                # Get headers and basic info
                reader = csv.DictReader(f, delimiter=delimiter)
                headers = list(reader.fieldnames) if reader.fieldnames else []

                # Count total rows
                f.seek(0)
                total_rows = sum(1 for _ in csv.reader(f, delimiter=delimiter)) - 1  # minus header

                return {
                    'file_path': str(file_path),
                    'file_size': file_path.stat().st_size,
                    'delimiter': delimiter,
                    'headers': headers,
                    'total_rows': total_rows,
                    'encoding': 'utf-8',
                    'has_headers': bool(headers),
                    'error': None
                }

        except Exception as e:
            return {
                'file_path': str(file_path),
                'error': str(e),
                'headers': [],
                'total_rows': 0,
                'delimiter': ',',
                'encoding': 'utf-8',
                'has_headers': False
            }

    @staticmethod
    def analyze_columns(file_path: Path, max_sample_rows: int = 100) -> List[ColumnInfo]:
        """Analyze column types and characteristics"""
        structure = CsvStructureDetector.detect_structure(file_path)
        if structure['error']:
            return []

        columns = []

        try:
            with open(file_path, 'r', encoding=structure['encoding']) as f:
                reader = csv.DictReader(f, delimiter=structure['delimiter'])

                # Initialize column info
                for i, header in enumerate(structure['headers']):
                    columns.append(ColumnInfo(
                        name=header,
                        index=i,
                        data_type=ColumnType.TEXT,
                        sample_values=[],
                        max_length=0
                    ))

                # Sample data for analysis
                sample_count = 0
                for row in reader:
                    if sample_count >= max_sample_rows:
                        break

                    for col_info in columns:
                        value = row.get(col_info.name, "")
                        if value and len(col_info.sample_values) < 5:
                            col_info.sample_values.append(value)
                        col_info.max_length = max(col_info.max_length, len(value))

                    sample_count += 1

                # Simple type detection (can be enhanced later)
                for col_info in columns:
                    col_info.data_type = CsvStructureDetector._detect_column_type(col_info.sample_values)

        except Exception:
            pass  # Return basic column info on error

        return columns

    @staticmethod
    def _detect_column_type(sample_values: List[str]) -> ColumnType:
        """Simple column type detection"""
        if not sample_values:
            return ColumnType.TEXT

        # Check if all values are numeric
        numeric_count = 0
        for value in sample_values:
            try:
                float(value.replace(',', ''))
                numeric_count += 1
            except (ValueError, AttributeError):
                pass

        if numeric_count == len(sample_values):
            return ColumnType.NUMBER

        # Check for boolean-like values
        boolean_values = {'true', 'false', 'yes', 'no', '1', '0', 'on', 'off'}
        boolean_count = sum(1 for v in sample_values if v.lower() in boolean_values)
        if boolean_count == len(sample_values):
            return ColumnType.BOOLEAN

        return ColumnType.TEXT


class CsvDataModel:
    """Schema-agnostic CSV data model"""

    def __init__(self):
        self.file_path: Optional[Path] = None
        self.columns: List[ColumnInfo] = []
        self.rows: List[CsvRow] = []
        self.delimiter: str = ','
        self.encoding: str = 'utf-8'
        self.has_changes: bool = False
        self._original_row_count: int = 0

    def load_from_file(self, file_path: Path) -> Tuple[bool, str]:
        """Load CSV data from file"""
        try:
            # Detect structure
            structure = CsvStructureDetector.detect_structure(file_path)
            if structure['error']:
                return False, f"Error reading file: {structure['error']}"

            if not structure['headers']:
                return False, "No headers detected in CSV file"

            # Store file info
            self.file_path = file_path
            self.delimiter = structure['delimiter']
            self.encoding = structure['encoding']

            # Analyze columns
            self.columns = CsvStructureDetector.analyze_columns(file_path)

            # Load all data
            self.rows = []
            with open(file_path, 'r', encoding=self.encoding) as f:
                reader = csv.DictReader(f, delimiter=self.delimiter)
                for row_idx, row_data in enumerate(reader):
                    # Clean the data - ensure all column values are strings
                    clean_data = {}
                    for col in self.columns:
                        raw_value = row_data.get(col.name, "")
                        clean_data[col.name] = str(raw_value) if raw_value is not None else ""

                    csv_row = CsvRow(data=clean_data, row_index=row_idx)
                    self.rows.append(csv_row)

            self._original_row_count = len(self.rows)
            self.has_changes = False

            return True, f"Loaded {len(self.rows)} rows with {len(self.columns)} columns"

        except Exception as e:
            return False, f"Failed to load CSV: {str(e)}"

    def save_to_file(self, file_path: Optional[Path] = None) -> Tuple[bool, str]:
        """Save CSV data to file"""
        target_path = file_path or self.file_path
        if not target_path:
            return False, "No file path specified"

        try:
            with open(target_path, 'w', newline='', encoding=self.encoding) as f:
                if not self.columns:
                    return False, "No columns defined"

                fieldnames = [col.name for col in self.columns]
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=self.delimiter)
                writer.writeheader()

                for row in self.rows:
                    # Ensure all required columns are present
                    row_data = {}
                    for col in self.columns:
                        row_data[col.name] = row.get_value(col.name, "")
                    writer.writerow(row_data)

            if file_path:
                self.file_path = file_path
            self.has_changes = False

            return True, f"Saved {len(self.rows)} rows to {target_path.name}"

        except Exception as e:
            return False, f"Failed to save CSV: {str(e)}"

    def add_row(self, data: Optional[Dict[str, str]] = None) -> CsvRow:
        """Add a new row with the same structure as existing rows"""
        new_data = {}

        # Initialize with empty values for all columns
        for col in self.columns:
            new_data[col.name] = ""

        # Override with provided data
        if data:
            for key, value in data.items():
                if key in new_data:  # Only allow existing columns
                    new_data[key] = str(value) if value is not None else ""

        new_row = CsvRow(data=new_data, row_index=len(self.rows))
        self.rows.append(new_row)
        self.has_changes = True

        return new_row

    def delete_row(self, row_index: int) -> bool:
        """Delete a row by index"""
        if 0 <= row_index < len(self.rows):
            del self.rows[row_index]
            # Update row indices
            for i, row in enumerate(self.rows):
                row.row_index = i
            self.has_changes = True
            return True
        return False

    def update_row(self, row_index: int, data: Dict[str, str]) -> bool:
        """Update a row with new data"""
        if 0 <= row_index < len(self.rows):
            row = self.rows[row_index]
            for key, value in data.items():
                if any(col.name == key for col in self.columns):  # Validate column exists
                    row.set_value(key, value)
            self.has_changes = True
            return True
        return False

    def get_row(self, row_index: int) -> Optional[CsvRow]:
        """Get a row by index"""
        if 0 <= row_index < len(self.rows):
            return self.rows[row_index]
        return None

    def get_column_names(self) -> List[str]:
        """Get list of column names"""
        return [col.name for col in self.columns]

    def get_row_count(self) -> int:
        """Get total number of rows"""
        return len(self.rows)

    def get_column_count(self) -> int:
        """Get total number of columns"""
        return len(self.columns)

    def get_structure_info(self) -> Dict[str, Any]:
        """Get summary of data structure"""
        return {
            'file_path': str(self.file_path) if self.file_path else None,
            'columns': len(self.columns),
            'rows': len(self.rows),
            'has_changes': self.has_changes,
            'delimiter': self.delimiter,
            'encoding': self.encoding,
            'column_names': self.get_column_names()
        }

    def create_template_row(self) -> Dict[str, str]:
        """Create a template row with empty values for all columns"""
        return {col.name: "" for col in self.columns}

    def validate_row_data(self, data: Dict[str, str]) -> Tuple[bool, List[str]]:
        """Validate row data against current structure"""
        errors = []

        # Check for unknown columns
        valid_columns = set(col.name for col in self.columns)
        for key in data.keys():
            if key not in valid_columns:
                errors.append(f"Unknown column: {key}")

        # Add more validation rules as needed
        # For now, we're keeping it simple and flexible

        return len(errors) == 0, errors
