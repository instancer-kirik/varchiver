# Supamerge - Supabase Project Migration Tool

Supamerge is a comprehensive tool for migrating schema, data, and policies between Supabase projects. It's integrated into Varchiver and also available as a standalone CLI tool.

## 🚀 Features

- **Complete Project Migration**: Migrate schema, data, RLS policies, and storage buckets
- **Safe Migration**: Automatic backup creation before making changes
- **Conflict Resolution**: Intelligent handling of conflicting table names and structures
- **Dry Run Mode**: Preview migrations without making changes
- **GUI and CLI**: Use through Varchiver's interface or command line
- **Environment Variable Support**: Secure credential management
- **Progress Tracking**: Real-time migration progress and detailed logs

## 📋 What Gets Migrated

### Database Elements
- ✅ **Schema Structure**: Tables, columns, indexes, constraints
- ✅ **Table Data**: Complete data migration with collision handling
- ✅ **Row Level Security (RLS)**: Policies and permissions
- ✅ **Custom Types**: Enums and composite types
- ✅ **Functions**: PostgreSQL functions and triggers

### Supabase Features
- ✅ **Storage Buckets**: Files and bucket configurations
- ✅ **Auth Settings**: User roles and permissions (optional)
- ✅ **Edge Functions**: Function definitions and configurations
- ✅ **API Configurations**: REST and GraphQL settings

## 🛠️ Installation

Supamerge is included with Varchiver. Install via:

```bash
# From AUR (Arch Linux)
yay -S varchiver

# From source
git clone https://github.com/kirik/varchiver.git
cd varchiver
uv pip install -e .[dev]
```

## 🖥️ GUI Usage

1. Launch Varchiver: `varchiver`
2. Switch to "Supamerge" mode from the dropdown
3. Set up your source and target connections
4. Configure migration options
5. Run validation and start migration

### Setting Up Connections

**Option 1: Use Existing Supabase Connections**
- Click "Manage Connections..." to add your projects
- Select source and target from dropdowns

**Option 2: Load Configuration File**
- Create a YAML config file (see examples below)
- Load it using "Load Config..." button

## 💻 CLI Usage

### Quick Start

```bash
# Create configuration template
supamerge template --output my-migration.yaml

# Edit the template with your project details
# Then validate the configuration
supamerge validate --config my-migration.yaml

# Run dry-run to preview changes
supamerge migrate --config my-migration.yaml --dry-run

# Execute actual migration
supamerge migrate --config my-migration.yaml
```

### Environment-Based Migration

```bash
# Set environment variables
export SOURCE_PROJECT_REF="abc123"
export SOURCE_SUPABASE_URL="https://abc123.supabase.co"
export SOURCE_ANON_KEY="eyJ..."
export SOURCE_SERVICE_KEY="eyJ..."

export TARGET_PROJECT_REF="def456"
export TARGET_SUPABASE_URL="https://def456.supabase.co"
export TARGET_ANON_KEY="eyJ..."
export TARGET_SERVICE_KEY="eyJ..."

# Run migration
supamerge migrate --from-env SOURCE --to-env TARGET --backup --include-data
```

## ⚙️ Configuration

### YAML Configuration Format

```yaml
source:
  project_ref: "your-source-project-ref"
  supabase_url: "https://your-source-project.supabase.co"
  anon_key: "${SOURCE_ANON_KEY}"
  service_role_key: "${SOURCE_SERVICE_KEY}"

target:
  project_ref: "your-target-project-ref"
  supabase_url: "https://your-target-project.supabase.co"
  anon_key: "${TARGET_ANON_KEY}"
  service_role_key: "${TARGET_SERVICE_KEY}"

include:
  schemas: ["public", "auth"]
  include_data: true
  include_policies: true
  include_storage: true

options:
  backup_target_first: true
  remap_conflicts: true
  skip_auth: false
  dry_run: false
```

### Connection String Format

Get your database connection string from:
1. Supabase Dashboard → Settings → Database
2. Look for "Connection string" section
3. Use the "Connection pooling" URL format:

```
postgresql://postgres.PROJECT_REF:SERVICE_ROLE_KEY@aws-0-us-west-1.pooler.supabase.com:5432/postgres
```

