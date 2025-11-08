"""
Data Format Converter for TOON, JSON, and CSV formats

This module provides conversion utilities between different data formats:
- TOON (Token-Optimized Object Notation) - efficient format for LLMs
- JSON (JavaScript Object Notation) - standard web format
- CSV (Comma-Separated Values) - tabular format

TOON Format Specification (v1.3):
- Token-efficient: 30-60% fewer tokens than JSON
- Tabular arrays: declare keys once, stream data as rows
- Indentation-based structure like YAML
- Explicit lengths and fields for validation
"""

import json
import csv
import io
import re
from typing import Any, Dict, List, Union, Optional, Tuple
from pathlib import Path


class TOONEncoder:
    """Encodes Python data structures to TOON format"""

    def __init__(
        self, indent: int = 2, delimiter: str = ",", length_marker: bool = False
    ):
        self.indent = indent
        self.delimiter = delimiter
        self.length_marker = "#" if length_marker else ""
        self.level = 0

    def encode(self, data: Any) -> str:
        """Convert data to TOON format"""
        if data is None:
            return "null"
        elif isinstance(data, bool):
            return "true" if data else "false"
        elif isinstance(data, (int, float)):
            if isinstance(data, float) and (
                data != data or data == float("inf") or data == float("-inf")
            ):
                return "null"
            return str(data)
        elif isinstance(data, str):
            return self._quote_string(data)
        elif isinstance(data, list):
            return self._encode_array(data)
        elif isinstance(data, dict):
            return self._encode_object(data)
        else:
            return "null"

    def _quote_string(self, s: str) -> str:
        """Quote string if necessary according to TOON rules"""
        if not s:
            return '""'

        # Check if quoting is needed
        needs_quotes = (
            s.startswith(" ")
            or s.endswith(" ")
            or self.delimiter in s
            or ":" in s
            or '"' in s
            or "\\" in s
            or s in ("true", "false", "null")
            or s.startswith("- ")
            or self._looks_like_number(s)
            or self._looks_like_structural(s)
            or any(ord(c) < 32 for c in s)
        )

        if not needs_quotes:
            return s

        # Escape quotes and backslashes
        escaped = s.replace("\\", "\\\\").replace('"', '\\"')
        # Escape control characters
        escaped = escaped.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")
        return f'"{escaped}"'

    def _looks_like_number(self, s: str) -> bool:
        """Check if string looks like a number"""
        try:
            float(s)
            return True
        except ValueError:
            return False

    def _looks_like_structural(self, s: str) -> bool:
        """Check if string looks like TOON structural tokens"""
        return bool(re.match(r"^\[.*\]$|^\{.*\}$", s))

    def _encode_array(self, arr: List[Any]) -> str:
        """Encode array to TOON format"""
        if not arr:
            return f"[{self.length_marker}0]:"

        # Check if all items are objects with same primitive keys
        if self._is_tabular_array(arr):
            return self._encode_tabular_array(arr)
        elif all(not isinstance(item, (dict, list)) for item in arr):
            # Primitive array (inline)
            values = [self.encode(item) for item in arr]
            return f"[{self.length_marker}{len(arr)}]: {self.delimiter.join(values)}"
        else:
            # Mixed/complex array (list format)
            return self._encode_list_array(arr)

    def _is_tabular_array(self, arr: List[Any]) -> bool:
        """Check if array can be encoded in tabular format"""
        if not arr or not isinstance(arr[0], dict):
            return False

        first_keys = set(arr[0].keys())
        return all(
            isinstance(item, dict)
            and set(item.keys()) == first_keys
            and all(not isinstance(v, (dict, list)) for v in item.values())
            for item in arr
        )

    def _encode_tabular_array(self, arr: List[Dict[str, Any]]) -> str:
        """Encode array as tabular format"""
        if not arr:
            return f"[{self.length_marker}0]:"

        keys = list(arr[0].keys())
        header_delimiter = self.delimiter if self.delimiter != "," else ""
        if header_delimiter:
            header_delimiter = (
                f"{self.delimiter}" if self.delimiter in ["\t", "|"] else ""
            )
            keys_str = self.delimiter.join(keys)
        else:
            keys_str = ",".join(keys)

        result = f"[{self.length_marker}{len(arr)}{header_delimiter}]{{{keys_str}}}:\n"

        for item in arr:
            values = [self.encode(item[key]) for key in keys]
            indent_str = " " * (self.level * self.indent + self.indent)
            result += f"{indent_str}{self.delimiter.join(values)}\n"

        return result.rstrip("\n")

    def _encode_list_array(self, arr: List[Any]) -> str:
        """Encode array as list format"""
        result = f"[{self.length_marker}{len(arr)}]:\n"
        self.level += 1

        for item in arr:
            indent_str = " " * (self.level * self.indent)
            if isinstance(item, dict) and item:
                # First key on hyphen line, rest indented
                first_key = next(iter(item.keys()))
                first_value = self.encode(item[first_key])
                result += f"{indent_str}- {first_key}: {first_value}\n"

                for key in list(item.keys())[1:]:
                    value = self.encode(item[key])
                    result += f"{indent_str}  {key}: {value}\n"
            else:
                result += f"{indent_str}- {self.encode(item)}\n"

        self.level -= 1
        return result.rstrip("\n")

    def _encode_object(self, obj: Dict[str, Any]) -> str:
        """Encode object to TOON format"""
        if not obj:
            return ""

        result = []
        self.level += 1

        for key, value in obj.items():
            indent_str = " " * (self.level * self.indent) if self.level > 0 else ""
            quoted_key = f'"{key}"' if not self._is_valid_identifier(key) else key

            if isinstance(value, dict):
                if value:
                    result.append(f"{indent_str}{quoted_key}:")
                    self.level += 1
                    nested = self._encode_object(value)
                    self.level -= 1
                    if nested:
                        result.append(nested)
                else:
                    result.append(f"{indent_str}{quoted_key}:")
            elif isinstance(value, list):
                array_result = self._encode_array(value)
                if "\n" in array_result:
                    result.append(f"{indent_str}{quoted_key}{array_result}")
                else:
                    result.append(f"{indent_str}{quoted_key}{array_result}")
            else:
                result.append(f"{indent_str}{quoted_key}: {self.encode(value)}")

        self.level -= 1
        return "\n".join(result)

    def _is_valid_identifier(self, key: str) -> bool:
        """Check if key is a valid unquoted identifier"""
        return bool(re.match(r"^[a-zA-Z_][a-zA-Z0-9_.]*$", key))


