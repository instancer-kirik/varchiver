# Supabase Environment Management Guide

## Overview

Varchiver now includes an enhanced Supabase profile management system that intelligently handles `.env` files, making credential management secure, non-destructive, and user-friendly.

## Key Features

✅ **Smart .env File Management** - Automatically creates and maintains `.env` files  
✅ **Non-Destructive Updates** - Preserves existing environment variables  
✅ **Multiple Profile Support** - Manage multiple Supabase projects easily  
✅ **Environment Variable Detection** - Automatically detects profiles from existing env vars  
✅ **Secure Credential Storage** - Keeps secrets out of version control  
✅ **GUI Configuration** - Easy-to-use dialog for managing profiles  
✅ **Real-time Validation** - Test connections before saving  

## Quick Start

### 1. Initial Setup

When you first run Varchiver, it will:
- Look for an existing `.env` file in your project directory
- If none exists, create one automatically
- Load any existing Supabase environment variables

### 2. Adding Your First Profile

1. Open Varchiver
2. Go to **Supabase tools** → **Manage Connections...**
3. Click **"Add Environment Profile"**
4. Fill in your profile details:
   - **Profile Name**: e.g., "Production", "Development", "Staging"
   - **Use Environment Variables**: ✅ (recommended)
   - **Project URL**: Your Supabase project URL
   - **Anon Key**: Your public/anon key
   - **Service Key**: Your service role key
5. Click **"Test Connection"** to verify
6. Click **"Save"**

Your credentials will be automatically saved to the `.env` file!

## Environment Variable Format

The system uses a consistent naming pattern:

```bash
SUPABASE_{PROFILE_NAME}_{CREDENTIAL_TYPE}
```

### Example

For a profile named "Production":

```bash
# Production Supabase Profile
SUPABASE_PRODUCTION_URL=https://your-project-ref.supabase.co
SUPABASE_PRODUCTION_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_PRODUCTION_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Configuration Options

### Profile Types

**Environment Profiles (Recommended)**
- Credentials stored in `.env` file
- Secure and excluded from version control
- Easy to manage through the GUI
- Supports multiple environments

**Direct Configuration Profiles**
- Credentials stored in config file
- Less secure (stored in plain text config)
- Useful for testing or development only

### Managing Multiple Environments

Create separate profiles for different environments:

```bash
# Development Environment
SUPABASE_DEVELOPMENT_URL=https://dev-project.supabase.co
SUPABASE_DEVELOPMENT_ANON_KEY=eyJ...
SUPABASE_DEVELOPMENT_SERVICE_KEY=eyJ...

# Staging Environment  
SUPABASE_STAGING_URL=https://staging-project.supabase.co
SUPABASE_STAGING_ANON_KEY=eyJ...
SUPABASE_STAGING_SERVICE_KEY=eyJ...

