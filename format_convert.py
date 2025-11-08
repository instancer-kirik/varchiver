#!/usr/bin/env python3
"""
TOON Format Converter CLI
Command-line interface for converting between TOON, JSON, and CSV formats

Usage:
    python format_convert.py input.json -o output.toon
    python format_convert.py data.toon --to json
    cat data.json | python format_convert.py --encode
    echo '{"name": "Ada"}' | python format_convert.py --stats
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# Add varchiver to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from varchiver.utils.format_converter import FormatConverter
except ImportError:
    print(
        "Error: Could not import FormatConverter. Make sure you're in the varchiver directory."
    )
    sys.exit(1)


def detect_format(file_path: str) -> str:
    """Auto-detect format from file extension"""
    ext = Path(file_path).suffix.lower().lstrip(".")
    if ext in ["json", "toon", "csv"]:
        return ext
    return "json"  # default


def read_input(input_source: Optional[str]) -> tuple[str, str]:
    """Read input from file or stdin, return (content, detected_format)"""
    if input_source is None or input_source == "-":
        # Read from stdin
        content = sys.stdin.read()
        # Try to detect format from content
        content_stripped = content.strip()
        if content_stripped.startswith("{") or content_stripped.startswith("["):
            return content, "json"
        elif (
            "," in content and "\n" in content and not content_stripped.startswith("[")
        ):
            return content, "csv"
        else:
            return content, "toon"
    else:
        # Read from file
        try:
            with open(input_source, "r", encoding="utf-8") as f:
                content = f.read()
            detected_format = detect_format(input_source)
            return content, detected_format
        except FileNotFoundError:
            print(f"Error: File not found: {input_source}")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}")
            sys.exit(1)


def write_output(content: str, output_path: Optional[str]):
    """Write output to file or stdout"""
    if output_path:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Output written to: {output_path}", file=sys.stderr)
        except Exception as e:
            print(f"Error writing output file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(content)


def show_stats(
    original_content: str,
    converted_content: str,
    original_format: str,
    target_format: str,
):
    """Display conversion statistics"""
    original_size = len(original_content)
    converted_size = len(converted_content)

    # Simple token estimation
    original_tokens = (
        len(original_content.split())
        + original_content.count(",")
        + original_content.count("{")
        + original_content.count("}")
    )
    converted_tokens = (
        len(converted_content.split())
        + converted_content.count(",")
        + converted_content.count(":")
    )

    size_reduction = (
        ((original_size - converted_size) / original_size * 100)
        if original_size > 0
        else 0
    )
    token_savings = (
        ((original_tokens - converted_tokens) / original_tokens * 100)
        if original_tokens > 0
        else 0
    )

    print(
        f"\n📊 Conversion Statistics ({original_format.upper()} → {target_format.upper()}):",
        file=sys.stderr,
    )
    print(
        f"Size: {original_size} → {converted_size} chars ({size_reduction:+.1f}%)",
        file=sys.stderr,
    )
    print(
        f"Est. tokens: {original_tokens} → {converted_tokens} ({token_savings:+.1f}%)",
        file=sys.stderr,
    )

    if target_format == "toon" and token_savings > 0:
        if token_savings > 40:
            print("🟢 Excellent token efficiency!", file=sys.stderr)
        elif token_savings > 20:
            print("🟡 Good token efficiency", file=sys.stderr)
        elif token_savings > 0:
            print("🟠 Moderate token efficiency", file=sys.stderr)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser"""
    parser = argparse.ArgumentParser(
        description="Convert between TOON, JSON, and CSV formats",
        epilog="""
Examples:
  %(prog)s data.json -o output.toon          # JSON to TOON
  %(prog)s data.toon --to json               # TOON to JSON (stdout)
  cat data.json | %(prog)s --encode          # JSON to TOON via pipe
  echo '{"x":1}' | %(prog)s --stats          # Show conversion stats
  %(prog)s data.csv --to toon --delimiter "|" # CSV to TOON with pipe delimiter
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Input/output
    parser.add_argument(
        "input", nargs="?", help='Input file path (use "-" or omit for stdin)'
    )
    parser.add_argument(
        "-o", "--output", help="Output file path (prints to stdout if omitted)"
    )

    # Format control
    parser.add_argument(
        "--from",
        dest="input_format",
        choices=["json", "toon", "csv"],
        help="Input format (auto-detected if not specified)",
    )
    parser.add_argument(
        "--to",
        dest="output_format",
        choices=["json", "toon", "csv"],
        help="Output format (auto-detected from output file extension)",
    )

    # Convenience flags
    parser.add_argument(
        "-e",
        "--encode",
        action="store_true",
        help="Force encode to TOON (same as --to toon)",
    )
    parser.add_argument(
        "-d",
        "--decode",
        action="store_true",
        help="Force decode from TOON (same as --from toon --to json)",
    )

    # TOON options
    parser.add_argument(
        "--delimiter",
        choices=["comma", "tab", "pipe", ",", "\t", "|"],
        default="comma",
        help="TOON array delimiter (default: comma)",
    )
    parser.add_argument(
        "--indent", type=int, default=2, help="Indentation size (default: 2)"
    )
    parser.add_argument(
        "--length-marker",
        action="store_true",
        help="Add # prefix to TOON array lengths",
    )

    # Other options
    parser.add_argument(
        "--stats", action="store_true", help="Show conversion statistics"
    )
    parser.add_argument(
        "--table-name",
        default="data",
        help="Table name for CSV to JSON conversion (default: data)",
    )
    parser.add_argument(
        "--no-strict",
        action="store_true",
        help="Disable strict validation when decoding TOON",
    )

    return parser


def normalize_delimiter(delimiter: str) -> str:
    """Convert delimiter name to actual character"""
    delimiter_map = {
        "comma": ",",
        "tab": "\t",
        "pipe": "|",
        ",": ",",
        "\t": "\t",
        "|": "|",
    }
    return delimiter_map.get(delimiter, ",")


def main():
    """Main CLI function"""
    parser = create_parser()
    args = parser.parse_args()

    # Handle convenience flags
    if args.encode:
        args.output_format = "toon"
    elif args.decode:
        args.input_format = "toon"
        args.output_format = "json"

    # Read input
    content, detected_input_format = read_input(args.input)

    if not content.strip():
        print("Error: No input data provided", file=sys.stderr)
        sys.exit(1)

    # Determine formats
    input_format = args.input_format or detected_input_format

    if args.output_format:
        output_format = args.output_format
    elif args.output:
        output_format = detect_format(args.output)
    else:
        # Default: if input is JSON, output TOON; otherwise output JSON
        output_format = "toon" if input_format == "json" else "json"

    # Validate format combination
    if input_format == output_format:
        print(
            f"Warning: Input and output formats are the same ({input_format})",
            file=sys.stderr,
        )

    # Setup converter
    converter = FormatConverter()

    # Prepare conversion options
    toon_options = {
        "indent": args.indent,
        "delimiter": normalize_delimiter(args.delimiter),
        "length_marker": args.length_marker,
    }

    csv_options = {"table_name": args.table_name}

    json_options = {"indent": args.indent}

    # Perform conversion
    try:
        if input_format == "json" and output_format == "toon":
            result = converter.json_to_toon(content, **toon_options)
        elif input_format == "toon" and output_format == "json":
            result = converter.toon_to_json(content, **json_options)
        elif input_format == "json" and output_format == "csv":
            result = converter.json_to_csv(content)
        elif input_format == "csv" and output_format == "json":
            result = converter.csv_to_json(content, **csv_options)
        elif input_format == "toon" and output_format == "csv":
            result = converter.toon_to_csv(content)
        elif input_format == "csv" and output_format == "toon":
            result = converter.csv_to_toon(content, **toon_options)
        else:
            print(
                f"Error: Unsupported conversion: {input_format} → {output_format}",
                file=sys.stderr,
            )
            sys.exit(1)

        # Write output
        write_output(result, args.output)

        # Show statistics if requested
        if args.stats:
            show_stats(content, result, input_format, output_format)

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input - {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Conversion failed - {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
