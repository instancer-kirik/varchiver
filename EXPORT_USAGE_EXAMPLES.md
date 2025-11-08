# Supabase Export - Real Usage Examples

This guide shows you exactly how to use the Supabase export tools with real credentials and projects. Perfect for widget merging and project migration.

## 🚀 Prerequisites Checklist

- [x] Export tools installed and working
- [ ] Supabase project credentials ready
- [ ] Profile configured (GUI or environment)

## 📋 Step 1: Get Your Supabase Credentials

For each project you want to export, collect these from your Supabase Dashboard:

### Finding Your Credentials

1. **Open Supabase Dashboard** → Go to your project
2. **Settings** → **API** tab
3. **Copy these values:**
   - **Project URL**: `https://your-project-abc123.supabase.co`
   - **anon/public key**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
   - **service_role key**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

### Database Connection URL (for advanced usage)

4. **Settings** → **Database** tab
5. **Connection string** → Copy the "Connection pooling" URL:
   ```
   postgresql://postgres.abc123:[YOUR-PASSWORD]@aws-0-region.pooler.supabase.com:5432/postgres
   ```

## 📝 Step 2: Configure Your Profiles

### Option A: Using Environment Variables (Recommended)

Create or edit your `.env` file in the varchiver directory:

```bash
# Widget Project 1
SUPABASE_WIDGET1_URL=https://your-widget1-abc123.supabase.co
SUPABASE_WIDGET1_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiYzEyMyIsInJvbGUiOiJhbm9uIiwiaWF0IjoxNjM5NTc2ODAwLCJleHAiOjE5NTUxNTI4MDB9.signature
SUPABASE_WIDGET1_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiYzEyMyIsInJvbGUiOiJzZXJ2aWNlX3JvbGUiLCJpYXQiOjE2Mzk1NzY4MDAsImV4cCI6MTk1NTE1MjgwMH0.signature

# Widget Project 2
SUPABASE_WIDGET2_URL=https://your-widget2-def456.supabase.co
SUPABASE_WIDGET2_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRlZjQ1NiIsInJvbGUiOiJhbm9uIiwiaWF0IjoxNjM5NTc2ODAwLCJleHAiOjE5NTUxNTI4MDB9.signature  
SUPABASE_WIDGET2_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRlZjQ1NiIsInJvbGUiOiJzZXJ2aWNlX3JvbGUiLCJpYXQiOjE2Mzk1NzY4MDAsImV4cCI6MTk1NTE1MjgwMH0.signature
```

**⚠️ Important:** Replace the example URLs and keys with your actual credentials!

### Option B: Using Varchiver GUI

1. **Launch Varchiver**: `uv run python varchiver/main.py`
2. **Supabase tools** → **Manage Connections...**
3. **Add Environment Profile**
4. Fill in your details and test the connection

## ✅ Step 3: Verify Your Setup

```bash
# Check that your profiles are detected
uv run python export_supabase.py --list-profiles
```

**Expected output:**
```
🔗 Available Supabase Profiles:
   📁 Environment Profiles:
     • widget1: https://your-widget1-abc123.supabase.co
     • widget2: https://your-widget2-def456.supabase.co
   🖥️  GUI Profiles:
     • My Production App: https://prod-app.supabase.co
```

## 🎯 Step 4: Real Export Examples

### Example 1: Full Project Backup

```bash
# Create a complete backup of your widget project
uv run python export_supabase.py --profile widget1 --format dump --output ./backups

# Results in: ./backups/widget1_20231215_143022/widget1_export_20231215_143022.dump
```

**Use case:** Before making changes or migrating to another project.

### Example 2: Data Analysis Export

```bash
# Export for analysis and comparison
uv run python export_supabase.py --profile widget1 --format json --output ./analysis

# Creates separate files:
# - widget1_schema_*.json    (database structure)
# - widget1_data_*.json      (all table data)  
# - widget1_policies_*.json  (security policies)
```

**Use case:** Understanding your data structure before merging with another project.

### Example 3: Schema-Only Export

