#!/usr/bin/env python3
"""
Comprehensive Test Suite for Dynamic Anything Parser
Tests format detection, parsing, and conversion capabilities with extensive examples

Author: VArchiver Team
Version: 1.0.0
"""

import json
import sys
import time
from pathlib import Path

# Add varchiver to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from varchiver.utils.dynamic_parser import (
    DynamicAnythingParser,
    FormatType,
    FormatDetector,
    TOONParser,
    parse_anything,
    parse_file,
    detect_format,
)


class TestData:
    """Test data samples for different formats"""

    TOON_SIMPLE = """users[3]{id,name,email,active}:
  1,Alice,alice@test.com,true
  2,Bob,bob@test.com,false
  3,Carol,carol@test.com,true
config:
  app_name: VArchiver
  version: 1.0.0
  debug: false"""

    TOON_COMPLEX = """inventory[3]{item,damage,durability,rarity}:
  Sword,25,100,common
  Magic Staff,45,80,rare
  Dragon Blade,95,150,legendary
player:
  name: Hero
  level: 42
  gold: 15750
  location: Ancient Ruins
quests[2]:
  - name: Find the Ancient Artifact
    status: active
    progress: 75
    rewards[3]: gold,experience,item
  - name: Defeat the Dragon
    status: pending
    progress: 0
    prerequisites[1]: Ancient Artifact Found"""

    TOON_DELIMITERS = """products[3|]{name|price|stock|category}:
  Widget|19.99|150|Tools
  Gadget|29.99|75|Electronics
  Tool|39.99|200|Hardware
settings:
  currency: USD
  tax_rate: 0.08
  shipping: free_over_50"""

    JSON_SIMPLE = """{
  "users": [
    {"id": 1, "name": "Alice", "email": "alice@test.com", "active": true},
    {"id": 2, "name": "Bob", "email": "bob@test.com", "active": false},
    {"id": 3, "name": "Carol", "email": "carol@test.com", "active": true}
  ],
  "config": {
    "app_name": "VArchiver",
    "version": "1.0.0",
    "debug": false
  }
}"""

    JSON_COMPLEX = """{
  "inventory": [
    {"item": "Sword", "damage": 25, "durability": 100, "rarity": "common"},
    {"item": "Magic Staff", "damage": 45, "durability": 80, "rarity": "rare"},
    {"item": "Dragon Blade", "damage": 95, "durability": 150, "rarity": "legendary"}
  ],
  "player": {
    "name": "Hero",
    "level": 42,
    "gold": 15750,
    "location": "Ancient Ruins"
  },
  "quests": [
    {
      "name": "Find the Ancient Artifact",
      "status": "active",
      "progress": 75,
      "rewards": ["gold", "experience", "item"]
    },
    {
      "name": "Defeat the Dragon",
      "status": "pending",
      "progress": 0,
      "prerequisites": ["Ancient Artifact Found"]
    }
  ]
}"""

    CSV_SIMPLE = """id,name,email,active
1,Alice,alice@test.com,true
2,Bob,bob@test.com,false
3,Carol,carol@test.com,true"""

    CSV_COMPLEX = """item,damage,durability,rarity,type,value
Sword,25,100,common,weapon,250
Magic Staff,45,80,rare,weapon,800
Dragon Blade,95,150,legendary,weapon,5000
Health Potion,0,1,common,consumable,50
Mana Crystal,0,1,rare,consumable,200"""

    TSV_DATA = """item	damage	durability	rarity
Sword	25	100	common
Magic Staff	45	80	rare
Dragon Blade	95	150	legendary"""

    PIPE_DATA = """item|damage|durability|rarity
Sword|25|100|common
Magic Staff|45|80|rare
Dragon Blade|95|150|legendary"""

    YAML_DATA = """users:
  - id: 1
    name: Alice
    email: alice@test.com
    active: true
  - id: 2
    name: Bob
    email: bob@test.com
    active: false
config:
  app_name: VArchiver
  version: "1.0.0"
  debug: false"""

    XML_DATA = """<?xml version="1.0" encoding="UTF-8"?>
<data>
  <users>
    <user id="1" active="true">
      <name>Alice</name>
      <email>alice@test.com</email>
    </user>
    <user id="2" active="false">
      <name>Bob</name>
      <email>bob@test.com</email>
    </user>
  </users>
  <config>
    <app_name>VArchiver</app_name>
    <version>1.0.0</version>
    <debug>false</debug>
  </config>
</data>"""

    KEY_VALUE_DATA = """app_name=VArchiver
version=1.0.0
debug=false
port=8080
host=localhost
# This is a comment
database_url=postgres://localhost/varchiver"""

    INI_DATA = """[app]
name = VArchiver
version = 1.0.0
debug = false

[database]
host = localhost
port = 5432
name = varchiver

[server]
port = 8080
host = 0.0.0.0"""

    PROPERTIES_DATA = """app.name=VArchiver
app.version=1.0.0
app.debug=false
database.host=localhost
database.port=5432
database.name=varchiver
server.port=8080
server.host=0.0.0.0"""


