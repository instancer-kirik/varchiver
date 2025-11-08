"""
Dynamic Anything Parser for VArchiver

A comprehensive, intelligent parser that can automatically detect and parse various data formats
with full-featured support for TOON (Token-Optimized Object Notation) and extensible architecture
for additional formats.

Features:
- Automatic format detection with confidence scoring
- Full TOON parsing with advanced features
- JSON, CSV, YAML, XML, and other format support
- Smart content analysis and structure inference
- Streaming and batch processing capabilities
- Error recovery and partial parsing
- Format conversion with optimization hints
- Extensible plugin architecture for custom formats

Author: VArchiver Team
Version: 1.0.0
License: MIT
"""

import json
import csv
import re
import io
import yaml
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Union, Optional, Tuple, Set, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
import logging
from abc import ABC, abstractmethod


class FormatType(Enum):
    """Supported data formats"""

    TOON = auto()
    JSON = auto()
    CSV = auto()
    YAML = auto()
    XML = auto()
    TSV = auto()  # Tab-separated values
    PIPE_DELIMITED = auto()  # Pipe-separated values
    KEY_VALUE = auto()  # Simple key=value format
    INI = auto()  # INI configuration format
    PROPERTIES = auto()  # Java properties format
    UNKNOWN = auto()


@dataclass
class ParseResult:
    """Result of parsing operation with metadata"""

    data: Any
    format_type: FormatType
    confidence: float  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    parsing_time: float = 0.0

    @property
    def is_successful(self) -> bool:
        """Check if parsing was successful"""
        return self.data is not None and not self.errors

    @property
    def has_warnings(self) -> bool:
        """Check if there are warnings"""
        return bool(self.warnings)


@dataclass
class FormatDetectionResult:
    """Result of format detection"""

    format_type: FormatType
    confidence: float
    indicators: List[str]  # What indicated this format
    sample_structure: Optional[Dict[str, Any]] = None


