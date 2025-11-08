# Dynamic Anything Parser - GUI User Guide

## Overview

The Dynamic Anything Parser GUI provides a powerful, user-friendly interface for parsing, analyzing, and converting various data formats. Built for VArchiver, it supports automatic format detection, real-time parsing, and seamless format conversion with visual feedback.

## Getting Started

### Launching the GUI

**Option 1: Standalone Launch**
```bash
cd varchiver
python launch_dynamic_parser.py
```

**Option 2: From VArchiver Main Interface**
- Menu: `Tools > Dynamic Parser > Launch Parser` (Ctrl+Shift+P)
- Toolbar: Click the "🚀 Parse" button
- Context Menu: Right-click any file → "Parse with Dynamic Parser"

**Option 3: With File Pre-loaded**
```bash
python launch_dynamic_parser.py --file data.toon
```

**Option 4: Demo Mode**
```bash
python launch_dynamic_parser.py --demo
```

### First Launch

On first launch, you'll see a welcome message explaining the key features:
- 🎯 Automatic format detection for 10+ formats
- 📊 Interactive data visualization  
- 🔄 Format conversion tools
- 📁 Drag & drop file loading
- ⚡ High performance parsing

## Interface Overview

### Main Window Layout

```
┌─────────────────────────────────────────────────────────────┐
│ VArchiver - Dynamic Anything Parser                    📁 Load File │
├─────────────────────────────────────────────────────────────┤
│ ┌─ Input Content ──────┐ ┌─ Results ─────────────────────┐   │
│ │ File: data.toon      │ │ 🔍 Format Detection            │   │
│ │ ┌─────────────────┐  │ │ 📊 Data Preview               │   │
│ │ │ Content area    │  │ │ 🔄 Format Conversion          │   │
│ │ │ (text editor)   │  │ │                               │   │
│ │ └─────────────────┘  │ │ [Detection Results]           │   │
│ │                      │ │                               │   │
│ │ ┌─ Parser Settings ─┐│ │                               │   │
│ │ │ Format: Auto      ││ │                               │   │
│ │ │ ☑ Strict parsing  ││ │                               │   │
│ │ │ ☑ Error recovery  ││ │                               │   │
│ │ │ Delimiter: Comma  ││ │                               │   │
│ │ └──────────────────┘│ │                               │   │
│ │                      │ │                               │   │
│ │ 🔍 🚀 🔄            │ │                               │   │
│ │ [Progress Bar]       │ │                               │   │
│ └──────────────────────┘ └───────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│ Status: Ready                                               │
└─────────────────────────────────────────────────────────────┘
```

### Left Panel - Input & Controls

**File Information Bar**
- Shows loaded file name and size
- Indicates input source (file, manual input, drag & drop)
- Color-coded status: Green (file), Orange (manual), Gray (empty)

**Content Text Area**
- Large text editor for viewing/editing content
- Syntax highlighting for recognized formats
- Supports copy/paste and manual editing
- Placeholder text shows supported formats

**Parser Settings**
- **Format Hint**: Auto-detect or specify format
- **Strict Parsing**: Fail on structural errors vs. attempt recovery
- **Error Recovery**: Enable partial parsing when errors occur
- **Delimiter**: Choose delimiter for tabular formats

**Action Buttons**
- **🔍 Detect Format**: Analyze content and determine format
- **🚀 Parse Content**: Parse content into structured data
- **🔄 Convert Format**: Open conversion interface

### Right Panel - Results

**Format Detection Tab** (🔍)
- Shows detected format with confidence level
- Color-coded confidence meter (Red: Low, Orange: Medium, Green: High)
- Lists detection indicators and evidence
- Displays structure hints when available

**Data Preview Tab** (📊)
- Multiple view modes: Tree, Table, Raw JSON, Summary
- **Tree View**: Hierarchical data structure with expand/collapse
- **Table View**: Tabular display for uniform data
- **Raw JSON**: Pretty-printed JSON representation
- **Summary**: Parsing statistics and metadata