def test_format_detection():
    """Test format detection accuracy"""
    print("🔍 Testing Format Detection")
    print("=" * 50)

    detector = FormatDetector()
    test_cases = [
        (TestData.TOON_SIMPLE, FormatType.TOON, "toon_simple.toon"),
        (TestData.TOON_COMPLEX, FormatType.TOON, "toon_complex.toon"),
        (TestData.JSON_SIMPLE, FormatType.JSON, "data.json"),
        (TestData.JSON_COMPLEX, FormatType.JSON, "complex.json"),
        (TestData.CSV_SIMPLE, FormatType.CSV, "users.csv"),
        (TestData.TSV_DATA, FormatType.TSV, "items.tsv"),
        (TestData.PIPE_DATA, FormatType.PIPE_DELIMITED, "items.pipe"),
        (TestData.YAML_DATA, FormatType.YAML, "config.yaml"),
        (TestData.XML_DATA, FormatType.XML, "data.xml"),
        (TestData.KEY_VALUE_DATA, FormatType.KEY_VALUE, "config.env"),
        (TestData.INI_DATA, FormatType.INI, "config.ini"),
        (TestData.PROPERTIES_DATA, FormatType.PROPERTIES, "app.properties"),
    ]

    correct = 0
    total = len(test_cases)

    for content, expected_format, filename in test_cases:
        result = detector.detect_format(content, filename)
        is_correct = result.format_type == expected_format

        status = "✓" if is_correct else "✗"
        confidence = f"{result.confidence:.2f}"

        print(f"{status} {expected_format.name:12} | {confidence} | {filename}")

        if is_correct:
            correct += 1
        else:
            print(
                f"    Expected: {expected_format.name}, Got: {result.format_type.name}"
            )
            print(f"    Indicators: {result.indicators[:3]}")

    accuracy = (correct / total) * 100
    print(f"\nAccuracy: {correct}/{total} ({accuracy:.1f}%)")

    if accuracy >= 90:
        print("🎉 Excellent detection accuracy!")
    elif accuracy >= 75:
        print("👍 Good detection accuracy")
    else:
        print("⚠️  Detection accuracy needs improvement")


def test_toon_parsing():
    """Test TOON parsing capabilities"""
    print("\n📋 Testing TOON Parsing")
    print("=" * 50)

    parser = TOONParser()
    test_cases = [
        ("Simple TOON", TestData.TOON_SIMPLE),
        ("Complex TOON", TestData.TOON_COMPLEX),
        ("Pipe Delimited TOON", TestData.TOON_DELIMITERS),
    ]

    for name, content in test_cases:
        print(f"\nTesting: {name}")
        print("-" * 30)

        start_time = time.time()
        result = parser.parse(content)
        parse_time = time.time() - start_time

        print(f"Success: {'✓' if result.is_successful else '✗'}")
        print(f"Parse time: {parse_time:.4f}s")

        if result.warnings:
            print(f"Warnings: {len(result.warnings)}")
            for warning in result.warnings[:3]:
                print(f"  - {warning}")

        if result.errors:
            print(f"Errors: {len(result.errors)}")
            for error in result.errors[:3]:
                print(f"  - {error}")

        if result.metadata:
            metadata = result.metadata
            if "structure_types" in metadata:
                print(f"Structure types: {list(metadata['structure_types'])}")
            if "array_stats" in metadata:
                arrays = metadata["array_stats"]
                print(f"Arrays: {len(arrays)} with {sum(arrays.values())} total items")

        if result.data and result.is_successful:
            print("Data structure preview:")
            if isinstance(result.data, dict):
                for key, value in list(result.data.items())[:3]:
                    value_type = type(value).__name__
                    if isinstance(value, (list, dict)):
                        size = len(value) if hasattr(value, "__len__") else "?"
                        print(f"  {key}: {value_type}({size})")
                    else:
                        preview = str(value)[:40] + (
                            "..." if len(str(value)) > 40 else ""
                        )
                        print(f"  {key}: {preview}")


