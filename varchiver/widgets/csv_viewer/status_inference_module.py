#!/usr/bin/env python3
"""
Status Inference Module - Connect CSV data to JSON databases for status detection

This module provides pluggable functionality to infer implementation status
of CSV records by checking their presence and completeness in JSON databases.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass

from .csv_data_model import CsvDataModel, CsvRow


class StatusType(Enum):
    """Possible status types for CSV records"""
    IMPLEMENTED = "implemented"    # Exists in JSON with full specs
    PARTIAL = "partial"           # Exists in JSON but incomplete
    CONCEPTUAL = "conceptual"     # Detailed CSV entry but no JSON item
    PENDING = "pending"           # Basic CSV entry only
    UNKNOWN = "unknown"           # No database set or error


@dataclass
class StatusRule:
    """Rule for determining status based on JSON content"""
    name: str
    description: str
    required_fields: List[str] = None
    optional_fields: List[str] = None
    min_optional_count: int = 0
    custom_check: Optional[Callable[[Dict], bool]] = None

    def __post_init__(self):
        if self.required_fields is None:
            self.required_fields = []
        if self.optional_fields is None:
            self.optional_fields = []


class StatusInferenceModule:
    """Module for inferring CSV record status from JSON databases"""

    def __init__(self):
        self.json_database_path: Optional[Path] = None
        self.json_data: Optional[Dict] = None
        self.csv_key_column: str = "term"  # Column in CSV to use as key
        self.json_key_fields: List[str] = ["id", "name", "term", "title"]  # Fields in JSON to match against
        self.case_sensitive: bool = False

        # Status determination rules
        self.status_rules = self._create_default_rules()

        # Cache for performance
        self._status_cache: Dict[str, StatusType] = {}
        self._json_items_index: Dict[str, Dict] = {}

    def _create_default_rules(self) -> Dict[StatusType, StatusRule]:
        """Create default rules for status determination"""
        return {
            StatusType.IMPLEMENTED: StatusRule(
                name="Implemented",
                description="Item exists in JSON with complete specifications",
                required_fields=["id", "name", "description"],
                optional_fields=["properties", "blueprint", "crafting_recipe_id", "lore_notes", "tech_tier"],
                min_optional_count=2  # Must have at least 2 optional fields
            ),
            StatusType.PARTIAL: StatusRule(
                name="Partial",
                description="Item exists in JSON but incomplete",
                required_fields=["id", "name"],
                min_optional_count=0
            )
        }

    def set_database(self, database_path: Path) -> tuple[bool, str]:
        """Set the JSON database file"""
        try:
            if not database_path.exists():
                return False, f"Database file not found: {database_path}"

            with open(database_path, 'r', encoding='utf-8') as f:
                self.json_data = json.load(f)

            self.json_database_path = database_path
            self._rebuild_index()
            self._clear_cache()

            item_count = len(self._json_items_index)
            return True, f"Loaded database with {item_count} items"

        except json.JSONDecodeError as e:
            return False, f"Invalid JSON format: {str(e)}"
        except Exception as e:
            return False, f"Failed to load database: {str(e)}"

    def _rebuild_index(self):
        """Rebuild the JSON items index for fast lookups"""
        self._json_items_index.clear()

        if not self.json_data:
            return

        # Handle different JSON structures
        items = []
        if isinstance(self.json_data, list):
            items = self.json_data
        elif isinstance(self.json_data, dict):
            # Check for common item container fields
            for container_field in ["items", "data", "records", "entries"]:
                if container_field in self.json_data:
                    container = self.json_data[container_field]
                    if isinstance(container, list):
                        items = container
                        break
            else:
                # Treat the dict itself as items if no container found
                items = [self.json_data]

        # Index items by all possible key fields
        for item in items:
            if not isinstance(item, dict):
                continue

            # Index by all possible key values (lowercased for case-insensitive lookup)
            for key_field in self.json_key_fields:
                if key_field in item and item[key_field]:
                    key_value = str(item[key_field]).strip()
                    if key_value:
                        index_key = key_value.lower() if not self.case_sensitive else key_value
                        self._json_items_index[index_key] = item

    def configure_mapping(self, csv_key_column: str, json_key_fields: List[str], case_sensitive: bool = False):
        """Configure how CSV keys map to JSON fields"""
        self.csv_key_column = csv_key_column
        self.json_key_fields = json_key_fields
        self.case_sensitive = case_sensitive

        # Rebuild index with new mapping
        if self.json_data:
            self._rebuild_index()
            self._clear_cache()

    def add_status_rule(self, status_type: StatusType, rule: StatusRule):
        """Add or update a status determination rule"""
        self.status_rules[status_type] = rule
        self._clear_cache()

    def infer_status(self, csv_row: CsvRow) -> StatusType:
        """Infer status for a single CSV row"""
        if not self.json_data:
            return StatusType.UNKNOWN

        # Get the key value from CSV row
        key_value = csv_row.get_value(self.csv_key_column, "").strip()
        if not key_value:
            return StatusType.UNKNOWN

        # Check cache first
        cache_key = key_value.lower() if not self.case_sensitive else key_value
        if cache_key in self._status_cache:
            return self._status_cache[cache_key]

        # Find corresponding JSON item
        lookup_key = cache_key
        json_item = self._json_items_index.get(lookup_key)

        if json_item:
            # Item exists in JSON - check completeness
            status = self._determine_implementation_status(json_item, csv_row)
        else:
            # Item not in JSON - check CSV completeness
            status = self._determine_csv_only_status(csv_row)

        # Cache result
        self._status_cache[cache_key] = status
        return status

    def _determine_implementation_status(self, json_item: Dict, csv_row: CsvRow) -> StatusType:
        """Determine status when item exists in JSON"""
        # Check against rules in order of preference
        for status_type in [StatusType.IMPLEMENTED, StatusType.PARTIAL]:
            if status_type in self.status_rules:
                rule = self.status_rules[status_type]
                if self._item_matches_rule(json_item, rule):
                    return status_type

        # Default to partial if item exists but doesn't match specific rules
        return StatusType.PARTIAL

    def _determine_csv_only_status(self, csv_row: CsvRow) -> StatusType:
        """Determine status when item only exists in CSV"""
        # Check if CSV row has substantial content
        description = csv_row.get_value("description", "")

        # Consider it "conceptual" if it has a substantial description
        if description and len(description.strip()) > 50:
            return StatusType.CONCEPTUAL

        # Otherwise it's just pending
        return StatusType.PENDING

    def _item_matches_rule(self, json_item: Dict, rule: StatusRule) -> bool:
        """Check if a JSON item matches a status rule"""
        # Check required fields
        for field in rule.required_fields:
            if field not in json_item or not json_item[field]:
                return False

        # Check optional fields count
        optional_present = 0
        for field in rule.optional_fields:
            if field in json_item and json_item[field]:
                optional_present += 1

        if optional_present < rule.min_optional_count:
            return False

        # Run custom check if provided
        if rule.custom_check and not rule.custom_check(json_item):
            return False

        return True

    def infer_status_for_model(self, model: CsvDataModel) -> Dict[int, StatusType]:
        """Infer status for all rows in a CSV model"""
        results = {}
        for i, row in enumerate(model.rows):
            results[i] = self.infer_status(row)
        return results

    def get_status_distribution(self, model: CsvDataModel) -> Dict[StatusType, int]:
        """Get distribution of status types in a CSV model"""
        distribution = {status: 0 for status in StatusType}

        for row in model.rows:
            status = self.infer_status(row)
            distribution[status] += 1

        return distribution

    def get_items_by_status(self, model: CsvDataModel, status_type: StatusType) -> List[tuple[int, CsvRow]]:
        """Get all rows with a specific status"""
        results = []
        for i, row in enumerate(model.rows):
            if self.infer_status(row) == status_type:
                results.append((i, row))
        return results

    def _clear_cache(self):
        """Clear the status cache"""
        self._status_cache.clear()

    def get_database_info(self) -> Dict[str, Any]:
        """Get information about the loaded database"""
        if not self.json_data:
            return {
                'loaded': False,
                'path': None,
                'item_count': 0
            }

        return {
            'loaded': True,
            'path': str(self.json_database_path),
            'item_count': len(self._json_items_index),
            'csv_key_column': self.csv_key_column,
            'json_key_fields': self.json_key_fields,
            'case_sensitive': self.case_sensitive
        }

    def get_configuration(self) -> Dict[str, Any]:
        """Get current configuration"""
        return {
            'database_path': str(self.json_database_path) if self.json_database_path else None,
            'csv_key_column': self.csv_key_column,
            'json_key_fields': self.json_key_fields,
            'case_sensitive': self.case_sensitive,
            'rules_count': len(self.status_rules),
            'cache_size': len(self._status_cache)
        }

    def export_status_report(self, model: CsvDataModel, output_path: Path) -> tuple[bool, str]:
        """Export status analysis to a text report"""
        try:
            distribution = self.get_status_distribution(model)
            db_info = self.get_database_info()

            report_lines = [
                "=== CSV Status Analysis Report ===",
                "",
                f"CSV File: {model.file_path.name if model.file_path else 'Unknown'}",
                f"Database: {db_info['path'] if db_info['loaded'] else 'No database loaded'}",
                f"Total Records: {len(model.rows)}",
                f"Comparison Key: {self.csv_key_column}",
                "",
                "=== Status Distribution ===",
            ]

            for status_type, count in distribution.items():
                percentage = (count / len(model.rows) * 100) if model.rows else 0
                report_lines.append(f"{status_type.value}: {count} ({percentage:.1f}%)")

            report_lines.extend(["", "=== Status Definitions ==="])
            for status_type, rule in self.status_rules.items():
                report_lines.append(f"{status_type.value}: {rule.description}")

            # Add sample items for each status
            for status_type in StatusType:
                items = self.get_items_by_status(model, status_type)
                if items:
                    report_lines.extend([
                        "",
                        f"=== {status_type.value.title()} Items (showing first 10) ===",
                    ])
                    for i, (row_index, row) in enumerate(items[:10]):
                        key_value = row.get_value(self.csv_key_column, "")
                        description = row.get_value("description", "")[:60]
                        report_lines.append(f"- {key_value}: {description}...")

                    if len(items) > 10:
                        report_lines.append(f"... and {len(items) - 10} more")

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(report_lines))

            return True, f"Status report exported to {output_path.name}"

        except Exception as e:
            return False, f"Failed to export report: {str(e)}"
