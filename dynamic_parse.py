#!/usr/bin/env python3
"""
Dynamic Anything Parser CLI Tool
Advanced command-line interface for parsing any data format with intelligent detection

Usage:
    python dynamic_parse.py input.toon
    python dynamic_parse.py data.json --format toon --output result.toon
    cat mixed_data.csv | python dynamic_parse.py --analyze
    python dynamic_parse.py --interactive
    python dynamic_parse.py bulk_convert folder/ --to json

Features:
    - Automatic format detection with confidence scoring
    - Full TOON format support with advanced parsing
    - Batch processing and directory scanning
    - Interactive mode for exploration
    - Format conversion and validation
    - Smart content analysis and statistics
    - Plugin architecture for custom parsers

Author: VArchiver Team
Version: 1.0.0
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

# Add varchiver to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from varchiver.utils.dynamic_parser import (
        DynamicAnythingParser,
        FormatType,
        ParseResult,
        FormatDetectionResult,
        parse_anything,
        parse_file,
        detect_format,
    )
except ImportError as e:
    print(f"Error: Could not import dynamic parser modules: {e}")
    print("Make sure you're in the varchiver directory and dependencies are installed.")
    sys.exit(1)


class Colors:
    """ANSI color codes for terminal output"""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"


def colorize(text: str, color: str) -> str:
    """Add color to text if stdout is a terminal"""
    if sys.stdout.isatty():
        return f"{color}{text}{Colors.RESET}"
    return text


def format_confidence(confidence: float) -> str:
    """Format confidence with color coding"""
    if confidence >= 0.8:
        return colorize(f"{confidence:.2f}", Colors.GREEN)
    elif confidence >= 0.5:
        return colorize(f"{confidence:.2f}", Colors.YELLOW)
    else:
        return colorize(f"{confidence:.2f}", Colors.RED)


def print_header(title: str):
    """Print a formatted header"""
    print(colorize(f"\n{'=' * 60}", Colors.CYAN))
    print(colorize(f" {title}", Colors.CYAN + Colors.BOLD))
    print(colorize(f"{'=' * 60}", Colors.CYAN))


def print_detection_result(detection: FormatDetectionResult):
    """Print format detection results"""
    print(f"\n{colorize('Format Detection:', Colors.BOLD)}")
    print(f"  Format: {colorize(detection.format_type.name, Colors.GREEN)}")
    print(f"  Confidence: {format_confidence(detection.confidence)}")

    if detection.indicators:
        print(f"  Indicators:")
        for indicator in detection.indicators[:5]:  # Show top 5
            print(f"    • {indicator}")

    if detection.sample_structure:
        print(f"  Structure hints:")
        for key, value in list(detection.sample_structure.items())[:3]:
            print(f"    {key}: {value}")


def print_parse_result(result: ParseResult, show_data: bool = True):
    """Print parsing results with formatting"""
    print(f"\n{colorize('Parse Result:', Colors.BOLD)}")
    print(
        f"  Success: {colorize('✓', Colors.GREEN) if result.is_successful else colorize('✗', Colors.RED)}"
    )
    print(f"  Format: {colorize(result.format_type.name, Colors.BLUE)}")
    print(f"  Confidence: {format_confidence(result.confidence)}")
    print(f"  Parse time: {colorize(f'{result.parsing_time:.4f}s', Colors.CYAN)}")

    if result.warnings:
        print(f"  {colorize('Warnings:', Colors.YELLOW)}")
        for warning in result.warnings:
            print(f"    ⚠ {warning}")

    if result.errors:
        print(f"  {colorize('Errors:', Colors.RED)}")
        for error in result.errors:
            print(f"    ✗ {error}")

    if result.metadata:
        print(f"  Metadata:")
        detection = result.metadata.get("detection", {})
        if detection:
            print(f"    Detection indicators: {len(detection.get('indicators', []))}")

        if "structure_types" in result.metadata:
            types = result.metadata["structure_types"]
            if types:
                print(f"    Structure types: {', '.join(types)}")

        if "array_stats" in result.metadata:
            arrays = result.metadata["array_stats"]
            if arrays:
                total_items = sum(arrays.values())
                print(f"    Array items: {total_items} across {len(arrays)} arrays")


def analyze_content(content: str, filename: Optional[str] = None):
    """Analyze content and show detailed information"""
    print_header("CONTENT ANALYSIS")

    # Basic stats
    lines = content.split("\n")
    chars = len(content)
    words = len(content.split())

    print(f"Content Statistics:")
    print(f"  Lines: {colorize(str(len(lines)), Colors.CYAN)}")
    print(f"  Characters: {colorize(str(chars), Colors.CYAN)}")
    print(f"  Words: {colorize(str(words), Colors.CYAN)}")

    # Format detection
    detection = detect_format(content, filename)
    print_detection_result(detection)

    # Parse the content
    parser = DynamicAnythingParser()
    result = parser.parse(content, filename=filename)
    print_parse_result(result, show_data=False)

    # Show sample of parsed data
    if result.data and result.is_successful:
        print(f"\n{colorize('Data Preview:', Colors.BOLD)}")

        if isinstance(result.data, dict):
            print(f"  Object with {len(result.data)} keys:")
            for i, (key, value) in enumerate(list(result.data.items())[:5]):
                value_type = type(value).__name__
                if isinstance(value, (list, dict)):
                    size = len(value) if hasattr(value, "__len__") else "?"
                    print(f"    {key}: {value_type}({size})")
                else:
                    preview = str(value)[:50] + ("..." if len(str(value)) > 50 else "")
                    print(f"    {key}: {preview}")

            if len(result.data) > 5:
                print(f"    ... and {len(result.data) - 5} more")

        elif isinstance(result.data, list):
            print(f"  Array with {len(result.data)} items:")
            if result.data:
                first_item = result.data[0]
                print(f"    First item type: {type(first_item).__name__}")
                if isinstance(first_item, dict):
                    print(f"    Keys: {list(first_item.keys())[:5]}")


def convert_format(
    content: str,
    from_format: FormatType,
    to_format: FormatType,
    filename: Optional[str] = None,
    **options,
) -> str:
    """Convert content from one format to another"""
    parser = DynamicAnythingParser()

    # Parse with source format
    result = parser.parse(
        content, filename=filename, format_hint=from_format, **options
    )

    if not result.is_successful:
        raise ValueError(f"Failed to parse as {from_format.name}: {result.errors}")

    # Convert to target format
    if to_format == FormatType.JSON:
        return json.dumps(result.data, indent=2, ensure_ascii=False)
    elif to_format == FormatType.TOON:
        # Use existing TOON encoder
        from varchiver.utils.format_converter import FormatConverter

        converter = FormatConverter()
        return converter.json_to_toon(result.data, **options)
    else:
        raise ValueError(f"Conversion to {to_format.name} not yet implemented")


def process_file(
    file_path: Path,
    output_path: Optional[Path] = None,
    to_format: Optional[FormatType] = None,
    analyze: bool = False,
    **options,
):
    """Process a single file"""
    print(f"\n{colorize('Processing:', Colors.BOLD)} {file_path}")

    try:
        # Read file
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if analyze:
            analyze_content(content, file_path.name)
            return

        # Parse content
        parser = DynamicAnythingParser()
        result = parser.parse(content, filename=file_path.name, **options)

        print_parse_result(result, show_data=False)

        # Convert if requested
        if to_format and result.is_successful:
            try:
                if result.format_type == to_format:
                    print(
                        f"  {colorize('Note:', Colors.YELLOW)} Source and target formats are the same"
                    )
                    converted = content
                else:
                    converted = convert_format(
                        content,
                        result.format_type,
                        to_format,
                        file_path.name,
                        **options,
                    )

                # Output converted content
                if output_path:
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(converted)
                    print(f"  {colorize('Converted to:', Colors.GREEN)} {output_path}")
                else:
                    print(f"\n{colorize('Converted Content:', Colors.BOLD)}")
                    print(converted)

            except Exception as e:
                print(f"  {colorize('Conversion error:', Colors.RED)} {e}")

    except Exception as e:
        print(f"  {colorize('Error:', Colors.RED)} {e}")


def batch_process(
    input_dir: Path,
    output_dir: Optional[Path] = None,
    to_format: Optional[FormatType] = None,
    pattern: str = "*",
    analyze: bool = False,
    **options,
):
    """Process multiple files in a directory"""
    print_header(f"BATCH PROCESSING: {input_dir}")

    files = list(input_dir.glob(pattern))
    if not files:
        print(
            f"{colorize('No files found matching pattern:', Colors.YELLOW)} {pattern}"
        )
        return

    print(f"Found {colorize(str(len(files)), Colors.CYAN)} files to process")

    processed = 0
    errors = 0

    for file_path in files:
        if file_path.is_file():
            try:
                output_path = None
                if output_dir and to_format:
                    # Determine output extension
                    ext_map = {
                        FormatType.JSON: ".json",
                        FormatType.TOON: ".toon",
                        FormatType.CSV: ".csv",
                        FormatType.YAML: ".yaml",
                    }
                    ext = ext_map.get(to_format, ".txt")
                    output_path = output_dir / (file_path.stem + ext)

                process_file(file_path, output_path, to_format, analyze, **options)
                processed += 1

            except Exception as e:
                print(f"  {colorize('File error:', Colors.RED)} {e}")
                errors += 1

    print(f"\n{colorize('Batch Summary:', Colors.BOLD)}")
    print(f"  Processed: {colorize(str(processed), Colors.GREEN)}")
    print(
        f"  Errors: {colorize(str(errors), Colors.RED if errors > 0 else Colors.GREEN)}"
    )


def interactive_mode():
    """Interactive exploration mode"""
    print_header("INTERACTIVE MODE")
    print("Enter content to parse (type 'help' for commands, 'quit' to exit)")

    parser = DynamicAnythingParser()

    while True:
        try:
            print(f"\n{colorize('>', Colors.CYAN)} ", end="")
            user_input = input().strip()

            if user_input.lower() in ("quit", "exit", "q"):
                print("Goodbye! 👋")
                break

            elif user_input.lower() == "help":
                print(f"""
{colorize("Available commands:", Colors.BOLD)}
  help              - Show this help
  formats           - List supported formats
  detect <content>  - Detect format only
  parse <content>   - Parse content
  file <path>       - Parse file
  analyze <content> - Analyze content in detail
  quit/exit/q       - Exit interactive mode