def test_dynamic_parsing():
    """Test dynamic parser with all formats"""
    print("\n🚀 Testing Dynamic Parser")
    print("=" * 50)

    parser = DynamicAnythingParser()
    test_cases = [
        ("TOON Simple", TestData.TOON_SIMPLE),
        ("TOON Complex", TestData.TOON_COMPLEX),
        ("JSON Simple", TestData.JSON_SIMPLE),
        ("JSON Complex", TestData.JSON_COMPLEX),
        ("CSV Simple", TestData.CSV_SIMPLE),
        ("CSV Complex", TestData.CSV_COMPLEX),
        ("TSV Data", TestData.TSV_DATA),
        ("YAML Data", TestData.YAML_DATA),
        ("XML Data", TestData.XML_DATA),
        ("Key-Value", TestData.KEY_VALUE_DATA),
        ("INI Config", TestData.INI_DATA),
        ("Properties", TestData.PROPERTIES_DATA),
    ]

    successful = 0
    total = len(test_cases)

    for name, content in test_cases:
        print(f"\nTesting: {name}")
        print("-" * 30)

        start_time = time.time()
        result = parser.parse(content)
        parse_time = time.time() - start_time

        status = "✓" if result.is_successful else "✗"
        print(f"{status} Format: {result.format_type.name}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Parse time: {parse_time:.4f}s")

        if result.is_successful:
            successful += 1
            print("  ✓ Parsing successful")
        else:
            print(f"  ✗ Parsing failed: {result.errors}")

        if result.warnings:
            print(f"  ⚠ Warnings: {len(result.warnings)}")

    success_rate = (successful / total) * 100
    print(f"\nOverall Success Rate: {successful}/{total} ({success_rate:.1f}%)")


def test_error_recovery():
    """Test error recovery and partial parsing"""
    print("\n🛠️  Testing Error Recovery")
    print("=" * 50)

    parser = DynamicAnythingParser()

    # Test cases with intentional errors
    error_cases = [
        (
            "Malformed TOON - Missing field",
            """users[2]{id,name}:
  1,Alice
  2,Bob,Extra,Field
config:
  debug: true""",
        ),
        (
            "Malformed JSON - Trailing comma",
            """{
  "users": [
    {"id": 1, "name": "Alice"},
    {"id": 2, "name": "Bob",}
  ],
}""",
        ),
        (
            "Mixed content",
            """This is not structured data
users[1]{name}:
  Alice
Some more random text
config: debug: true""",
        ),
    ]

    for name, content in error_cases:
        print(f"\nTesting: {name}")
        print("-" * 30)

        # Test with recovery enabled
        result = parser.parse(content, recovery=True)

        print(f"Format detected: {result.format_type.name}")
        print(f"Success: {'✓' if result.is_successful else '✗'}")
        print(f"Warnings: {len(result.warnings)}")
        print(f"Errors: {len(result.errors)}")

        if result.data:
            print("Partial data recovered:")
            if isinstance(result.data, dict):
                for key in list(result.data.keys())[:3]:
                    print(f"  {key}: {type(result.data[key]).__name__}")

        # Test with strict mode
        result_strict = parser.parse(content, strict=True, recovery=False)
        print(f"Strict mode success: {'✓' if result_strict.is_successful else '✗'}")


def test_performance():
    """Test parsing performance with large data"""
    print("\n⚡ Testing Performance")
    print("=" * 50)

    parser = DynamicAnythingParser()

    # Generate large test data
    large_toon = f"""users[1000]{{id,name,email,active}}:\n"""
    for i in range(1000):
        active = "true" if i % 2 == 0 else "false"
        large_toon += f"  {i + 1},User{i + 1},user{i + 1}@test.com,{active}\n"

    large_json = {
        "users": [
            {
                "id": i + 1,
                "name": f"User{i + 1}",
                "email": f"user{i + 1}@test.com",
                "active": i % 2 == 0,
            }
            for i in range(1000)
        ]
    }
    large_json_str = json.dumps(large_json)

    test_cases = [
        ("Large TOON (1000 records)", large_toon),
        ("Large JSON (1000 records)", large_json_str),
    ]

    for name, content in test_cases:
        print(f"\nTesting: {name}")
        print(f"Content size: {len(content):,} characters")

        start_time = time.time()
        result = parser.parse(content)
        parse_time = time.time() - start_time

        print(f"Parse time: {parse_time:.4f}s")
        print(f"Success: {'✓' if result.is_successful else '✗'}")

        if result.data and isinstance(result.data, dict):
            for key, value in result.data.items():
                if isinstance(value, list):
                    print(f"Parsed {len(value)} {key}")
                    break

        # Calculate throughput
        throughput = len(content) / parse_time
        print(f"Throughput: {throughput:,.0f} chars/sec")


