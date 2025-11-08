#!/usr/bin/env python3
"""
Test script for the TOON/JSON/CSV format converter

This script demonstrates the format converter functionality and provides
comprehensive testing of all conversion combinations.
"""

import json
import tempfile
import os
from pathlib import Path

# Add the varchiver module to path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from varchiver.utils.format_converter import FormatConverter


def test_sample_data():
    """Test with sample tech items data"""
    print("🔧 Testing with Sample Tech Items Data")
    print("=" * 50)

    # Sample data similar to varchiver's tech items
    sample_data = {
        "items": [
            {
                "id": "resonator_t1",
                "name": "Basic Resonator",
                "description": "A simple harmonic resonator for basic frequency matching",
                "tech_tier": "Tier 1",
                "energy_type": "Resonant",
                "category": "Modular",
                "subcategory": "Resonators",
                "type": "tech_module",
                "tech_tags": ["resonant", "harmonic", "basic"],
                "effects": ["Frequency matching"],
                "inventory_properties": {
                    "stack_size": 1,
                    "max_stack_size": 5,
                    "slot_size": [1, 1],
                    "weight_kg": 0.8,
                    "volume_l": 0.5,
                },
            },
            {
                "id": "magitek_core_t2",
                "name": "Advanced Magitek Core",
                "description": "A sophisticated core that integrates magical and technological energies",
                "tech_tier": "Tier 2",
                "energy_type": "Magitek",
                "category": "Modular",
                "subcategory": "Cores",
                "type": "tech_module",
                "tech_tags": ["magitek", "advanced", "energy"],
                "effects": ["Energy integration", "Magical amplification"],
                "inventory_properties": {
                    "stack_size": 1,
                    "max_stack_size": 3,
                    "slot_size": [2, 2],
                    "weight_kg": 2.1,
                    "volume_l": 1.8,
                },
            },
        ],
        "metadata": {"version": "1.0", "created_by": "varchiver", "item_count": 2},
    }

    converter = FormatConverter()

    # Test JSON to TOON conversion
    print("\n📝 JSON to TOON Conversion:")
    print("-" * 30)

    json_input = json.dumps(sample_data, indent=2)
    print(f"JSON input size: {len(json_input)} characters")

    # Test different TOON options
    toon_options = [
        {"delimiter": ",", "length_marker": False},
        {"delimiter": "\t", "length_marker": True},
        {"delimiter": "|", "length_marker": True},
    ]

    for i, options in enumerate(toon_options, 1):
        print(f"\nTOON Option {i}: {options}")
        toon_output = converter.json_to_toon(sample_data, **options)
        print(f"TOON output size: {len(toon_output)} characters")

        # Show first few lines
        toon_lines = toon_output.split("\n")[:10]
        for line in toon_lines:
            print(f"  {line}")
        if len(toon_output.split("\n")) > 10:
            print(f"  ... ({len(toon_output.split('\n')) - 10} more lines)")

        # Test round-trip conversion
        try:
            converted_back = converter.toon_to_json(toon_output)
            original_data = json.loads(converted_back)
            if original_data == sample_data:
                print("  ✅ Round-trip conversion successful!")
            else:
                print("  ❌ Round-trip conversion failed!")
        except Exception as e:
            print(f"  ❌ Round-trip error: {e}")

        # Calculate savings
        savings = calculate_savings(json_input, toon_output)
        print(f"  📊 Size reduction: {savings['size_reduction']:.1f}%")
        print(f"  🎯 Token savings (est.): {savings['token_savings']:.1f}%")


def test_tabular_data():
    """Test with tabular data (best case for TOON)"""
    print("\n\n📊 Testing with Tabular Data")
    print("=" * 50)

    # Create tabular data that should compress well with TOON
    tabular_data = {
        "users": [
            {"id": 1, "name": "Alice", "role": "admin", "active": True, "score": 95.5},
            {"id": 2, "name": "Bob", "role": "user", "active": True, "score": 87.2},
            {
                "id": 3,
                "name": "Charlie",
                "role": "user",
                "active": False,
                "score": 92.1,
            },
            {
                "id": 4,
                "name": "Diana",
                "role": "moderator",
                "active": True,
                "score": 98.7,
            },
            {"id": 5, "name": "Eve", "role": "user", "active": True, "score": 84.3},
        ],
        "stats": {"total_users": 5, "active_users": 4, "average_score": 91.56},
    }

    converter = FormatConverter()

    json_str = json.dumps(tabular_data, indent=2)
    print(f"JSON input: {len(json_str)} characters")

    # Test TOON conversion with comma delimiter
    toon_output = converter.json_to_toon(tabular_data, delimiter=",")
    print(f"\nTOON output (comma delimiter):")
    print(toon_output)
    print(f"\nTOON size: {len(toon_output)} characters")

    # Test TOON conversion with tab delimiter
    toon_tab_output = converter.json_to_toon(tabular_data, delimiter="\t")
    print(f"\nTOON output (tab delimiter):")
    print(toon_tab_output)
    print(f"TOON (tab) size: {len(toon_tab_output)} characters")

    # Calculate and display savings
    savings_comma = calculate_savings(json_str, toon_output)
    savings_tab = calculate_savings(json_str, toon_tab_output)

    print(f"\n📊 Efficiency Comparison:")
    print(
        f"Comma delimiter - Size: {savings_comma['size_reduction']:.1f}%, Tokens: {savings_comma['token_savings']:.1f}%"
    )
    print(
        f"Tab delimiter   - Size: {savings_tab['size_reduction']:.1f}%, Tokens: {savings_tab['token_savings']:.1f}%"
    )