```bash
# Export just the database structure (no data)
uv run python export_supabase.py --profile widget1 --format sql --no-data

# Creates: widget1_export_*.sql with CREATE TABLE statements
```

**Use case:** Setting up a new project with the same structure.

### Example 4: Specific Tables Only

```bash
# Export only certain tables
uv run python export_supabase.py --profile widget1 --tables users,posts,comments --format json

# Only exports the specified tables
```

**Use case:** Partial data migration or analysis.

## 🔄 Step 5: Widget Project Comparison & Merging

### Compare Two Widget Projects

```bash
# Analyze differences between your widget projects
uv run python examples/widget_export_example.py --compare widget1 widget2

# Creates detailed comparison report showing:
# - Common tables
# - Unique tables in each project  
# - Column conflicts that need resolution
```

**Sample Output:**
```
📊 Schema Comparison Results:
   Common tables: 8
   Tables unique to widget1: 3
   Tables unique to widget2: 2
   Tables with column conflicts: 1

⚠️  Column Conflicts Detected:
   Table 'user_profiles':
     - avatar_url: text vs varchar(255)

📄 Comparison report saved: widget_exports/schema_comparison_widget1_vs_widget2.json
```

### Prepare Complete Widget Merge

```bash
# Get everything ready for merging widget1 into widget2
uv run python examples/widget_export_example.py --prepare-merge widget1 widget2

# This creates:
# - Complete backups of both projects
# - Schema comparison analysis
# - Merge strategy document
# - Step-by-step instructions
```

**Generated Files:**
```
widget_exports/
├── widget1_export_20231215_143022.dump         # Source data
├── widget1_data_20231215_143022.json           # Source as JSON
├── widget2_backup_20231215_143100.dump         # Target backup
├── schema_comparison_widget1_vs_widget2.json   # Analysis
├── merge_strategy_widget1_to_widget2.yaml      # Strategy
└── MERGE_INSTRUCTIONS_widget1_to_widget2.md    # Instructions
```

### Execute the Widget Merge

```bash
# Test the merge first (safe dry run)
uv run supamerge migrate --from-env WIDGET1 --to-env WIDGET2 --backup --dry-run

# Review the output, then execute for real:
uv run supamerge migrate --from-env WIDGET1 --to-env WIDGET2 --backup --include-data
```

## 🔧 Advanced Usage with Supamerge CLI

### Using Environment Variables

```bash
# Set up environment for CLI usage
export SOURCE_PROJECT_REF="widget1-abc123"
export SOURCE_SUPABASE_URL="https://widget1-abc123.supabase.co"
export SOURCE_ANON_KEY="eyJhbGciOiJIUzI1NiIs..."
export SOURCE_SERVICE_KEY="eyJhbGciOiJIUzI1NiIs..."

# Export using environment variables
uv run supamerge export --from-env SOURCE --format json --output ./exports
```

### Using Configuration File

Create `my_export_config.yaml`:
```yaml
source:
  project_ref: "widget1-abc123"
  db_url: "postgresql://postgres.widget1-abc123:YOUR-SERVICE-KEY@aws-0-us-west-1.pooler.supabase.com:5432/postgres"
  supabase_url: "https://widget1-abc123.supabase.co"
  anon_key: "eyJhbGciOiJIUzI1NiIs..."
  service_role_key: "eyJhbGciOiJIUzI1NiIs..."

export_options:
  output_format: "dump"
  output_dir: "./my_exports"
  include_data: true
  schemas: ["public"]
```

Then export:
```bash
uv run supamerge export --config my_export_config.yaml
```

## 📊 Real-World Workflow: Merging Two Widget Apps

Let's say you have two widget applications you want to merge:

### Project Details
- **Widget App A**: User management and profiles
- **Widget App B**: Content management and posts  
- **Goal**: Merge App A into App B to create a unified platform

### Step-by-Step Process

