# Format Converter - TOON, JSON, CSV

A powerful data format converter for VArchiver that enables seamless conversion between **TOON** (Token-Optimized Object Notation), **JSON**, and **CSV** formats. Designed to reduce LLM token usage by 30-60% while maintaining readability and structure.

## What is TOON?

TOON (Token-Optimized Object Notation) is a data format specifically designed for LLM applications that provides:

- **🔥 30-60% fewer tokens** compared to JSON
- **📊 Tabular arrays** - declare keys once, stream data as rows
- **🎯 LLM-friendly** - explicit lengths and fields enable validation
- **⚡ Multiple delimiters** - comma, tab, or pipe for optimal efficiency
- **🌳 Indentation-based** structure like YAML

### Quick Example

**JSON (162 characters, ~20 tokens):**
```json
{
  "users": [
    {"id": 1, "name": "Alice", "role": "admin"},
    {"id": 2, "name": "Bob", "role": "user"}
  ]
}
```

**TOON (52 characters, ~8 tokens - 67% reduction):**
```toon
users[2]{id,name,role}:
  1,Alice,admin
  2,Bob,user
```

## Features

### Supported Conversions
- ✅ JSON ↔ TOON
- ✅ JSON ↔ CSV  
- ✅ CSV ↔ TOON
- ✅ Round-trip conversions
- ✅ File and pipe operations
- ✅ Batch processing

### TOON Format Features
- **Tabular Arrays**: `items[3]{id,name,price}:` - efficient for uniform data
- **Inline Arrays**: `tags[4]: web,api,json,toon` - for simple lists
- **List Format**: Mixed/complex arrays with `- ` prefixes
- **Multiple Delimiters**: Comma (`,`), Tab (`\t`), Pipe (`|`)
- **Length Markers**: Optional `#` prefix (`items[#3]`) for LLM validation
- **Smart Quoting**: Only quotes when necessary to maximize efficiency

## Installation & Usage

### Python API

```python
from varchiver.utils.format_converter import FormatConverter

converter = FormatConverter()

# JSON to TOON
toon_data = converter.json_to_toon(json_data, delimiter="\t", length_marker=True)

# TOON to JSON  
json_data = converter.toon_to_json(toon_data)

# CSV conversions
csv_data = converter.json_to_csv(json_data)
json_data = converter.csv_to_json(csv_data)

# Token efficiency estimation
stats = converter.estimate_token_savings(json_data, "json")
print(f"Token savings: {stats['savings_percent']}%")
```

### Command Line Interface

```bash
# Convert files (auto-detects formats)
python format_convert.py data.json -o output.toon
python format_convert.py data.toon -o output.json

# Pipe operations
cat data.json | python format_convert.py --encode
echo '{"users":[{"id":1,"name":"Alice"}]}' | python format_convert.py --stats

# Specify formats explicitly
python format_convert.py data.csv --to toon --delimiter "|"

# Show token savings
python format_convert.py input.json --stats --delimiter tab
```

### GUI Widget

The format converter includes a PyQt6 widget for interactive conversion:

```python
from varchiver.widgets.format_converter_widget import FormatConverterWidget

widget = FormatConverterWidget()
widget.show()
```

**GUI Features:**
- Real-time conversion preview
- Syntax highlighting for JSON and TOON
- Token efficiency statistics
- Multiple delimiter options
- File load/save operations
- Error handling and validation

## TOON Format Specification

### Objects
```toon
user:
  id: 123
  name: Alice
  active: true
```

### Arrays - Tabular Format
For uniform objects with same primitive fields:
```toon
users[3]{id,name,role}:
  1,Alice,admin
  2,Bob,user  
  3,Carol,moderator
```

### Arrays - Inline Format
For simple lists:
```toon
tags[4]: web,api,json,toon
numbers[3]: 1,2,3
```

### Arrays - List Format  
For mixed/complex content:
```toon
items[2]:
  - id: 1
    name: Widget
    metadata:
      weight: 1.5
  - id: 2
    name: Gadget
```

### Delimiter Options

**Comma (default):**
```toon
data[2]{id,name}:
  1,Alice
  2,Bob
```

**Tab (often more efficient):**
```toon
data[2	]{id	name}:
  1	Alice
  2	Bob
```