class TOONDecoder:
    """Decodes TOON format to Python data structures"""

    def __init__(self, indent: int = 2, strict: bool = True):
        self.indent = indent
        self.strict = strict
        self.lines = []
        self.pos = 0

    def decode(self, toon_str: str) -> Any:
        """Convert TOON format to Python data"""
        self.lines = toon_str.strip().split("\n")
        self.pos = 0

        if not self.lines or not self.lines[0].strip():
            return {}

        return self._parse_value(0)

    def _parse_value(self, level: int) -> Any:
        """Parse value at current position"""
        if self.pos >= len(self.lines):
            return None

        line = self.lines[self.pos].rstrip()
        indent_level = (len(line) - len(line.lstrip())) // self.indent

        if indent_level != level:
            return None

        content = line.strip()

        # Array format
        if content.startswith("[") and "]:" in content:
            return self._parse_array(level)

        # Object key-value pair
        if ":" in content and not content.endswith(":"):
            key, value = content.split(":", 1)
            key = key.strip().strip('"')
            value = value.strip()
            return {key: self._parse_primitive(value)}

        # Object with nested content
        if content.endswith(":"):
            key = content[:-1].strip().strip('"')
            self.pos += 1
            nested_value = self._parse_value(level + 1)
            return {key: nested_value}

        return self._parse_primitive(content)

    def _parse_array(self, level: int) -> List[Any]:
        """Parse array format"""
        line = self.lines[self.pos].strip()
        self.pos += 1

        # Extract length and check for tabular format
        match = re.match(r"^\[#?(\d+)([^\]]*)\](?:\{([^}]+)\})?:", line)
        if not match:
            return []

        length = int(match.group(1))
        delimiter_info = match.group(2)
        fields = match.group(3)

        if length == 0:
            return []

        # Determine delimiter
        delimiter = ","
        if delimiter_info:
            if "\t" in delimiter_info:
                delimiter = "\t"
            elif "|" in delimiter_info:
                delimiter = "|"

        # Tabular format
        if fields:
            field_names = fields.split(delimiter)
            result = []

            for _ in range(length):
                if self.pos >= len(self.lines):
                    break

                data_line = self.lines[self.pos].strip()
                self.pos += 1

                values = data_line.split(delimiter)
                row = {}
                for i, field in enumerate(field_names):
                    if i < len(values):
                        row[field.strip()] = self._parse_primitive(values[i].strip())
                result.append(row)

            return result

        # List format or primitive array
        if self.pos < len(self.lines) and not self.lines[self.pos].strip().startswith(
            "-"
        ):
            # Primitive array (inline)
            data_line = self.lines[self.pos].strip()
            self.pos += 1
            values = data_line.split(delimiter)
            return [self._parse_primitive(v.strip()) for v in values]

        # List format
        result = []
        for _ in range(length):
            if self.pos >= len(self.lines):
                break

            line = self.lines[self.pos].strip()
            if line.startswith("- "):
                self.pos += 1
                item_content = line[2:]
                if ":" in item_content:
                    # Object item
                    key, value = item_content.split(":", 1)
                    item = {key.strip(): self._parse_primitive(value.strip())}

                    # Check for additional fields
                    while (
                        self.pos < len(self.lines)
                        and self.lines[self.pos].strip()
                        and not self.lines[self.pos].strip().startswith("-")
                    ):
                        field_line = self.lines[self.pos].strip()
                        if ":" in field_line:
                            field_key, field_value = field_line.split(":", 1)
                            item[field_key.strip()] = self._parse_primitive(
                                field_value.strip()
                            )
                        self.pos += 1

                    result.append(item)
                else:
                    result.append(self._parse_primitive(item_content))
            else:
                break

        return result

    def _parse_primitive(self, value: str) -> Any:
        """Parse primitive value"""
        value = value.strip()

        if not value:
            return ""

        if value == "null":
            return None
        elif value == "true":
            return True
        elif value == "false":
            return False
        elif value.startswith('"') and value.endswith('"'):
            # Quoted string
            unquoted = value[1:-1]
            # Unescape
            unquoted = unquoted.replace('\\"', '"').replace("\\\\", "\\")
            unquoted = (
                unquoted.replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r")
            )
            return unquoted
        else:
            # Try to parse as number
            try:
                if "." in value or "e" in value.lower():
                    return float(value)
                else:
                    return int(value)
            except ValueError:
                return value