#### 1. Set Up Credentials
```bash
# Add to .env file
SUPABASE_WIDGETAPPA_URL=https://user-widget-abc123.supabase.co
SUPABASE_WIDGETAPPA_ANON_KEY=eyJ...actual-key-here
SUPABASE_WIDGETAPPA_SERVICE_KEY=eyJ...actual-key-here

SUPABASE_WIDGETAPPB_URL=https://content-widget-def456.supabase.co  
SUPABASE_WIDGETAPPB_ANON_KEY=eyJ...actual-key-here
SUPABASE_WIDGETAPPB_SERVICE_KEY=eyJ...actual-key-here
```

#### 2. Verify Connection
```bash
uv run python export_supabase.py --list-profiles
# Should show widgetappa and widgetappb
```

#### 3. Create Backups
```bash
# Backup both projects first!
uv run python export_supabase.py --profile widgetappa --format dump --output ./backups
uv run python export_supabase.py --profile widgetappb --format dump --output ./backups
```

#### 4. Analyze for Conflicts
```bash
# Compare the two projects  
uv run python examples/widget_export_example.py --compare widgetappa widgetappb

# Check the generated report for conflicts
cat widget_exports/schema_comparison_widgetappa_vs_widgetappb.json
```

#### 5. Prepare Migration
```bash  
# Generate complete merge strategy
uv run python examples/widget_export_example.py --prepare-merge widgetappa widgetappb

# Review the instructions
cat widget_exports/MERGE_INSTRUCTIONS_widgetappa_to_widgetappb.md
```

#### 6. Execute Migration
```bash
# Dry run first to test
uv run supamerge migrate --from-env WIDGETAPPA --to-env WIDGETAPPB --backup --dry-run

# If everything looks good, run for real
uv run supamerge migrate --from-env WIDGETAPPA --to-env WIDGETAPPB --backup --include-data
```

#### 7. Verify Results
```bash
# Export the merged result to verify
uv run python export_supabase.py --profile widgetappb --format json --output ./verification

# Check row counts, sample data, etc.
```

## 🚨 Troubleshooting Real Issues

### "Tenant or user not found"
**Problem**: Connection fails with tenant error
**Solution**: 
- Check your project URL format: must be `https://your-project-ref.supabase.co`
- Verify the project ref in your service key matches the URL
- Ensure the project isn't paused or deleted

### "Permission denied for schema public"  
**Problem**: Service key doesn't have enough permissions
**Solution**:
- Go to Supabase Dashboard → Settings → API
- Regenerate service role key
- Verify RLS policies aren't blocking the service role

### "Profile not found" (but you set it up)
**Problem**: Environment variables not loading
**Solution**:
```bash
# Check if variables are set
env | grep SUPABASE_

# Make sure .env file is in the right location
ls -la .env

# Restart your terminal/shell
```

### Large Export Timeouts
**Problem**: Export hangs or times out on large databases
**Solution**:
```bash
# Export schema first, then data separately
uv run python export_supabase.py --profile myproject --no-data --format sql

# Or export specific tables
uv run python export_supabase.py --profile myproject --tables users,posts --format dump
```

## 🎉 Success Stories

### Widget Merge Success
After following this guide, you should have:
- ✅ Complete backups of both projects
- ✅ Successful schema analysis and conflict resolution  
- ✅ Clean migration with all data preserved
- ✅ Unified widget application with features from both projects

### Export Success
Your export files can be used for:
- ✅ **Development**: Set up local copies for testing
- ✅ **Staging**: Create staging environments  
- ✅ **Analysis**: Understand your data patterns
- ✅ **Migration**: Move to different providers or regions
- ✅ **Backup**: Regular automated backups

## 📞 Getting Help

If you encounter issues:

1. **Check the logs**: `tail -f logs/export_*.log`
2. **Use verbose mode**: Add `--verbose` to any command  
3. **Verify credentials**: Test connection in Supabase dashboard first
4. **Check permissions**: Ensure service role key has database access

**Common success indicators:**
- Profiles show up in `--list-profiles`
- Exports create files (even if empty due to connection issues)
- Dry runs complete without errors
- Actual migrations show row count changes

You're now ready to export, analyze, and merge your Supabase widget projects with confidence! 🚀