**Format Conversion Tab** (🔄)
- Target format selection (TOON, JSON, CSV, YAML)
- Conversion options (indentation, length markers)
- Statistics showing size changes and efficiency
- Export converted data to file

## Loading Data

### Method 1: File Loading
1. Click "📁 Load File" button
2. Select any supported file type
3. File content appears in text area
4. Auto-detection starts after 500ms

### Method 2: Drag & Drop
1. Drag any file from your file manager
2. Drop it onto the parser window
3. File loads automatically with format detection

### Method 3: Manual Input
1. Click in the content text area
2. Paste or type your data directly
3. Use any supported format (TOON, JSON, CSV, etc.)

### Method 4: Context Menu (VArchiver Integration)
1. Right-click any file in VArchiver
2. Select "Parse with Dynamic Parser"
3. Parser launches with file pre-loaded

## Format Detection

### Automatic Detection Process
1. **File Extension Analysis**: Checks .toon, .json, .csv, etc.
2. **Content Pattern Matching**: Looks for format-specific syntax
3. **Structure Analysis**: Examines data organization
4. **Confidence Scoring**: Rates detection accuracy (0-1.0)

### Reading Detection Results
- **High Confidence (0.8+)**: Green indicator, very likely correct
- **Medium Confidence (0.5-0.8)**: Orange indicator, probably correct
- **Low Confidence (<0.5)**: Red indicator, uncertain detection

### Detection Indicators
Common indicators include:
- "File extension: .toon" - Extension-based detection
- "Tabular array declaration" - TOON syntax found
- "JSON brackets structure" - JSON-like format
- "Consistent comma separation" - CSV pattern
- "Valid XML parse" - Well-formed XML

## Parsing Content

### Basic Parsing
1. Load or enter content
2. Optionally adjust parser settings
3. Click "🚀 Parse Content"
4. View results in Data Preview tab

### Parser Settings Explained

**Format Hint**
- **Auto-detect**: Let parser determine format (recommended)
- **Specific Format**: Force parsing as TOON, JSON, etc.
- Use when auto-detection is uncertain

**Strict Parsing**
- **Enabled**: Fail immediately on structural errors
- **Disabled**: Attempt to continue parsing despite errors
- Useful for malformed or partial data

**Error Recovery**
- **Enabled**: Try to extract partial data from malformed input
- **Disabled**: Return null data on any parsing error
- Helpful for corrupted or incomplete files

**Delimiter**
- **Comma**: Standard CSV delimiter
- **Tab**: TSV (Tab-Separated Values)
- **Pipe**: Pipe-delimited format
- **Semicolon**: European CSV standard

### Understanding Parse Results

**Success Indicators**
- ✅ Green checkmark in results
- Data appears in preview tabs
- Status bar shows "Parse successful"

**Failure Indicators**
- ❌ Red X in results
- Error messages displayed
- Empty or null data

**Warnings**
- ⚠️ Yellow warning indicators
- Partial success with issues
- Data extracted but with problems

## Data Preview Modes

### Tree View
- **Best for**: Nested, hierarchical data structures
- **Features**: Expand/collapse nodes, type information
- **Controls**: "Expand All" / "Collapse All" buttons
- **Display**: Key-value pairs with data types

### Table View
- **Best for**: Uniform tabular data (arrays of objects)
- **Features**: Sortable columns, row highlighting
- **Formats**: Automatically formats lists of dictionaries
- **Fallback**: Shows key-value pairs for simple objects

### Raw JSON View
- **Best for**: Exact data structure examination
- **Features**: Syntax highlighting, proper indentation
- **Format**: Always shows JSON representation
- **Use case**: Debugging, exact structure verification

### Summary View
- **Best for**: Quick overview and statistics
- **Information includes**:
  - Basic parse information (format, success, timing)
  - Data structure summary (type, size, keys)
  - Parsing metadata (structure types, arrays found)
  - Warnings and errors with details

## Format Conversion

### Supported Conversions
- **TOON ↔ JSON**: Bidirectional with high fidelity
- **JSON → CSV**: Flattens tabular data structures
- **CSV → TOON**: Creates tabular arrays
- **Any → JSON**: Universal conversion target