**Pipe (visual clarity):**
```toon
data[2|]{id|name}:
  1|Alice
  2|Bob
```

## Performance & Efficiency

### Token Savings by Data Type

| Data Type | JSON Tokens | TOON Tokens | Savings |
|-----------|-------------|-------------|---------|
| Tabular Data | 150 | 65 | 57% |
| Configuration | 85 | 55 | 35% |
| User Lists | 120 | 45 | 62% |
| Tech Items | 200 | 90 | 55% |

### Best Use Cases for TOON

✅ **Excellent for:**
- Uniform arrays of objects (database exports)
- API responses with tabular data
- LLM prompts requiring structured data
- Configuration files
- Data exports for analysis

⚠️ **Moderate for:**
- Mixed/irregular object structures
- Deep nesting (>3 levels)
- Single objects without arrays

❌ **Not optimal for:**
- Heavily nested trees
- Schema with frequent variations
- Binary data or large text blobs

## Examples

### VArchiver Tech Items

```toon
items[3]{id,name,tech_tier,category,weight_kg,stack_size}:
  resonator_t1,Basic Resonator,Tier 1,Modular,0.8,5
  magitek_core_t2,Advanced Magitek Core,Tier 2,Modular,2.1,3
  crystal_t3,Prismatic Crystal,Tier 3,Energy,0.3,10
metadata:
  version: 1.0
  total_items: 3
  last_updated: 2025-01-02T10:30:00Z
```

### Inventory System
```toon
inventory[4]{sku,product,price,stock,active}:
  A001,Widget,19.99,150,true
  A002,Gadget,29.99,75,true  
  A003,Tool,39.99,200,false
  A004,Device,49.99,25,true
stats:
  total_value: 2847.25
  active_items: 3
  low_stock_threshold: 50
```

## Using TOON with LLMs

### Input to LLMs
Wrap TOON data in code blocks:

````markdown
Here's user data in TOON format:
```toon
users[3]{id,name,role,lastLogin}:
  1,Alice,admin,2025-01-15T10:30:00Z
  2,Bob,user,2025-01-14T15:22:00Z  
  3,Charlie,user,2025-01-13T09:45:00Z
```

Task: Return only admin users in the same TOON format.
````

### Output from LLMs
Be explicit about format requirements:

> Generate user data as TOON format:
> - Use tabular format with headers: {id,name,role}
> - Include array length: users[N]
> - Use 2-space indentation
> - Output only the TOON code block

### Benefits for LLMs
- **Fewer tokens** = lower API costs
- **Structure validation** = fewer parsing errors
- **Length markers** = helps models track counts
- **Field headers** = reduces key repetition mistakes

## Testing & Development

Run the comprehensive test suite:
```bash
python test_format_converter.py
```

See format examples and demonstrations:
```bash
python toon_examples.py
```

## Integration

### Adding to VArchiver Modes

The format converter can be integrated into VArchiver's mode system:

```python
# In main widget
if mode == "Format Converter":
    from varchiver.widgets.format_converter_widget import FormatConverterWidget
    widget = FormatConverterWidget()
    return widget
```

### Batch Operations

Process multiple files:
```bash
# Convert all JSON files to TOON
for file in *.json; do
    python format_convert.py "$file" -o "${file%.json}.toon"
done
```

## Technical Details

### Dependencies
- `json` (standard library)
- `csv` (standard library) 
- `re` (standard library)
- `pathlib` (standard library)
- `PyQt6` (for GUI widget only)

### Architecture
- `TOONEncoder` - Converts Python data to TOON format
- `TOONDecoder` - Parses TOON format to Python data
- `FormatConverter` - High-level conversion interface
- `FormatConverterWidget` - GUI component with syntax highlighting

### Error Handling
- JSON validation before conversion
- TOON syntax validation with detailed error messages
- Graceful handling of malformed data
- Round-trip conversion verification in tests

## Contributing

The format converter is part of the VArchiver project. To contribute:

1. Test your changes with `python test_format_converter.py`
2. Add examples to `toon_examples.py` for new features
3. Update this README with any new functionality
4. Ensure GUI widget works with PyQt6

## License

Same as VArchiver project. See main project LICENSE file.

---

**Ready to reduce your LLM token costs by 30-60%?**

Start with: `python format_convert.py --help`

Or try the interactive examples: `python toon_examples.py`