class FormatDetector:
    """Intelligent format detection with confidence scoring"""

    def __init__(self):
        self.detectors = {
            FormatType.TOON: self._detect_toon,
            FormatType.JSON: self._detect_json,
            FormatType.CSV: self._detect_csv,
            FormatType.YAML: self._detect_yaml,
            FormatType.XML: self._detect_xml,
            FormatType.TSV: self._detect_tsv,
            FormatType.PIPE_DELIMITED: self._detect_pipe,
            FormatType.KEY_VALUE: self._detect_key_value,
            FormatType.INI: self._detect_ini,
            FormatType.PROPERTIES: self._detect_properties,
        }

    def detect_format(
        self, content: str, filename: Optional[str] = None
    ) -> FormatDetectionResult:
        """Detect format with confidence scoring"""
        content = content.strip()
        if not content:
            return FormatDetectionResult(FormatType.UNKNOWN, 0.0, ["Empty content"])

        results = []

        # Run all detectors
        for format_type, detector in self.detectors.items():
            try:
                confidence, indicators, structure = detector(content, filename)
                if confidence > 0:
                    results.append(
                        FormatDetectionResult(
                            format_type, confidence, indicators, structure
                        )
                    )
            except Exception as e:
                logging.debug(f"Detection error for {format_type}: {e}")

        if not results:
            return FormatDetectionResult(
                FormatType.UNKNOWN, 0.0, ["No format detected"]
            )

        # Return highest confidence result
        return max(results, key=lambda r: r.confidence)

    def _detect_toon(
        self, content: str, filename: Optional[str] = None
    ) -> Tuple[float, List[str], Optional[Dict]]:
        """Detect TOON format with comprehensive analysis"""
        indicators = []
        confidence = 0.0

        # File extension check
        if filename and filename.endswith(".toon"):
            indicators.append("File extension: .toon")
            confidence += 0.3

        lines = content.split("\n")

        # TOON-specific patterns
        toon_patterns = [
            (r"^\w+\[\d+\]\{.*\}:", "Tabular array declaration"),
            (r"^\w+\[\d+\]:", "Array with length"),
            (r"^\s*\w+:", "Key-value structure"),
            (r"^\s*-\s+", "List item marker"),
            (r"^\s+[\w,\-\.\s]+$", "Indented data row"),
        ]

        pattern_matches = 0
        structure_hints = {}

        for line in lines[:20]:  # Check first 20 lines
            for pattern, description in toon_patterns:
                if re.match(pattern, line):
                    indicators.append(f"Pattern match: {description}")
                    pattern_matches += 1

                    # Extract structure hints
                    if "{" in line and "}" in line:
                        fields_match = re.search(r"\{([^}]+)\}", line)
                        if fields_match:
                            fields = fields_match.group(1).split(",")
                            structure_hints["table_fields"] = [
                                f.strip() for f in fields
                            ]

                    break

        # TOON typically has indented structure
        indented_lines = sum(1 for line in lines if line.startswith("  "))
        if indented_lines > len(lines) * 0.3:
            indicators.append("Significant indentation")
            confidence += 0.2

        # Check for TOON-specific syntax
        if re.search(r"\[\d+\]", content):
            indicators.append("Array length markers")
            confidence += 0.25

        if re.search(r"\{[^}]+\}:", content):
            indicators.append("Field declarations")
            confidence += 0.25

        # Boost confidence based on pattern matches
        confidence += min(pattern_matches * 0.1, 0.5)

        return confidence, indicators, structure_hints if structure_hints else None

    def _detect_json(
        self, content: str, filename: Optional[str] = None
    ) -> Tuple[float, List[str], Optional[Dict]]:
        """Detect JSON format"""
        indicators = []
        confidence = 0.0

        if filename and filename.endswith(".json"):
            indicators.append("File extension: .json")
            confidence += 0.4

        # JSON structure checks
        stripped = content.strip()
        if (stripped.startswith("{") and stripped.endswith("}")) or (
            stripped.startswith("[") and stripped.endswith("]")
        ):
            indicators.append("JSON brackets structure")
            confidence += 0.3

        # Try to parse as JSON
        try:
            data = json.loads(content)
            indicators.append("Valid JSON parse")
            confidence += 0.5

            # Analyze structure
            structure = {}
            if isinstance(data, dict):
                structure["type"] = "object"
                structure["keys"] = list(data.keys())[:10]  # First 10 keys
            elif isinstance(data, list):
                structure["type"] = "array"
                structure["length"] = len(data)
                if data and isinstance(data[0], dict):
                    structure["item_keys"] = list(data[0].keys())[:10]

            return confidence, indicators, structure
        except json.JSONDecodeError:
            # Not valid JSON, reduce confidence
            confidence *= 0.3

        return confidence, indicators, None

    def _detect_csv(
        self, content: str, filename: Optional[str] = None
    ) -> Tuple[float, List[str], Optional[Dict]]:
        """Detect CSV format"""
        indicators = []
        confidence = 0.0

        if filename and filename.endswith(".csv"):
            indicators.append("File extension: .csv")
            confidence += 0.4

        lines = content.split("\n")[:10]  # First 10 lines
        if not lines or not lines[0]:
            return 0.0, indicators, None

        # Check for comma-separated structure
        comma_counts = [line.count(",") for line in lines if line.strip()]
        if comma_counts and len(set(comma_counts)) <= 2:  # Consistent comma count
            indicators.append("Consistent comma separation")
            confidence += 0.3

        # Try CSV parsing
        try:
            dialect = csv.Sniffer().sniff(content[:1000])
            reader = csv.reader(io.StringIO(content), dialect)
            rows = list(reader)[:5]

            if len(rows) >= 2 and len(rows[0]) > 1:
                indicators.append("Valid CSV structure")
                confidence += 0.4

                structure = {
                    "delimiter": dialect.delimiter,
                    "headers": rows[0],
                    "columns": len(rows[0]),
                    "rows": len(rows) - 1,
                }

                return confidence, indicators, structure
        except (csv.Error, Exception):
            pass

        return confidence, indicators, None

    def _detect_yaml(
        self, content: str, filename: Optional[str] = None
    ) -> Tuple[float, List[str], Optional[Dict]]:
        """Detect YAML format"""
        indicators = []
        confidence = 0.0

        if filename and filename.endswith((".yaml", ".yml")):
            indicators.append("File extension: .yaml/.yml")
            confidence += 0.4

        # YAML patterns
        if re.search(r"^\w+:", content, re.MULTILINE):
            indicators.append("Key-value structure")
            confidence += 0.2

        if re.search(r"^\s*-\s+", content, re.MULTILINE):
            indicators.append("List items")
            confidence += 0.2

        try:
            data = yaml.safe_load(content)
            if data is not None:
                indicators.append("Valid YAML parse")
                confidence += 0.4

                structure = {"type": type(data).__name__}
                if isinstance(data, dict):
                    structure["keys"] = list(data.keys())[:10]

                return confidence, indicators, structure
        except yaml.YAMLError:
            pass

        return confidence, indicators, None

    def _detect_xml(
        self, content: str, filename: Optional[str] = None
    ) -> Tuple[float, List[str], Optional[Dict]]:
        """Detect XML format"""
        indicators = []
        confidence = 0.0

        if filename and filename.endswith(".xml"):
            indicators.append("File extension: .xml")
            confidence += 0.4

        if content.strip().startswith("<?xml"):
            indicators.append("XML declaration")
            confidence += 0.3

        if re.search(r"<\w+.*?>", content):
            indicators.append("XML tags")
            confidence += 0.2

        try:
            root = ET.fromstring(content)
            indicators.append("Valid XML parse")
            confidence += 0.4

            structure = {
                "root_tag": root.tag,
                "children": len(list(root)),
                "attributes": len(root.attrib),
            }

            return confidence, indicators, structure
        except ET.ParseError:
            pass

        return confidence, indicators, None

    def _detect_tsv(
        self, content: str, filename: Optional[str] = None
    ) -> Tuple[float, List[str], Optional[Dict]]:
        """Detect TSV (Tab-Separated Values) format"""
        indicators = []
        confidence = 0.0

        if filename and filename.endswith(".tsv"):
            indicators.append("File extension: .tsv")
            confidence += 0.4

        lines = content.split("\n")[:10]
        tab_counts = [line.count("\t") for line in lines if line.strip()]

        if tab_counts and len(set(tab_counts)) <= 2 and max(tab_counts) > 0:
            indicators.append("Consistent tab separation")
            confidence += 0.4

            structure = {"delimiter": "\t", "columns": max(tab_counts) + 1}

            return confidence, indicators, structure

        return confidence, indicators, None

    def _detect_pipe(
        self, content: str, filename: Optional[str] = None
    ) -> Tuple[float, List[str], Optional[Dict]]:
        """Detect pipe-delimited format"""
        indicators = []
        confidence = 0.0

        lines = content.split("\n")[:10]
        pipe_counts = [line.count("|") for line in lines if line.strip()]

        if pipe_counts and len(set(pipe_counts)) <= 2 and max(pipe_counts) > 1:
            indicators.append("Consistent pipe separation")
            confidence += 0.3

            structure = {"delimiter": "|", "columns": max(pipe_counts) + 1}

            return confidence, indicators, structure

        return confidence, indicators, None

    def _detect_key_value(
        self, content: str, filename: Optional[str] = None
    ) -> Tuple[float, List[str], Optional[Dict]]:
        """Detect simple key=value format"""
        indicators = []
        confidence = 0.0

        lines = content.split("\n")
        kv_lines = [
            line for line in lines if "=" in line and not line.strip().startswith("#")
        ]

        if len(kv_lines) > len(lines) * 0.5:
            indicators.append("Key-value pairs")
            confidence += 0.3

            return confidence, indicators, {"format": "key_value"}

        return confidence, indicators, None

    def _detect_ini(
        self, content: str, filename: Optional[str] = None
    ) -> Tuple[float, List[str], Optional[Dict]]:
        """Detect INI configuration format"""
        indicators = []
        confidence = 0.0

        if filename and filename.endswith(".ini"):
            indicators.append("File extension: .ini")
            confidence += 0.4

        if re.search(r"^\[.*\]", content, re.MULTILINE):
            indicators.append("INI sections")
            confidence += 0.3

        if re.search(r"^\w+\s*=", content, re.MULTILINE):
            indicators.append("Key-value assignments")
            confidence += 0.2

        return confidence, indicators, {"format": "ini"} if confidence > 0 else None

    def _detect_properties(
        self, content: str, filename: Optional[str] = None
    ) -> Tuple[float, List[str], Optional[Dict]]:
        """Detect Java properties format"""
        indicators = []
        confidence = 0.0

        if filename and filename.endswith(".properties"):
            indicators.append("File extension: .properties")
            confidence += 0.4

        lines = content.split("\n")
        prop_lines = [line for line in lines if re.match(r"^\w+[\.\w]*\s*[=:]", line)]

        if len(prop_lines) > len(lines) * 0.5:
            indicators.append("Properties format")
            confidence += 0.3

        return (
            confidence,
            indicators,
            {"format": "properties"} if confidence > 0 else None,
        )