class FormatConverter:
    """Main converter class for handling TOON, JSON, and CSV conversions"""

    def __init__(self):
        self.toon_encoder = TOONEncoder()
        self.toon_decoder = TOONDecoder()

    def json_to_toon(self, json_data: Union[str, Dict, List], **toon_options) -> str:
        """Convert JSON to TOON format"""
        if isinstance(json_data, str):
            data = json.loads(json_data)
        else:
            data = json_data

        encoder = TOONEncoder(**toon_options)
        return encoder.encode(data)

    def toon_to_json(self, toon_data: str, indent: Optional[int] = 2) -> str:
        """Convert TOON to JSON format"""
        data = self.toon_decoder.decode(toon_data)
        return json.dumps(data, indent=indent, ensure_ascii=False)

    def json_to_csv(
        self, json_data: Union[str, Dict, List], output_file: Optional[str] = None
    ) -> str:
        """Convert JSON to CSV format (works best with tabular data)"""
        if isinstance(json_data, str):
            data = json.loads(json_data)
        else:
            data = json_data

        # Handle different JSON structures
        if isinstance(data, list) and data and isinstance(data[0], dict):
            # Array of objects - direct conversion
            rows = data
        elif isinstance(data, dict):
            # Look for arrays of objects in the dict
            arrays = {
                k: v
                for k, v in data.items()
                if isinstance(v, list) and v and isinstance(v[0], dict)
            }

            if len(arrays) == 1:
                # Single array found - use it
                rows = list(arrays.values())[0]
            elif len(arrays) > 1:
                # Multiple arrays - create a combined structure
                combined_rows = []
                for table_name, table_data in arrays.items():
                    for row in table_data:
                        combined_row = {"table": table_name}
                        combined_row.update(row)
                        combined_rows.append(combined_row)
                rows = combined_rows
            else:
                # No suitable arrays - flatten the object
                rows = [data]
        else:
            raise ValueError("JSON structure not suitable for CSV conversion")

        if not rows:
            return ""

        # Get all unique keys
        all_keys = set()
        for row in rows:
            all_keys.update(row.keys())

        fieldnames = sorted(all_keys)

        # Create CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            # Ensure all values are strings and handle nested structures
            csv_row = {}
            for key in fieldnames:
                value = row.get(key, "")
                if isinstance(value, (dict, list)):
                    csv_row[key] = json.dumps(value)
                else:
                    csv_row[key] = str(value) if value is not None else ""
            writer.writerow(csv_row)

        csv_content = output.getvalue()
        output.close()

        if output_file:
            with open(output_file, "w", newline="", encoding="utf-8") as f:
                f.write(csv_content)

        return csv_content

    def csv_to_json(
        self, csv_data: Union[str, io.StringIO], table_name: str = "data"
    ) -> str:
        """Convert CSV to JSON format"""
        if isinstance(csv_data, str):
            # Check if it's a file path or CSV content
            if "\n" in csv_data or "," in csv_data:
                # CSV content
                input_stream = io.StringIO(csv_data)
            else:
                # File path
                with open(csv_data, "r", encoding="utf-8") as f:
                    input_stream = io.StringIO(f.read())
        else:
            input_stream = csv_data

        reader = csv.DictReader(input_stream)
        rows = []

        for row in reader:
            # Try to parse JSON values back to objects
            parsed_row = {}
            for key, value in row.items():
                if value.startswith(("{", "[")) and value.endswith(("}", "]")):
                    try:
                        parsed_row[key] = json.loads(value)
                    except json.JSONDecodeError:
                        parsed_row[key] = value
                else:
                    # Try to convert to appropriate type
                    if value.lower() in ("true", "false"):
                        parsed_row[key] = value.lower() == "true"
                    elif value.lower() == "null" or value == "":
                        parsed_row[key] = None
                    else:
                        # Try numeric conversion
                        try:
                            if "." in value:
                                parsed_row[key] = float(value)
                            else:
                                parsed_row[key] = int(value)
                        except (ValueError, TypeError):
                            parsed_row[key] = value

            rows.append(parsed_row)

        result = {table_name: rows}
        return json.dumps(result, indent=2, ensure_ascii=False)

    def toon_to_csv(self, toon_data: str, output_file: Optional[str] = None) -> str:
        """Convert TOON to CSV format"""
        json_data = self.toon_to_json(toon_data)
        return self.json_to_csv(json_data, output_file)

    def csv_to_toon(
        self,
        csv_data: Union[str, io.StringIO],
        table_name: str = "data",
        **toon_options,
    ) -> str:
        """Convert CSV to TOON format"""
        json_data = self.csv_to_json(csv_data, table_name)
        return self.json_to_toon(json_data, **toon_options)

    def convert_file(
        self,
        input_file: str,
        output_file: str,
        input_format: str = None,
        output_format: str = None,
        **options,
    ) -> bool:
        """Convert between file formats automatically detecting format from extensions"""

        input_path = Path(input_file)
        output_path = Path(output_file)

        # Auto-detect formats if not specified
        if not input_format:
            input_format = input_path.suffix.lower().lstrip(".")
        if not output_format:
            output_format = output_path.suffix.lower().lstrip(".")

        # Read input file
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading input file: {e}")
            return False

        # Convert based on format combination
        try:
            if input_format == "json" and output_format == "toon":
                result = self.json_to_toon(content, **options)
            elif input_format == "toon" and output_format == "json":
                result = self.toon_to_json(content, **options)
            elif input_format == "json" and output_format == "csv":
                result = self.json_to_csv(content, **options)
            elif input_format == "csv" and output_format == "json":
                result = self.csv_to_json(content, **options)
            elif input_format == "toon" and output_format == "csv":
                result = self.toon_to_csv(content, **options)
            elif input_format == "csv" and output_format == "toon":
                result = self.csv_to_toon(content, **options)
            else:
                print(f"Unsupported conversion: {input_format} -> {output_format}")
                return False

            # Write output file
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result)

            return True

        except Exception as e:
            print(f"Error during conversion: {e}")
            return False

    def estimate_token_savings(
        self, data: Union[str, Dict, List], source_format: str = "json"
    ) -> Dict[str, Any]:
        """Estimate token savings when converting to TOON format"""

        if source_format == "json":
            if isinstance(data, str):
                json_content = data
                parsed_data = json.loads(data)
            else:
                parsed_data = data
                json_content = json.dumps(data, indent=2)
        else:
            raise ValueError("Token estimation currently only supports JSON as source")

        toon_content = self.json_to_toon(parsed_data)

        # Simple token estimation (rough approximation)
        json_tokens = (
            len(json_content.split())
            + json_content.count(",")
            + json_content.count("{")
            + json_content.count("}")
        )
        toon_tokens = (
            len(toon_content.split())
            + toon_content.count(",")
            + toon_content.count(":")
        )

        savings = (json_tokens - toon_tokens) / json_tokens if json_tokens > 0 else 0

        return {
            "json_tokens": json_tokens,
            "toon_tokens": toon_tokens,
            "savings_percent": round(savings * 100, 1),
            "json_length": len(json_content),
            "toon_length": len(toon_content),
            "size_reduction": round(
                (len(json_content) - len(toon_content)) / len(json_content) * 100, 1
            ),
        }