{colorize("Examples:", Colors.BOLD)}
  parse {{"name": "test"}}
  detect users[2]{{name,age}}: Alice,25 Bob,30
  file data.toon
  analyze config: debug: true
""")

            elif user_input.lower() == "formats":
                formats = parser.get_supported_formats()
                print(f"Supported formats: {[f.name for f in formats]}")

            elif user_input.startswith("detect "):
                content = user_input[7:]
                detection = detect_format(content)
                print_detection_result(detection)

            elif user_input.startswith("parse "):
                content = user_input[6:]
                result = parser.parse(content)
                print_parse_result(result)

                if result.data and result.is_successful:
                    print(f"\n{colorize('Parsed Data:', Colors.BOLD)}")
                    print(
                        json.dumps(
                            result.data, indent=2, ensure_ascii=False, default=str
                        )
                    )

            elif user_input.startswith("file "):
                file_path = Path(user_input[5:].strip())
                if file_path.exists():
                    process_file(file_path, analyze=True)
                else:
                    print(
                        f"{colorize('Error:', Colors.RED)} File not found: {file_path}"
                    )

            elif user_input.startswith("analyze "):
                content = user_input[8:]
                analyze_content(content)

            elif user_input:
                # Default: try to parse as content
                result = parser.parse(user_input)
                print_parse_result(result)

                if result.data and result.is_successful:
                    print(f"\n{colorize('Parsed Data:', Colors.BOLD)}")
                    print(
                        json.dumps(
                            result.data, indent=2, ensure_ascii=False, default=str
                        )
                    )

        except KeyboardInterrupt:
            print(f"\n{colorize('Interrupted. Type quit to exit.', Colors.YELLOW)}")
        except Exception as e:
            print(f"{colorize('Error:', Colors.RED)} {e}")


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="Dynamic Anything Parser - Parse any data format intelligently",
        epilog="""