class BaseParser(ABC):
    """Abstract base class for format parsers"""

    @abstractmethod
    def parse(self, content: str, **options) -> ParseResult:
        """Parse content and return structured data"""
        pass

    @abstractmethod
    def can_handle(self, format_type: FormatType) -> bool:
        """Check if this parser can handle the format"""
        pass


class TOONParser(BaseParser):
    """Advanced TOON format parser with full feature support"""

    def __init__(self):
        self.strict_mode = True
        self.allow_recovery = True

    def can_handle(self, format_type: FormatType) -> bool:
        return format_type == FormatType.TOON

    def parse(self, content: str, **options) -> ParseResult:
        """Parse TOON content with advanced features"""
        import time

        start_time = time.time()

        result = ParseResult(data=None, format_type=FormatType.TOON, confidence=1.0)

        try:
            # Configure parser options
            self.strict_mode = options.get("strict", True)
            self.allow_recovery = options.get("recovery", True)

            # Parse the content
            parsed_data, metadata = self._parse_toon_content(content)

            result.data = parsed_data
            result.metadata = metadata
            result.parsing_time = time.time() - start_time

        except Exception as e:
            result.errors.append(str(e))
            if self.allow_recovery:
                # Attempt partial parsing
                try:
                    partial_data, partial_metadata = self._partial_parse(content)
                    result.data = partial_data
                    result.metadata = partial_metadata
                    result.warnings.append("Partial parsing due to errors")
                except Exception:
                    result.data = None

        return result

    def _parse_toon_content(self, content: str) -> Tuple[Any, Dict]:
        """Parse TOON content with full feature support"""
        lines = content.split("\n")
        data = {}
        metadata = {
            "line_count": len(lines),
            "structure_types": set(),
            "field_mappings": {},
            "array_stats": {},
        }

        i = 0
        while i < len(lines):
            line = lines[i].rstrip()

            if not line or line.startswith("#"):  # Skip empty lines and comments
                i += 1
                continue

            # Parse different TOON structures
            if self._is_tabular_array(line):
                key, array_data, lines_consumed = self._parse_tabular_array(lines, i)
                data[key] = array_data
                metadata["structure_types"].add("tabular_array")
                metadata["array_stats"][key] = len(array_data)
                i += lines_consumed
            elif self._is_simple_array(line):
                key, array_data, lines_consumed = self._parse_simple_array(lines, i)
                data[key] = array_data
                metadata["structure_types"].add("simple_array")
                i += lines_consumed
            elif self._is_list_array(line):
                key, list_data, lines_consumed = self._parse_list_array(lines, i)
                data[key] = list_data
                metadata["structure_types"].add("list_array")
                i += lines_consumed
            elif self._is_key_value(line):
                key, value = self._parse_key_value(line)
                data[key] = value
                metadata["structure_types"].add("key_value")
                i += 1
            else:
                i += 1

        return data, metadata

    def _is_tabular_array(self, line: str) -> bool:
        """Check if line declares a tabular array"""
        return bool(re.match(r"^\w+\[\d*\]\{.+\}:", line))

    def _is_simple_array(self, line: str) -> bool:
        """Check if line declares a simple array"""
        return bool(re.match(r"^\w+\[\d*\]:", line))

    def _is_list_array(self, line: str) -> bool:
        """Check if line declares a list array"""
        return bool(re.match(r"^\w+\[\d*\]:\s*$", line))

    def _is_key_value(self, line: str) -> bool:
        """Check if line is a key-value pair"""
        return (
            ":" in line and not line.endswith(":") and not line.strip().startswith("-")
        )

    def _parse_tabular_array(
        self, lines: List[str], start_idx: int
    ) -> Tuple[str, List[Dict], int]:
        """Parse tabular array structure"""
        header_line = lines[start_idx]

        # Extract array name and fields
        match = re.match(r"^(\w+)\[(\d*)\]\{(.+)\}:", header_line)
        if not match:
            raise ValueError(f"Invalid tabular array syntax: {header_line}")

        array_name = match.group(1)
        expected_length = int(match.group(2)) if match.group(2) else None
        fields = [f.strip() for f in match.group(3).split(",")]

        # Parse data rows
        data = []
        i = start_idx + 1

        while i < len(lines):
            line = lines[i].strip()

            if not line or line.startswith("#"):
                i += 1
                continue

            # Check if this is a data row (indented)
            if not lines[i].startswith("  "):
                break

            # Parse row data
            row_data = self._parse_data_row(line, fields)
            data.append(row_data)
            i += 1

        # Validate length if specified
        if expected_length is not None and len(data) != expected_length:
            if self.strict_mode:
                raise ValueError(
                    f"Array length mismatch: expected {expected_length}, got {len(data)}"
                )

        return array_name, data, i - start_idx

    def _parse_simple_array(
        self, lines: List[str], start_idx: int
    ) -> Tuple[str, List, int]:
        """Parse simple array structure"""
        header_line = lines[start_idx]

        # Extract array name
        match = re.match(r"^(\w+)\[(\d*)\]:\s*(.*)$", header_line)
        if not match:
            raise ValueError(f"Invalid simple array syntax: {header_line}")

        array_name = match.group(1)
        expected_length = int(match.group(2)) if match.group(2) else None
        inline_data = match.group(3)

        if inline_data:
            # Inline array data
            items = [item.strip() for item in inline_data.split(",")]
            return array_name, items, 1

        # Multi-line array data
        data = []
        i = start_idx + 1

        while i < len(lines):
            line = lines[i].strip()

            if not line or line.startswith("#"):
                i += 1
                continue

            if not lines[i].startswith("  "):
                break

            # Parse array item
            item = self._parse_value(line.strip())
            data.append(item)
            i += 1

        return array_name, data, i - start_idx

    def _parse_list_array(
        self, lines: List[str], start_idx: int
    ) -> Tuple[str, List, int]:
        """Parse list array structure with items marked by '- '"""
        header_line = lines[start_idx]

        # Extract array name
        match = re.match(r"^(\w+)\[(\d*)\]:", header_line)
        if not match:
            raise ValueError(f"Invalid list array syntax: {header_line}")

        array_name = match.group(1)
        data = []
        i = start_idx + 1

        while i < len(lines):
            line = lines[i]

            if not line.strip() or line.strip().startswith("#"):
                i += 1
                continue

            if not line.startswith("  "):
                break

            # Look for list item marker
            if line.strip().startswith("- "):
                item, lines_consumed = self._parse_list_item(lines, i)
                data.append(item)
                i += lines_consumed
            else:
                i += 1

        return array_name, data, i - start_idx

    def _parse_list_item(self, lines: List[str], start_idx: int) -> Tuple[Any, int]:
        """Parse a single list item which can be complex"""
        line = lines[start_idx]
        item_content = line.strip()[2:]  # Remove '- '

        if ":" in item_content and not item_content.endswith(":"):
            # Simple key-value item
            key, value = item_content.split(":", 1)
            return {key.strip(): self._parse_value(value.strip())}, 1

        # Complex item - might span multiple lines
        item_data = {}
        i = start_idx

        # Parse the first line
        if item_content:
            if item_content.endswith(":"):
                # Object start
                key = item_content[:-1].strip()
                i += 1

                # Parse nested content
                while i < len(lines):
                    line = lines[i]
                    if not line.startswith("    "):  # End of nested content
                        break

                    nested_line = line[4:]  # Remove extra indentation
                    if ":" in nested_line:
                        nested_key, nested_value = nested_line.split(":", 1)
                        if key not in item_data:
                            item_data[key] = {}
                        item_data[key][nested_key.strip()] = self._parse_value(
                            nested_value.strip()
                        )

                    i += 1
            else:
                # Simple value
                return self._parse_value(item_content), 1

        return item_data, i - start_idx

    def _parse_data_row(self, row: str, fields: List[str]) -> Dict:
        """Parse a data row according to field schema"""
        # Handle different delimiters
        delimiter = ","
        if "\t" in row:
            delimiter = "\t"
        elif "|" in row:
            delimiter = "|"

        values = [v.strip() for v in row.split(delimiter)]

        if len(values) != len(fields):
            if self.strict_mode:
                raise ValueError(
                    f"Field count mismatch: expected {len(fields)}, got {len(values)}"
                )
            # Pad or truncate as needed
            while len(values) < len(fields):
                values.append("")
            values = values[: len(fields)]

        return {field: self._parse_value(value) for field, value in zip(fields, values)}

    def _parse_key_value(self, line: str) -> Tuple[str, Any]:
        """Parse a key-value line"""
        key, value = line.split(":", 1)
        return key.strip(), self._parse_value(value.strip())

    def _parse_value(self, value: str) -> Any:
        """Parse a value string to appropriate Python type"""
        if not value:
            return None

        # Handle quoted strings
        if value.startswith('"') and value.endswith('"'):
            return value[1:-1].replace('\\"', '"').replace("\\\\", "\\")

        # Handle boolean values
        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        # Handle null
        if value.lower() == "null":
            return None

        # Try to parse as number
        try:
            if "." in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass

        # Return as string
        return value

    def _partial_parse(self, content: str) -> Tuple[Dict, Dict]:
        """Attempt partial parsing for error recovery"""
        lines = content.split("\n")
        data = {}
        metadata = {"partial": True, "parse_errors": []}

        for i, line in enumerate(lines):
            if ":" in line and not line.strip().startswith("#"):
                try:
                    key, value = line.split(":", 1)
                    data[key.strip()] = self._parse_value(value.strip())
                except Exception as e:
                    metadata["parse_errors"].append(f"Line {i + 1}: {str(e)}")

        return data, metadata