def main():
    """CLI interface for format conversion"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert between TOON, JSON, and CSV formats"
    )
    parser.add_argument("input_file", help="Input file path")
    parser.add_argument("-o", "--output", required=True, help="Output file path")
    parser.add_argument(
        "--input-format",
        choices=["json", "toon", "csv"],
        help="Input format (auto-detected if not specified)",
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "toon", "csv"],
        help="Output format (auto-detected if not specified)",
    )
    parser.add_argument(
        "--delimiter",
        choices=[",", "\t", "|"],
        default=",",
        help="TOON array delimiter",
    )
    parser.add_argument("--indent", type=int, default=2, help="Indentation size")
    parser.add_argument(
        "--length-marker",
        action="store_true",
        help="Add # prefix to TOON array lengths",
    )
    parser.add_argument(
        "--table-name", default="data", help="Table name for CSV to JSON conversion"
    )
    parser.add_argument(
        "--stats", action="store_true", help="Show token count estimates and savings"
    )

    args = parser.parse_args()

    converter = FormatConverter()

    # Prepare options
    toon_options = {
        "indent": args.indent,
        "delimiter": args.delimiter,
        "length_marker": args.length_marker,
    }

    json_options = {"indent": args.indent}

    csv_options = {"table_name": args.table_name}

    # Perform conversion
    success = converter.convert_file(
        args.input_file,
        args.output,
        args.input_format,
        args.output_format,
        **toon_options,
        **json_options,
        **csv_options,
    )

    if success:
        print(f"Successfully converted {args.input_file} to {args.output}")

        # Show stats if requested
        if args.stats and args.output_format == "toon":
            try:
                with open(args.input_file, "r", encoding="utf-8") as f:
                    original_content = f.read()

                if args.input_format == "json":
                    stats = converter.estimate_token_savings(original_content, "json")
                    print(f"\nToken Efficiency:")
                    print(f"JSON tokens (estimated): {stats['json_tokens']}")
                    print(f"TOON tokens (estimated): {stats['toon_tokens']}")
                    print(f"Token savings: {stats['savings_percent']}%")
                    print(f"Size reduction: {stats['size_reduction']}%")
            except Exception as e:
                print(f"Could not calculate stats: {e}")
    else:
        print("Conversion failed")
        exit(1)


if __name__ == "__main__":
    main()