def test_csv_conversions():
    """Test CSV conversions"""
    print("\n\n📄 Testing CSV Conversions")
    print("=" * 50)

    converter = FormatConverter()

    # Create simple tabular data
    data = {
        "products": [
            {"sku": "A001", "name": "Widget", "price": 19.99, "stock": 150},
            {"sku": "A002", "name": "Gadget", "price": 29.99, "stock": 75},
            {"sku": "A003", "name": "Doohickey", "price": 9.99, "stock": 200},
        ]
    }

    # JSON to CSV
    print("JSON to CSV:")
    csv_output = converter.json_to_csv(data)
    print(csv_output)

    # CSV back to JSON
    print("\nCSV back to JSON:")
    json_from_csv = converter.csv_to_json(csv_output)
    print(json_from_csv)

    # JSON to TOON
    print("\nJSON to TOON:")
    toon_from_json = converter.json_to_toon(data)
    print(toon_from_json)

    # CSV to TOON (via JSON)
    print("\nCSV to TOON:")
    toon_from_csv = converter.csv_to_toon(csv_output)
    print(toon_from_csv)


def test_file_operations():
    """Test file I/O operations"""
    print("\n\n📁 Testing File Operations")
    print("=" * 50)

    converter = FormatConverter()

    # Create test data
    test_data = {
        "config": {"app_name": "VArchiver", "version": "1.0.0", "debug": True},
        "features": ["archive", "extract", "browse", "convert"],
        "settings": [
            {"key": "theme", "value": "dark", "type": "string"},
            {"key": "auto_extract", "value": True, "type": "boolean"},
            {"key": "compression_level", "value": 5, "type": "integer"},
        ],
    }

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Save as JSON
        json_file = temp_path / "test.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f, indent=2)

        # Convert JSON file to TOON file
        toon_file = temp_path / "test.toon"
        success = converter.convert_file(str(json_file), str(toon_file))
        print(
            f"JSON -> TOON file conversion: {'✅ Success' if success else '❌ Failed'}"
        )

        if success:
            with open(toon_file, "r", encoding="utf-8") as f:
                toon_content = f.read()
            print("TOON file content:")
            print(toon_content[:300] + ("..." if len(toon_content) > 300 else ""))

        # Convert TOON file back to JSON file
        json_file2 = temp_path / "test_converted.json"
        success2 = converter.convert_file(str(toon_file), str(json_file2))
        print(
            f"\nTOON -> JSON file conversion: {'✅ Success' if success2 else '❌ Failed'}"
        )

        if success2:
            with open(json_file2, "r", encoding="utf-8") as f:
                converted_data = json.load(f)

            if converted_data == test_data:
                print("✅ Round-trip file conversion successful!")
            else:
                print("❌ Round-trip file conversion data mismatch!")


def test_error_handling():
    """Test error handling"""
    print("\n\n🚨 Testing Error Handling")
    print("=" * 50)

    converter = FormatConverter()

    # Test invalid JSON
    print("Testing invalid JSON:")
    try:
        result = converter.json_to_toon('{"invalid": json}')
        print("❌ Should have failed!")
    except Exception as e:
        print(f"✅ Correctly caught error: {type(e).__name__}")

    # Test invalid TOON
    print("\nTesting invalid TOON:")
    try:
        result = converter.toon_to_json("invalid[toon format")
        print("❌ Should have failed!")
    except Exception as e:
        print(f"✅ Correctly caught error: {type(e).__name__}")

    # Test empty data
    print("\nTesting empty data:")
    try:
        result = converter.json_to_toon("{}")
        print(f"✅ Empty object handled: '{result}'")
    except Exception as e:
        print(f"❌ Failed on empty object: {e}")


def calculate_savings(original: str, converted: str) -> dict:
    """Calculate size and estimated token savings"""
    original_size = len(original)
    converted_size = len(converted)

    size_reduction = (
        ((original_size - converted_size) / original_size * 100)
        if original_size > 0
        else 0
    )

    # Simple token estimation (rough approximation)
    original_tokens = (
        len(original.split())
        + original.count(",")
        + original.count("{")
        + original.count("}")
    )
    converted_tokens = (
        len(converted.split()) + converted.count(",") + converted.count(":")
    )

    token_savings = (
        ((original_tokens - converted_tokens) / original_tokens * 100)
        if original_tokens > 0
        else 0
    )

    return {
        "size_reduction": size_reduction,
        "token_savings": token_savings,
        "original_size": original_size,
        "converted_size": converted_size,
        "original_tokens": original_tokens,
        "converted_tokens": converted_tokens,
    }


def main():
    """Run all tests"""
    print("🧪 TOON Format Converter Test Suite")
    print("=" * 60)
    print("Testing conversion between TOON, JSON, and CSV formats")
    print("TOON (Token-Optimized Object Notation) is designed to reduce")
    print("token usage for LLM applications while maintaining readability.")
    print("=" * 60)

    try:
        # Run all test functions
        test_sample_data()
        test_tabular_data()
        test_csv_conversions()
        test_file_operations()
        test_error_handling()

        print("\n\n🎉 All Tests Completed!")
        print("=" * 60)
        print("The format converter supports:")
        print("• JSON ↔ TOON conversion with customizable options")
        print("• CSV ↔ JSON ↔ TOON conversion chains")
        print("• File I/O operations with auto-format detection")
        print("• Token efficiency estimation and reporting")
        print("• Robust error handling and validation")
        print("")
        print("TOON format features:")
        print("• 30-60% token reduction compared to JSON")
        print("• Tabular arrays for efficient data representation")
        print("• Multiple delimiter options (comma, tab, pipe)")
        print("• Length markers for LLM validation")
        print("• Indentation-based structure like YAML")

    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