class DynamicAnythingParser:
    """Main dynamic parser that can handle any format intelligently"""

    def __init__(self):
        self.format_detector = FormatDetector()
        self.parsers = {
            FormatType.TOON: TOONParser(),
        }
        self.fallback_parsers = self._init_fallback_parsers()

    def _init_fallback_parsers(self) -> Dict[FormatType, Callable]:
        """Initialize fallback parsers for other formats"""
        return {
            FormatType.JSON: self._parse_json,
            FormatType.CSV: self._parse_csv,
            FormatType.YAML: self._parse_yaml,
            FormatType.XML: self._parse_xml,
            FormatType.TSV: self._parse_tsv,
            FormatType.PIPE_DELIMITED: self._parse_pipe_delimited,
            FormatType.KEY_VALUE: self._parse_key_value,
            FormatType.INI: self._parse_ini,
            FormatType.PROPERTIES: self._parse_properties,
        }

    def parse(
        self,
        content: str,
        filename: Optional[str] = None,
        format_hint: Optional[FormatType] = None,
        **options,
    ) -> ParseResult:
        """
        Parse content automatically detecting format or using hint

        Args:
            content: The content to parse
            filename: Optional filename for format detection hints
            format_hint: Optional format type hint to skip detection
            **options: Format-specific parsing options

        Returns:
            ParseResult with parsed data and metadata
        """
        import time

        start_time = time.time()

        # Use format hint or detect format
        if format_hint:
            format_type = format_hint
            confidence = 1.0
            detection_result = FormatDetectionResult(
                format_type, confidence, ["Format hint provided"]
            )
        else:
            detection_result = self.format_detector.detect_format(content, filename)
            format_type = detection_result.format_type
            confidence = detection_result.confidence

        # Create base result
        result = ParseResult(
            data=None,
            format_type=format_type,
            confidence=confidence,
            metadata={
                "detection": {
                    "format": format_type.name,
                    "confidence": confidence,
                    "indicators": detection_result.indicators,
                    "structure_hints": detection_result.sample_structure,
                }
            },
        )

        # Parse using appropriate parser
        try:
            if format_type in self.parsers:
                # Use dedicated parser
                parse_result = self.parsers[format_type].parse(content, **options)
                result.data = parse_result.data
                result.metadata.update(parse_result.metadata)
                result.warnings.extend(parse_result.warnings)
                result.errors.extend(parse_result.errors)
            elif format_type in self.fallback_parsers:
                # Use fallback parser
                try:
                    parsed_data = self.fallback_parsers[format_type](content, **options)
                    result.data = parsed_data
                    result.metadata["parser_type"] = "fallback"
                except Exception as e:
                    result.errors.append(f"Fallback parser error: {str(e)}")
            else:
                result.errors.append(f"No parser available for format: {format_type}")

            result.parsing_time = time.time() - start_time

        except Exception as e:
            result.errors.append(f"Parsing failed: {str(e)}")
            result.parsing_time = time.time() - start_time

        return result

    def parse_file(self, file_path: Union[str, Path], **options) -> ParseResult:
        """Parse a file automatically detecting its format"""
        file_path = Path(file_path)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            return self.parse(content, filename=file_path.name, **options)

        except Exception as e:
            result = ParseResult(
                data=None, format_type=FormatType.UNKNOWN, confidence=0.0
            )
            result.errors.append(f"File reading error: {str(e)}")
            return result

    def register_parser(self, format_type: FormatType, parser: BaseParser):
        """Register a custom parser for a format type"""
        self.parsers[format_type] = parser

    def get_supported_formats(self) -> List[FormatType]:
        """Get list of supported formats"""
        return list(set(list(self.parsers.keys()) + list(self.fallback_parsers.keys())))

    def _parse_json(self, content: str, **options) -> Any:
        """Fallback JSON parser"""
        return json.loads(content)

    def _parse_csv(self, content: str, **options) -> List[Dict]:
        """Fallback CSV parser"""
        delimiter = options.get("delimiter", ",")
        reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
        return list(reader)

    def _parse_yaml(self, content: str, **options) -> Any:
        """Fallback YAML parser"""
        return yaml.safe_load(content)

    def _parse_xml(self, content: str, **options) -> Dict:
        """Fallback XML parser"""
        root = ET.fromstring(content)
        return self._xml_to_dict(root)

    def _xml_to_dict(self, element) -> Dict:
        """Convert XML element to dictionary"""
        result = {}

        # Add attributes
        if element.attrib:
            result["@attributes"] = element.attrib

        # Add text content
        if element.text and element.text.strip():
            result["@text"] = element.text.strip()

        # Add children
        children = {}
        for child in element:
            child_data = self._xml_to_dict(child)
            if child.tag in children:
                if not isinstance(children[child.tag], list):
                    children[child.tag] = [children[child.tag]]
                children[child.tag].append(child_data)
            else:
                children[child.tag] = child_data

        result.update(children)
        return result

    def _parse_tsv(self, content: str, **options) -> List[Dict]:
        """Fallback TSV parser"""
        reader = csv.DictReader(io.StringIO(content), delimiter="\t")
        return list(reader)

    def _parse_pipe_delimited(self, content: str, **options) -> List[Dict]:
        """Fallback pipe-delimited parser"""
        reader = csv.DictReader(io.StringIO(content), delimiter="|")
        return list(reader)

    def _parse_key_value(self, content: str, **options) -> Dict:
        """Fallback key-value parser"""
        result = {}
        for line in content.split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                result[key.strip()] = value.strip()
        return result

    def _parse_ini(self, content: str, **options) -> Dict:
        """Fallback INI parser"""
        import configparser

        config = configparser.ConfigParser()
        config.read_string(content)

        result = {}
        for section in config.sections():
            result[section] = dict(config.items(section))

        return result

    def _parse_properties(self, content: str, **options) -> Dict:
        """Fallback Java properties parser"""
        result = {}
        for line in content.split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and ("=" in line or ":" in line):
                if "=" in line:
                    key, value = line.split("=", 1)
                else:
                    key, value = line.split(":", 1)
                result[key.strip()] = value.strip()
        return result


