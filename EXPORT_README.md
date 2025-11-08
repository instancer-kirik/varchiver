# Supabase Export Tools

Complete toolkit for exporting Supabase project state in various formats, specifically designed for widget merging and project migration.

## 🚀 Quick Start

### Simple Export

```bash
# Export your project as PostgreSQL dump
uv run python export_supabase.py --profile myproject

# Export as JSON for analysis
uv run python export_supabase.py --profile widget1 --format json

# List available profiles
uv run python export_supabase.py --list-profiles
```

### Advanced Export with Supamerge CLI

```bash
# Export using Supamerge CLI
supamerge export --from-env MYPROJECT --format dump --output ./exports

# Export specific schemas only
supamerge export --config config.yaml --format json --schemas public,auth
```

## 📋 Supported Export Formats

| Format | Extension | Use Case | Restore Method |
|--------|-----------|----------|----------------|
| **dump** | `.dump` | Full migration, backup | `pg_restore` |
| **sql** | `.sql` | Manual editing, review | `psql < file.sql` |
| **json** | `.json` | Analysis, custom scripts | Custom import |
| **yaml** | `.yaml` | Configuration, human-readable | Custom import |

## 🛠️ Export Options

### What Gets Exported

- ✅ **Database Schema**: Tables, columns, indexes, constraints
- ✅ **Table Data**: Complete row data with proper typing
- ✅ **RLS Policies**: Row-level security configurations
- ✅ **Custom Types**: Enums and composite types
- ✅ **Functions & Triggers**: PostgreSQL functions (in dump/sql formats)
- ⚠️ **Storage Buckets**: Optional (not included by default)
- ❌ **Auth Users**: Excluded for security (can be enabled)

### Format Details

#### PostgreSQL Dump (.dump)
- **Most Complete**: Includes schema, data, functions, triggers
- **Binary Format**: Efficient storage and fast restore
- **pg_restore Compatible**: Standard PostgreSQL restoration
- **Recommended for**: Production migrations, full backups

#### SQL Export (.sql)
- **Human Readable**: Plain text SQL statements
- **Editable**: Can modify before importing
- **Universal**: Works with any PostgreSQL client
- **Recommended for**: Development, manual review

#### JSON Export (.json)
- **Structured Data**: Separate schema and data files
- **API Friendly**: Easy to process programmatically
- **Analysis Ready**: Perfect for data comparison
- **Recommended for**: Widget merging, data analysis

#### YAML Export (.yaml)
- **Configuration Format**: Human-readable structure
- **Version Control**: Easy to diff and track changes
- **Documentation**: Self-documenting format
- **Recommended for**: Configuration management

## 🔧 Usage Examples

### Basic Export

```bash
# Export everything as PostgreSQL dump
uv run python export_supabase.py --profile myproject

# Export schema only (no data)
uv run python export_supabase.py --profile myproject --no-data

# Export specific schemas
uv run python export_supabase.py --profile myproject --schemas public,auth
```

### Widget Project Merging

```bash
# Compare two widget projects
uv run python examples/widget_export_example.py --compare widget1 widget2

# Prepare complete merge
uv run python examples/widget_export_example.py --prepare-merge widget1 widget2

# Export for analysis
uv run python export_supabase.py --profile widget1 --format json
uv run python export_supabase.py --profile widget2 --format json
```

### Advanced Supamerge CLI

```bash
# Export with environment variables
export SOURCE_PROJECT_REF="abc123"
export SOURCE_SUPABASE_URL="https://abc123.supabase.co"
export SOURCE_ANON_KEY="eyJ..."
export SOURCE_SERVICE_KEY="eyJ..."

supamerge export --from-env SOURCE --format dump --include-data

# Export using config file
supamerge export --config export_config.yaml --format json
```

## 📁 File Organization

Exports are organized by profile and timestamp:

```
exports/
├── myproject_20231215_143022/
│   ├── myproject_export_20231215_143022.dump
│   ├── myproject_manifest_20231215_143022.json
│   └── export_20231215_143022.log
├── widget1_20231215_143100/
│   ├── widget1_schema_20231215_143100.json
│   ├── widget1_data_20231215_143100.json
│   ├── widget1_policies_20231215_143100.json
│   └── widget1_manifest_20231215_143100.json
└── comparison_reports/
    ├── schema_comparison_widget1_vs_widget2.json
    └── merge_strategy_widget1_to_widget2.yaml
```

## 🔗 Profile Management

### Setting Up Profiles

**Option 1: Using Varchiver GUI**
1. Open Varchiver
2. Go to Supabase tools → Manage Connections
3. Add Environment Profile
4. Fill in your project details

**Option 2: Environment Variables**
```bash
# Set environment variables
export SUPABASE_MYPROJECT_URL="https://abc123.supabase.co"
export SUPABASE_MYPROJECT_ANON_KEY="eyJ..."
export SUPABASE_MYPROJECT_SERVICE_KEY="eyJ..."
```

