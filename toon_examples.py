#!/usr/bin/env python3
"""
TOON Format Examples and Demonstrations

This file provides comprehensive examples of TOON (Token-Optimized Object Notation)
format, showing how it compares to JSON and demonstrating its token efficiency benefits
for LLM applications.

TOON is designed to reduce token usage by 30-60% compared to JSON while maintaining
readability and structure. It's particularly effective for tabular data and uniform
object arrays.
"""

import json
import sys
from pathlib import Path

# Add varchiver to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from varchiver.utils.format_converter import FormatConverter
except ImportError:
    print("Note: FormatConverter not available. Showing static examples.")
    FormatConverter = None


def show_basic_example():
    """Show basic TOON format example"""
    print("🔧 Basic TOON Format Example")
    print("=" * 50)

    # JSON representation
    json_data = {
        "users": [
            {"id": 1, "name": "Alice", "role": "admin"},
            {"id": 2, "name": "Bob", "role": "user"},
        ]
    }

    json_str = json.dumps(json_data, indent=2)
    print("JSON format:")
    print(json_str)
    print(f"Size: {len(json_str)} characters")

    # TOON representation
    toon_str = """users[2]{id,name,role}:
  1,Alice,admin
  2,Bob,user"""

    print("\nTOON format:")
    print(toon_str)
    print(f"Size: {len(toon_str)} characters")

    reduction = (len(json_str) - len(toon_str)) / len(json_str) * 100
    print(f"Size reduction: {reduction:.1f}%")


def show_varchiver_tech_items():
    """Show TOON format for varchiver tech items"""
    print("\n\n⚙️ VArchiver Tech Items in TOON Format")
    print("=" * 50)

    # Sample tech item data
    tech_items = {
        "items": [
            {
                "id": "resonator_t1",
                "name": "Basic Resonator",
                "tech_tier": "Tier 1",
                "category": "Modular",
                "type": "tech_module",
                "weight_kg": 0.8,
                "stack_size": 5,
            },
            {
                "id": "magitek_core_t2",
                "name": "Advanced Magitek Core",
                "tech_tier": "Tier 2",
                "category": "Modular",
                "type": "tech_module",
                "weight_kg": 2.1,
                "stack_size": 3,
            },
            {
                "id": "crystal_t3",
                "name": "Prismatic Crystal",
                "tech_tier": "Tier 3",
                "category": "Energy",
                "type": "power_source",
                "weight_kg": 0.3,
                "stack_size": 10,
            },
        ],
        "metadata": {
            "version": "1.0",
            "total_items": 3,
            "last_updated": "2025-01-02T10:30:00Z",
        },
    }

    print("TOON representation of tech items:")

    toon_output = """items[3]{id,name,tech_tier,category,type,weight_kg,stack_size}:
  resonator_t1,Basic Resonator,Tier 1,Modular,tech_module,0.8,5
  magitek_core_t2,Advanced Magitek Core,Tier 2,Modular,tech_module,2.1,3
  crystal_t3,Prismatic Crystal,Tier 3,Energy,power_source,0.3,10
metadata:
  version: 1.0
  total_items: 3
  last_updated: 2025-01-02T10:30:00Z"""

    print(toon_output)

    json_size = len(json.dumps(tech_items, indent=2))
    toon_size = len(toon_output)
    print(f"\nJSON size: {json_size} characters")
    print(f"TOON size: {toon_size} characters")
    print(f"Reduction: {(json_size - toon_size) / json_size * 100:.1f}%")


def show_delimiter_options():
    """Show different delimiter options in TOON"""
    print("\n\n📊 TOON Delimiter Options")
    print("=" * 50)

    data = [
        {"product": "Widget", "price": 19.99, "stock": 150},
        {"product": "Gadget", "price": 29.99, "stock": 75},
        {"product": "Tool", "price": 39.99, "stock": 200},
    ]

    print("Comma delimiter (default):")
    comma_toon = """[3]{product,price,stock}:
  Widget,19.99,150
  Gadget,29.99,75
  Tool,39.99,200"""
    print(comma_toon)

    print("\nTab delimiter (often more token-efficient):")
    tab_toon = """[3\t]{product\tprice\tstock}:
  Widget\t19.99\t150
  Gadget\t29.99\t75
  Tool\t39.99\t200"""
    print(tab_toon)

    print("\nPipe delimiter (visual clarity):")
    pipe_toon = """[3|]{product|price|stock}:
  Widget|19.99|150
  Gadget|29.99|75
  Tool|39.99|200"""
    print(pipe_toon)


def show_complex_structures():
    """Show TOON handling of complex nested structures"""
    print("\n\n🌳 Complex Nested Structures")
    print("=" * 50)

    print("When data doesn't fit tabular format, TOON uses list format:")

    complex_toon = """projects[2]:
  - name: VArchiver
    version: 1.0.0
    features[4]: archive,extract,browse,convert
    contributors[2]{name,role}:
      Alice,Lead Developer
      Bob,UI Designer
  - name: DataProcessor
    version: 2.1.5
    features[2]: process,analyze
    contributors[1]{name,role}:
      Charlie,Backend Developer"""

    print(complex_toon)

    print("\nKey features:")
    print("• Arrays of uniform objects use tabular format: contributors[2]{name,role}")
    print(
        "• Simple arrays use inline format: features[4]: archive,extract,browse,convert"
    )
    print("• Mixed content uses list format: projects[2]: with '- ' prefixes")
    print("• Nested structures maintain clear indentation hierarchy")