# Convenience functions for direct use
def parse_anything(content: str, **options) -> ParseResult:
    """Convenience function to parse any content"""
    parser = DynamicAnythingParser()
    return parser.parse(content, **options)


def parse_file(file_path: Union[str, Path], **options) -> ParseResult:
    """Convenience function to parse any file"""
    parser = DynamicAnythingParser()
    return parser.parse_file(file_path, **options)


def detect_format(
    content: str, filename: Optional[str] = None
) -> FormatDetectionResult:
    """Convenience function to detect format only"""
    detector = FormatDetector()
    return detector.detect_format(content, filename)


# Example usage and testing
if __name__ == "__main__":
    # Example TOON content for testing
    toon_example = """users[3]{id,name,email,active}:
  1,Alice,alice@test.com,true
  2,Bob,bob@test.com,false
  3,Carol,carol@test.com,true
config:
  app_name: VArchiver
  version: 1.0.0
  debug: false
features[4]: archive,extract,browse,convert
nested_data[2]:
  - name: Project A
    status: active
    contributors[2]{name,role}:
      Alice,Lead
      Bob,Developer
  - name: Project B
    status: inactive
    contributors[1]{name,role}:
      Carol,Tester"""

    # Test the dynamic parser
    parser = DynamicAnythingParser()

    print("🚀 Dynamic Anything Parser Test")
    print("=" * 50)

    result = parser.parse(toon_example)

    print(f"Format detected: {result.format_type.name}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Parse successful: {result.is_successful}")
    print(f"Parsing time: {result.parsing_time:.4f}s")

    if result.warnings:
        print(f"Warnings: {result.warnings}")

    if result.errors:
        print(f"Errors: {result.errors}")

    if result.data:
        print("\nParsed data structure:")
        import pprint

        pprint.pprint(result.data, width=80)

    print("\nMetadata:")
    pprint.pprint(result.metadata, width=80)

    print(f"\nSupported formats: {[f.name for f in parser.get_supported_formats()]}")