**Option 3: Manual .env File**
```bash
# Add to .env file
SUPABASE_WIDGET1_URL=https://widget1.supabase.co
SUPABASE_WIDGET1_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_WIDGET1_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Finding Your Credentials

1. Go to your Supabase Dashboard
2. Settings → API
3. Copy the values:
   - **Project URL**: Use as `SUPABASE_*_URL`
   - **anon/public key**: Use as `SUPABASE_*_ANON_KEY`
   - **service_role key**: Use as `SUPABASE_*_SERVICE_KEY`

## 🎯 Widget Merging Workflow

### Step 1: Analyze Projects
```bash
uv run python examples/widget_export_example.py --compare widget1 widget2
```
This creates a comparison report showing:
- Common tables between projects
- Unique tables in each project
- Column conflicts that need resolution

### Step 2: Export Source Data
```bash
uv run python export_supabase.py --profile widget1 --format dump
uv run python export_supabase.py --profile widget1 --format json
```

### Step 3: Backup Target
```bash
uv run python export_supabase.py --profile widget2 --format dump --output ./backups
```

### Step 4: Prepare Merge Strategy
```bash
uv run python examples/widget_export_example.py --prepare-merge widget1 widget2
```
This generates:
- Merge strategy document
- Step-by-step instructions
- SQL commands for manual resolution

### Step 5: Execute Migration
```bash
# Test first with dry run
supamerge migrate --from-env WIDGET1 --to-env WIDGET2 --dry-run --backup

# Execute actual migration
supamerge migrate --from-env WIDGET1 --to-env WIDGET2 --backup --include-data
```

## 🔒 Security Best Practices

### Credential Management
- ✅ Use environment variables for credentials
- ✅ Keep `.env` files out of version control
- ✅ Use service keys with minimal required permissions
- ✅ Rotate keys regularly
- ❌ Never commit credentials to code

### Export Security
- ✅ Exclude auth data by default
- ✅ Review exported data before sharing
- ✅ Store exports securely
- ✅ Delete temporary exports after use

## 🚨 Troubleshooting

### Common Issues

**"Profile not found"**
```bash
# Check available profiles
uv run python export_supabase.py --list-profiles

# Verify environment variables
env | grep SUPABASE_
```

**Connection Failures**
- Verify project URL format: `https://your-project.supabase.co`
- Check service key permissions in Supabase dashboard
- Ensure network connectivity

**Large Export Timeouts**
- Use `--no-data` for schema-only exports first
- Export specific schemas with `--schemas`
- Consider splitting large exports by table

**Permission Errors**
- Ensure service role key has sufficient privileges
- Check RLS policies aren't blocking access
- Verify database connection URL format

### Debug Mode

```bash
# Enable verbose logging
uv run python export_supabase.py --profile myproject --verbose

# Check Supamerge logs
tail -f logs/export_*.log
```

## 🔄 Integration with Supamerge

The export functionality is fully integrated with Supamerge for complete migration workflows:

```bash
# Export → Analyze → Migrate workflow
supamerge export --from-env SOURCE --format json
# Review exported data and conflicts
supamerge migrate --from-env SOURCE --to-env TARGET --backup
```

## 📚 Advanced Configuration

### Custom Export Configuration

Create `export_config.yaml`:
```yaml
source:
  project_ref: "my-project"
  supabase_url: "https://my-project.supabase.co"
  anon_key: "${SUPABASE_MYPROJECT_ANON_KEY}"
  service_role_key: "${SUPABASE_MYPROJECT_SERVICE_KEY}"

export_options:
  output_format: "json"
  output_dir: "./custom_exports"
  include_schema: true
  include_data: true
  include_policies: true
  schemas: ["public", "custom"]
  tables: ["users", "posts", "comments"]
```

### Programmatic Usage

```python
from varchiver.supamerge.export import export_supabase_project
from varchiver.supamerge.core import SourceConfig

# Configure source
source = SourceConfig(
    project_ref="my-project",
    db_url="postgresql://...",
    supabase_url="https://my-project.supabase.co",
    anon_key="eyJ...",
    service_role_key="eyJ..."
)

# Export project
result = await export_supabase_project(
    source_config=source,
    output_format="json",
    include_data=True
)

if result.success:
    print(f"Export completed: {result.export_files}")
```

## 🤝 Contributing

Found a bug or want to add features?
1. Check existing issues
2. Create detailed bug reports
3. Submit pull requests with tests

## 📄 License

Part of the Varchiver project. See main LICENSE file.

---

**Need Help?** 
- Check the logs in `logs/export_*.log`
- Use `--verbose` flag for detailed output
- Create an issue with your configuration and error messages