Examples:
  %(prog)s data.toon                           # Parse TOON file
  %(prog)s input.json --to toon                # Convert JSON to TOON
  %(prog)s --analyze --input data.csv          # Analyze CSV structure
  %(prog)s --batch folder/ --to json           # Convert all files to JSON
  %(prog)s --interactive                       # Interactive mode
  cat data.json | %(prog)s --stdin --to toon   # Pipe conversion
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Input options
    parser.add_argument("input", nargs="?", help="Input file or directory")
    parser.add_argument("--stdin", action="store_true", help="Read from stdin")

    # Output options
    parser.add_argument("--output", "-o", help="Output file")
    parser.add_argument(
        "--to", choices=["json", "toon", "csv", "yaml"], help="Convert to format"
    )

    # Format options
    parser.add_argument(
        "--format",
        choices=["auto", "json", "toon", "csv", "yaml", "xml"],
        default="auto",
        help="Input format (auto-detect if not specified)",
    )
    parser.add_argument(
        "--delimiter", default=",", help="Delimiter for tabular formats"
    )
    parser.add_argument("--indent", type=int, default=2, help="Indentation for output")

    # Processing modes
    parser.add_argument(
        "--analyze",
        "-a",
        action="store_true",
        help="Analyze content structure and format",
    )
    parser.add_argument(
        "--detect-only", action="store_true", help="Only detect format, don't parse"
    )
    parser.add_argument(
        "--interactive", action="store_true", help="Start interactive mode"
    )
    parser.add_argument(
        "--batch", action="store_true", help="Process directory of files"
    )

    # Batch processing
    parser.add_argument(
        "--pattern", default="*", help="File pattern for batch processing"
    )
    parser.add_argument("--output-dir", help="Output directory for batch processing")

    # Parser options
    parser.add_argument(
        "--strict", action="store_true", help="Enable strict parsing (fail on errors)"
    )
    parser.add_argument(
        "--recovery",
        action="store_true",
        default=True,
        help="Enable error recovery (partial parsing)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Quiet output (errors only)"
    )

    return parser