### Conversion Process
1. Parse source data successfully first
2. Switch to "Format Conversion" tab
3. Select target format from dropdown
4. Adjust conversion options as needed
5. Click "🔄 Convert Now"
6. Review results and statistics
7. Export if satisfied

### Conversion Options

**Indentation Size** (1-8 spaces)
- Controls pretty-printing for JSON/TOON
- Smaller values = more compact
- Larger values = more readable

**Use Length Markers** (TOON only)
- Adds `#` prefix to array lengths: `array[#5]:`
- Helps with validation and parsing efficiency
- Optional but recommended for large arrays

### Understanding Conversion Statistics
- **Original Size**: Character count of source data
- **Converted Size**: Character count of result
- **Size Change**: Percentage increase/decrease
- **Positive values**: Result is larger than original
- **Negative values**: Result is smaller (more efficient)

### Exporting Converted Data
1. Click "💾 Export Converted Data"
2. Choose file location and name
3. File extension auto-suggested based on format
4. Click Save to write converted data

## TOON Format Features

### Tabular Arrays
```toon
users[3]{id,name,email,active}:
  1,Alice,alice@test.com,true
  2,Bob,bob@test.com,false  
  3,Carol,carol@test.com,true
```
- Declares field schema: `{id,name,email,active}`
- Length specification: `[3]` 
- Efficient for uniform data structures

### Simple Arrays
```toon
features[4]: archive,extract,browse,convert
categories: tools,utilities,media
```
- Inline format for simple lists
- Optional length specification
- Automatic type inference

### Key-Value Structures  
```toon
config:
  app_name: VArchiver
  version: 1.0.0
  debug: false
```
- Indentation-based hierarchy
- Automatic type detection
- Clean, readable syntax

### Complex Lists
```toon
projects[2]:
  - name: VArchiver
    status: active
    contributors[2]{name,role}:
      Alice,Lead Developer
      Bob,UI Designer
  - name: DataProcessor
    status: inactive
```
- Mixed content with `- ` prefixes
- Nested tabular arrays within lists
- Flexible structure for complex data

## Error Handling

### Common Parsing Errors

**"Invalid tabular array syntax"**
- **Cause**: Malformed TOON array declaration
- **Solution**: Check `array[length]{fields}:` syntax
- **Example Fix**: `users[2]{name,age}:` not `users{name,age}:`

**"Field count mismatch"** 
- **Cause**: Data row has wrong number of fields
- **Solution**: Enable error recovery or fix data
- **Prevention**: Verify CSV structure before parsing

**"Invalid JSON input"**
- **Cause**: Malformed JSON syntax
- **Solution**: Check brackets, quotes, commas
- **Tool**: Use Raw JSON view to examine structure

**"No format detected"**
- **Cause**: Content doesn't match any known format
- **Solution**: Check content or specify format hint
- **Fallback**: Try manual format selection

### Recovery Strategies

**Enable Error Recovery**
- Attempts partial data extraction
- Continues parsing despite errors  
- Shows warnings for problem areas

**Adjust Parser Settings**
- Try different delimiter options
- Disable strict mode
- Change format hint

**Content Preprocessing**
- Remove comments or extra content
- Fix obvious syntax errors
- Validate structure manually

## Integration with VArchiver

### Menu Integration
Access parser features through:
- **Tools → Dynamic Parser → Launch Parser** (Ctrl+Shift+P)
- **Tools → Dynamic Parser → Parse Current File** (Ctrl+Alt+P)
- **Tools → Dynamic Parser → Detect Format**
- **Tools → Dynamic Parser → Batch Process**

### Toolbar Integration
Quick access buttons in main toolbar:
- **🚀 Parse**: Launch parser window
- **🔍 Detect**: Detect format of current file

### Context Menu Integration
Right-click any file for:
- **Parse with Dynamic Parser**: Load file in parser
- **Detect Format**: Quick format detection dialog

### Status Bar Integration
Shows parser availability status:
- **✅ Available**: All components working
- **❌ Not Available**: Missing dependencies