# Production Environment
SUPABASE_PRODUCTION_URL=https://prod-project.supabase.co
SUPABASE_PRODUCTION_ANON_KEY=eyJ...
SUPABASE_PRODUCTION_SERVICE_KEY=eyJ...
```

## Using the Configuration Dialog

### Profile Management Tab

- **Add New Profile**: Create a profile with direct configuration
- **Add Environment Profile**: Create a profile that uses `.env` variables
- **Delete Selected**: Remove a profile (also removes from `.env` if applicable)

### Environment Variables Tab

- View and directly edit your `.env` file content
- Changes are saved when you click "Save"
- Shows the current path to your `.env` file
- Reload button to refresh from disk

### Connection Testing

- **Test Connection**: Verify your credentials work
- **Debug Connection**: Get detailed diagnostic information
- Shows validation status for each credential

## Manual .env Management

If you prefer to manage the `.env` file manually:

### 1. Create .env File

Copy the example template:

```bash
cp .env.example .env
```

### 2. Edit Credentials

Replace the example values with your actual credentials:

```bash
# Your actual Supabase project
SUPABASE_MYPROJECT_URL=https://abcd1234.supabase.co
SUPABASE_MYPROJECT_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiY2QxMjM0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE2Mzk1NzY4MDAsImV4cCI6MTk1NTE1MjgwMH0.signature
SUPABASE_MYPROJECT_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiY2QxMjM0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTYzOTU3NjgwMCwiZXhwIjoxOTU1MTUyODAwfQ.signature
```

### 3. Add Profile in Varchiver

1. Open **Manage Connections...**
2. Click **"Add Environment Profile"**
3. Set the profile name to match your env vars (e.g., "MyProject")
4. The system will automatically detect and load your credentials

## Security Best Practices

### ✅ Do This

- ✅ Use environment profiles for all production credentials
- ✅ Keep `.env` files in `.gitignore` (already configured)
- ✅ Use descriptive profile names (PRODUCTION, STAGING, DEV)
- ✅ Rotate keys regularly
- ✅ Use service keys with minimal required permissions
- ✅ Test connections before deploying

### ❌ Don't Do This

- ❌ Commit `.env` files to version control
- ❌ Share `.env` files in chat/email
- ❌ Store production keys in direct configuration profiles
- ❌ Use overprivileged service keys
- ❌ Leave unused profiles with active credentials

## Troubleshooting

### Profile Not Detected

**Problem**: Environment variables exist but profile not showing in dialog.

**Solution**: 
1. Check variable naming follows `SUPABASE_{NAME}_{TYPE}` pattern
2. Restart Varchiver to reload environment
3. Use "Reload from File" in Environment Variables tab

### Connection Test Fails

**Problem**: "Connection failed" error when testing.

**Solutions**:
1. Verify URL format: `https://your-project-ref.supabase.co`
2. Check keys are complete (not truncated)
3. Confirm keys have necessary permissions in Supabase dashboard
4. Try the "Debug Connection" button for detailed diagnostics

### .env File Not Loading

**Problem**: Environment variables not available in application.

**Solutions**:
1. Check `.env` file is in the project root directory
2. Verify file syntax (no spaces around `=`)
3. Restart Varchiver
4. Check file permissions

### Multiple Profiles Confusion

**Problem**: Wrong profile being used or mixed credentials.

**Solutions**:
1. Check "Active Profile" selection in configuration dialog
2. Use Debug Connection to see which profile is active
3. Ensure profile names are unique and descriptive

## Advanced Usage

### Programmatic Access

```python
from varchiver.utils.supabase_connector import get_supabase_client, get_supabase_service_client

# Get the main client (uses anon key)
client = get_supabase_client()

# Get the service client (uses service key) 
service_client = get_supabase_service_client()

# Test connection programmatically
from varchiver.utils.supabase_connector import get_supabase_connector
connector = get_supabase_connector()
success, message = connector.test_connection()
```

### Environment Manager API

```python
from varchiver.utils.env_manager import EnvManager

env_manager = EnvManager()

# Get all detected profiles
profiles = env_manager.get_all_supabase_profiles()

# Get credentials for a specific profile
credentials = env_manager.get_env_vars_for_profile("production")

# Set credentials for a profile
env_manager.set_env_vars_for_profile("newproject", {
    "url": "https://newproject.supabase.co",
    "anon_key": "eyJ...",
    "service_key": "eyJ..."
})
```

## Migration from Old System

If you're upgrading from an older version:

1. **Backup**: Your existing configuration will be preserved
2. **Convert**: Use "Add Environment Profile" to move credentials to `.env`
3. **Verify**: Test all connections after migration
4. **Clean up**: Remove old direct configuration profiles if desired

## File Structure

```
your-project/
├── .env                    # Your credentials (auto-created)
├── .env.example           # Template file (safe to commit)
├── .gitignore             # Includes .env exclusion
└── varchiver/
    ├── .config/varchiver/
    │   └── config.json    # App configuration
    └── ...
```

## Support

If you encounter issues:

1. Run the test script: `python test_supabase_env.py`
2. Check the debug information in the configuration dialog
3. Verify your `.env` file syntax
4. Ensure your Supabase credentials are correct and have proper permissions

The new system is designed to be robust and user-friendly. It handles edge cases automatically and provides clear feedback when something needs attention.