def main():
    """Main CLI function"""
    parser = create_parser()
    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    elif args.quiet:
        logging.basicConfig(level=logging.ERROR)
    else:
        logging.basicConfig(level=logging.INFO)

    # Interactive mode
    if args.interactive:
        interactive_mode()
        return

    # Determine input source
    content = None
    filename = None

    if args.stdin:
        content = sys.stdin.read()
    elif args.input:
        input_path = Path(args.input)

        # Check if this should be batch processing
        if args.batch or input_path.is_dir():
            # Batch processing mode
            output_dir = Path(args.output_dir) if args.output_dir else None
            if output_dir:
                output_dir.mkdir(parents=True, exist_ok=True)

            to_format = FormatType[args.to.upper()] if args.to else None

            batch_process(
                input_path,
                output_dir,
                to_format,
                args.pattern,
                args.analyze,
                strict=args.strict,
                recovery=args.recovery,
                delimiter=args.delimiter,
                indent=args.indent,
            )
            return
        else:
            # Single file processing
            filename = input_path.name
            with open(input_path, "r", encoding="utf-8") as f:
                content = f.read()
    else:
        parser.error(
            "No input provided. Use --stdin, specify file, or --interactive mode"
        )

    if not content:
        parser.error("No content to parse")

    # Parse format hint
    format_hint = None
    if args.format != "auto":
        try:
            format_hint = FormatType[args.format.upper()]
        except KeyError:
            parser.error(f"Invalid format: {args.format}")

    # Format detection only
    if args.detect_only:
        detection = detect_format(content, filename)
        print_detection_result(detection)
        return

    # Content analysis
    if args.analyze:
        analyze_content(content, filename)
        return

    # Parse content
    dynamic_parser = DynamicAnythingParser()
    result = dynamic_parser.parse(
        content,
        filename=filename,
        format_hint=format_hint,
        strict=args.strict,
        recovery=args.recovery,
        delimiter=args.delimiter,
    )

    if not args.quiet:
        print_parse_result(result, show_data=False)

    # Handle conversion
    output_content = None
    if args.to and result.is_successful:
        try:
            to_format = FormatType[args.to.upper()]
            if result.format_type == to_format:
                output_content = content
                if not args.quiet:
                    print(
                        f"{colorize('Note:', Colors.YELLOW)} Source and target formats are the same"
                    )
            else:
                output_content = convert_format(
                    content,
                    result.format_type,
                    to_format,
                    filename,
                    indent=args.indent,
                    delimiter=args.delimiter,
                )
        except Exception as e:
            print(f"{colorize('Conversion error:', Colors.RED)} {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Default output: pretty-print parsed data as JSON
        if result.is_successful:
            output_content = json.dumps(
                result.data, indent=args.indent, ensure_ascii=False, default=str
            )

    # Write output
    if output_content:
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_content)
            if not args.quiet:
                print(f"{colorize('Output written to:', Colors.GREEN)} {args.output}")
        else:
            print(output_content)

    # Exit with appropriate code
    sys.exit(0 if result.is_successful else 1)


if __name__ == "__main__":
    main()