## 🔧 Migration Options

| Option | Description | Default |
|--------|-------------|---------|
| `backup_target_first` | Create backup before migration | `true` |
| `include_data` | Migrate table data | `true` |
| `include_policies` | Migrate RLS policies | `true` |
| `include_storage` | Migrate storage buckets | `true` |
| `remap_conflicts` | Auto-rename conflicting tables | `true` |
| `schemas` | Schemas to migrate | `["public"]` |
| `dry_run` | Preview without changes | `false` |

## 🚨 Safety Features

### Automatic Backups
- Target database is automatically backed up before migration
- Backups are stored as `.dump` files with timestamps
- Can be restored using `pg_restore`

### Conflict Resolution
- Detects existing tables/objects in target
- Options to rename, skip, or merge conflicting items
- Detailed conflict reports generated

### Validation Checks
- Connection testing before migration
- Schema compatibility verification  
- Permission and access validation

## 📊 Migration Process

1. **Pre-flight Checks**
   - Validate source and target connections
   - Check required permissions
   - Analyze potential conflicts

2. **Backup Phase** (if enabled)
   - Create timestamped backup of target database
   - Verify backup integrity

3. **Schema Migration**
   - Export source schema using `pg_dump`
   - Apply schema to target with conflict resolution

4. **Data Migration**
   - Migrate table data with collision handling
   - Preserve data integrity and constraints

5. **Supabase Features**
   - Copy storage buckets and files
   - Migrate RLS policies and auth settings
   - Update API configurations

6. **Verification**
   - Compare row counts and critical data
   - Generate migration report
   - Log all actions and results

## 🐛 Troubleshooting

### Common Issues

**Connection Errors**
```bash
# Test your connection using the Supabase client
# Connection test is built into the UI configuration dialog
```

**Permission Issues**
- Ensure service role key has sufficient permissions
- Check RLS policies aren't blocking migration
- Verify target project allows schema modifications

**Large Database Migrations**
- Consider migrating schema first, then data separately
- Use `--schemas` to migrate specific schemas only
- Monitor disk space for backup files

### Debug Mode

```bash
# Enable verbose logging
supamerge migrate --config config.yaml --verbose

# Check log files in logs/ directory
tail -f logs/supamerge_*.log
```

## 🔒 Security Best Practices

1. **Use Environment Variables**: Never commit credentials to config files
2. **Service Role Keys**: Use least-privilege keys when possible
3. **Network Security**: Run migrations from secure networks
4. **Backup Verification**: Always verify backups before migration
5. **Test Migrations**: Use staging environments first

## 📝 Examples

### Staging to Production

```yaml
# staging-to-prod.yaml
source:
  project_ref: "staging-abc123"
  supabase_url: "https://staging-abc123.supabase.co"
  anon_key: "${STAGING_ANON_KEY}"
  service_role_key: "${STAGING_SERVICE_KEY}"

target:
  project_ref: "prod-def456"
  supabase_url: "https://prod-def456.supabase.co"
  anon_key: "${PROD_ANON_KEY}"
  service_role_key: "${PROD_SERVICE_KEY}"

options:
  backup_target_first: true
  dry_run: true  # Always dry-run prod migrations first!
```

### Schema-Only Migration

```bash
supamerge migrate \
  --config config.yaml \
  --schemas public \
  --no-include-data \
  --include-policies
```

### Emergency Migration

```bash
# Quick migration with minimal safety checks (not recommended)
supamerge migrate \
  --from-env SOURCE \
  --to-env TARGET \
  --no-backup \
  --no-remap
```

## 🤝 Contributing

Found a bug or want to contribute? 

1. Check existing issues: https://github.com/kirik/varchiver/issues
2. Create detailed bug reports with logs
3. Submit pull requests with tests
4. Help improve documentation

## 📄 License

Supamerge is part of Varchiver and shares the same proprietary license.

## ⚡ Performance Tips

- Use connection pooling for large migrations
- Migrate during low-traffic periods
- Monitor both source and target resource usage
- Consider breaking large migrations into chunks
- Use dry-run mode to estimate migration time

---

**Need Help?** Check the logs in `logs/supamerge_*.log` or create an issue with your configuration and error messages.