## Performance and Optimization

### Performance Characteristics
- **Format Detection**: ~0.5ms average response
- **TOON Parsing**: 578K+ characters/second
- **JSON Parsing**: 147K+ characters/second
- **Memory Usage**: Efficient streaming for large files

### Optimization Tips

**For Large Files**
- Enable progress tracking for files >10KB
- Use batch processing for multiple files
- Consider format conversion for efficiency

**For Complex Data**
- Use Tree view for initial exploration
- Switch to Table view for tabular data
- Use Summary view for quick statistics

**For Repeated Tasks**
- Save parsing settings preferences
- Use keyboard shortcuts for common actions
- Batch process similar files together

## Troubleshooting

### GUI Won't Launch
**Error**: "PyQt5 not available"
```bash
pip install PyQt5
```

**Error**: "Dynamic parser not available"
- Check VArchiver installation
- Verify Python path includes varchiver directory
- Run dependency check: `python launch_dynamic_parser.py --check-deps`

### Parsing Issues
**Low detection confidence**
- Try specifying format hint manually
- Check for mixed content or comments
- Verify file isn't corrupted

**Parse fails completely**
- Enable error recovery mode
- Check file encoding (should be UTF-8)
- Try CLI mode: `python launch_dynamic_parser.py --cli`

**Conversion problems**
- Ensure source data parsed successfully first
- Check target format supports source structure
- Try intermediate conversion (e.g., via JSON)

### Performance Issues
**Slow parsing**
- Check available memory
- Try smaller test files first
- Use batch processing for multiple files

**GUI responsiveness**
- Parsing runs in background threads
- Large files show progress indication
- Use Ctrl+C to interrupt operations

## Advanced Features

### Batch Processing
1. Use menu: Tools → Dynamic Parser → Batch Process
2. Select directory containing files to process
3. Parser provides guidance for handling multiple files
4. Use CLI for advanced batch operations

### Custom Format Support
The parser is extensible for custom formats:
- Register new format detectors
- Add custom parsing logic
- Integrate with existing VArchiver workflows

### Keyboard Shortcuts
- **Ctrl+Shift+P**: Launch parser
- **Ctrl+Alt+P**: Parse current file
- **Ctrl+O**: Open file (when parser focused)
- **Ctrl+S**: Save/export results
- **F5**: Refresh/re-parse current content

## Tips and Best Practices

### Workflow Recommendations
1. **Start with detection**: Always detect format first
2. **Check confidence**: Low confidence may need format hint
3. **Use recovery mode**: For imperfect real-world data
4. **Preview before converting**: Verify parse results first
5. **Export important results**: Save converted data

### Format-Specific Tips

**TOON Files**
- Use consistent indentation (2 spaces recommended)
- Declare field schemas for tabular data
- Include length markers for validation

**JSON Files**  
- Validate syntax before parsing
- Use proper UTF-8 encoding
- Watch for trailing commas

**CSV Files**
- Ensure consistent delimiter usage
- Include headers in first row
- Handle quoted fields properly

### Efficiency Tips
- **TOON format**: 30-60% more token-efficient than JSON
- **Pipe delimiters**: Often more efficient than commas
- **Length markers**: Improve validation speed
- **Flat structures**: Process faster than deeply nested

## Support and Resources

### Documentation
- **Parser API**: `varchiver/varchiver/utils/dynamic_parser.py`
- **CLI Usage**: `python dynamic_parse.py --help`
- **Integration**: `varchiver/varchiver/widgets/parser_integration.py`

### Testing
- **Run tests**: `python test_dynamic_parser.py`
- **Specific tests**: `python test_dynamic_parser.py detection`
- **Demo mode**: `python launch_dynamic_parser.py --demo`

### Getting Help
1. Check error messages and status bar
2. Try CLI fallback mode for debugging
3. Run dependency checks
4. Review console output for detailed errors
5. Use demo mode to verify installation

---

*VArchiver Dynamic Parser GUI v1.0.0*
*Last updated: January 2025*