def test_conversion_roundtrip():
    """Test format conversion and round-trip accuracy"""
    print("\n🔄 Testing Format Conversion")
    print("=" * 50)

    parser = DynamicAnythingParser()

    # Test TOON <-> JSON conversion
    print("TOON ↔ JSON conversion:")

    # Parse TOON
    toon_result = parser.parse(TestData.TOON_SIMPLE, format_hint=FormatType.TOON)
    print(f"TOON parse: {'✓' if toon_result.is_successful else '✗'}")

    if toon_result.is_successful:
        # Convert to JSON
        json_str = json.dumps(toon_result.data, indent=2)
        print(f"JSON size: {len(json_str)} chars")

        # Parse JSON back
        json_result = parser.parse(json_str, format_hint=FormatType.JSON)
        print(f"JSON parse: {'✓' if json_result.is_successful else '✗'}")

        # Compare data structures
        if json_result.is_successful:
            data_match = toon_result.data == json_result.data
            print(f"Data integrity: {'✓' if data_match else '✗'}")

    print("\nJSON → TOON conversion:")

    # Parse JSON
    json_result = parser.parse(TestData.JSON_SIMPLE, format_hint=FormatType.JSON)
    print(f"JSON parse: {'✓' if json_result.is_successful else '✗'}")

    if json_result.is_successful:
        # Would need TOON encoder for full conversion test
        print("TOON encoding would require format converter integration")


def benchmark_detection():
    """Benchmark format detection speed"""
    print("\n📊 Benchmarking Detection Speed")
    print("=" * 50)

    detector = FormatDetector()
    test_data = [
        TestData.TOON_SIMPLE,
        TestData.JSON_SIMPLE,
        TestData.CSV_SIMPLE,
        TestData.YAML_DATA,
        TestData.XML_DATA,
    ]

    iterations = 100

    for i, content in enumerate(test_data):
        format_name = ["TOON", "JSON", "CSV", "YAML", "XML"][i]

        start_time = time.time()
        for _ in range(iterations):
            detector.detect_format(content)
        total_time = time.time() - start_time

        avg_time = (total_time / iterations) * 1000  # milliseconds
        print(f"{format_name:5}: {avg_time:.2f}ms avg ({iterations} iterations)")


def run_all_tests():
    """Run all test suites"""
    print("🧪 Dynamic Anything Parser - Comprehensive Test Suite")
    print("=" * 60)
    print(f"Python version: {sys.version}")
    print(f"Test started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    start_time = time.time()

    try:
        test_format_detection()
        test_toon_parsing()
        test_dynamic_parsing()
        test_error_recovery()
        test_performance()
        test_conversion_roundtrip()
        benchmark_detection()

    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False

    total_time = time.time() - start_time
    print(f"\n✅ All tests completed successfully!")
    print(f"Total test time: {total_time:.2f}s")
    print("=" * 60)
    return True


def demo_interactive_features():
    """Demonstrate interactive parser features"""
    print("\n🎮 Interactive Demo")
    print("=" * 50)

    parser = DynamicAnythingParser()

    demo_inputs = [
        "users[2]{name,age}: Alice,25 Bob,30",
        '{"name": "test", "value": 42}',
        "name,age\nAlice,25\nBob,30",
        "config: debug: true",
    ]

    for i, demo_input in enumerate(demo_inputs, 1):
        print(f"\nDemo {i}: {demo_input[:30]}...")

        result = parser.parse(demo_input)
        print(
            f"  Detected: {result.format_type.name} (confidence: {result.confidence:.2f})"
        )

        if result.is_successful:
            print("  ✓ Parsed successfully")
            if isinstance(result.data, dict) and len(result.data) <= 3:
                print("  Data:", result.data)
        else:
            print(
                "  ✗ Parse failed:",
                result.errors[0] if result.errors else "Unknown error",
            )


if __name__ == "__main__":
    # Check if specific test requested
    if len(sys.argv) > 1:
        test_name = sys.argv[1].lower()
        if test_name == "detection":
            test_format_detection()
        elif test_name == "toon":
            test_toon_parsing()
        elif test_name == "dynamic":
            test_dynamic_parsing()
        elif test_name == "recovery":
            test_error_recovery()
        elif test_name == "performance":
            test_performance()
        elif test_name == "conversion":
            test_conversion_roundtrip()
        elif test_name == "benchmark":
            benchmark_detection()
        elif test_name == "demo":
            demo_interactive_features()
        else:
            print(f"Unknown test: {test_name}")
            print(
                "Available tests: detection, toon, dynamic, recovery, performance, conversion, benchmark, demo"
            )
    else:
        # Run all tests
        success = run_all_tests()
        demo_interactive_features()
        sys.exit(0 if success else 1)