def show_token_efficiency_comparison():
    """Compare token efficiency across different data types"""
    print("\n\n🎯 Token Efficiency Comparison")
    print("=" * 50)

    examples = [
        {
            "name": "User Database",
            "json": """{
  "users": [
    {"id": 1, "name": "Alice", "email": "alice@test.com", "active": true},
    {"id": 2, "name": "Bob", "email": "bob@test.com", "active": false},
    {"id": 3, "name": "Carol", "email": "carol@test.com", "active": true}
  ]
}""",
            "toon": """users[3]{id,name,email,active}:
  1,Alice,alice@test.com,true
  2,Bob,bob@test.com,false
  3,Carol,carol@test.com,true""",
        },
        {
            "name": "Configuration Settings",
            "json": """{
  "app": {
    "name": "VArchiver",
    "version": "1.0.0",
    "debug": false
  },
  "database": {
    "host": "localhost",
    "port": 5432,
    "ssl": true
  }
}""",
            "toon": """app:
  name: VArchiver
  version: 1.0.0
  debug: false
database:
  host: localhost
  port: 5432
  ssl: true""",
        },
    ]

    for example in examples:
        print(f"\n{example['name']}:")
        print(f"JSON: {len(example['json'])} chars")
        print(f"TOON: {len(example['toon'])} chars")
        reduction = (
            (len(example["json"]) - len(example["toon"])) / len(example["json"]) * 100
        )
        print(f"Reduction: {reduction:.1f}%")


def show_llm_usage_examples():
    """Show examples of using TOON with LLMs"""
    print("\n\n🤖 Using TOON with LLMs")
    print("=" * 50)

    print("TOON is designed for LLM input/output. Here's how to use it:")

    print("\n1. Sending TOON to LLMs (Input):")
    print("Wrap in code blocks and let the model parse naturally:")

    prompt_example = """```toon
users[3]{id,name,role,lastLogin}:
  1,Alice,admin,2025-01-15T10:30:00Z
  2,Bob,user,2025-01-14T15:22:00Z
  3,Charlie,user,2025-01-13T09:45:00Z
```

Task: Return only admin users as TOON format."""

    print(prompt_example)

    print("\n2. Getting TOON from LLMs (Output):")
    print("Be explicit about the format requirements:")

    instruction_example = """Generate user data as TOON format:
- Use 2-space indentation
- Show array length in brackets: users[N]
- Tabular format with headers: {id,name,role}
- Output only the TOON code block"""

    print(instruction_example)

    print("\n3. Benefits for LLMs:")
    print("• Fewer tokens = lower API costs")
    print("• Clear structure = fewer parsing errors")
    print("• Length markers help models track counts")
    print("• Field headers reduce key repetition mistakes")


def interactive_demo():
    """Run interactive demonstration if converter is available"""
    if FormatConverter is None:
        print("\n⚠️ Interactive demo requires FormatConverter")
        return

    print("\n\n🚀 Interactive Demo")
    print("=" * 50)

    converter = FormatConverter()

    # Sample data for live conversion
    sample_data = {
        "inventory": [
            {"item": "Sword", "damage": 25, "durability": 100, "rarity": "common"},
            {"item": "Magic Staff", "damage": 45, "durability": 80, "rarity": "rare"},
            {
                "item": "Dragon Blade",
                "damage": 95,
                "durability": 150,
                "rarity": "legendary",
            },
        ],
        "player": {
            "name": "Hero",
            "level": 42,
            "gold": 15750,
            "location": "Ancient Ruins",
        },
    }

    print("Live conversion example:")

    # Convert to TOON with different options
    toon_comma = converter.json_to_toon(sample_data, delimiter=",")
    toon_tab = converter.json_to_toon(sample_data, delimiter="\t", length_marker=True)

    print("\nWith comma delimiter:")
    print(toon_comma)

    print("\nWith tab delimiter and length markers:")
    print(toon_tab)

    # Show stats
    json_str = json.dumps(sample_data, indent=2)
    stats = converter.estimate_token_savings(json_str, "json")

    print(f"\nEfficiency stats:")
    print(f"JSON tokens: {stats['json_tokens']}")
    print(f"TOON tokens: {stats['toon_tokens']}")
    print(f"Token savings: {stats['savings_percent']}%")
    print(f"Size reduction: {stats['size_reduction']}%")


def main():
    """Run all demonstrations"""
    print("🎨 TOON Format Examples & Demonstrations")
    print("=" * 60)
    print("TOON (Token-Optimized Object Notation) reduces LLM token usage")
    print("while maintaining readability and structure.")
    print("=" * 60)

    show_basic_example()
    show_varchiver_tech_items()
    show_delimiter_options()
    show_complex_structures()
    show_token_efficiency_comparison()
    show_llm_usage_examples()
    interactive_demo()

    print("\n\n✨ Summary")
    print("=" * 50)
    print("TOON format provides:")
    print("• 30-60% token reduction vs JSON")
    print("• Tabular arrays for uniform data")
    print("• Multiple delimiter options")
    print("• LLM-friendly structure validation")
    print("• Indentation-based hierarchy")
    print("• Seamless JSON interoperability")
    print(
        "\nPerfect for: API responses, data exports, LLM prompts, configuration files"
    )
    print("Get started: python format_convert.py --help")


if __name__ == "__main__":
    main()
