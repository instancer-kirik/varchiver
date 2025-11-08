# Environment Variable Setup for Supabase Connections

## Overview

For security, you can store your Supabase credentials in environment variables instead of saving them in configuration files. This prevents sensitive data from being accidentally committed to source control.

## Setting Up Environment Variables

### 1. Create Environment Variables

For each Supabase project profile, set these environment variables:

```bash
# For a profile named "Findry"
export SUPABASE_FINDRY_URL="https://your-project-ref.supabase.co"
export SUPABASE_FINDRY_ANON_KEY="eyJhbGciOiJIUzI1NiIs..."
export SUPABASE_FINDRY_SERVICE_KEY="eyJhbGciOiJIUzI1NiIs..."

# For a profile named "Production"
export SUPABASE_PRODUCTION_URL="https://prod-ref.supabase.co"  
export SUPABASE_PRODUCTION_ANON_KEY="eyJhbGciOiJIUzI1NiIs..."
export SUPABASE_PRODUCTION_SERVICE_KEY="eyJhbGciOiJIUzI1NiIs..."
```

### 2. Environment Variable Naming Convention

The naming pattern is: `SUPABASE_{PROFILE_NAME}_{CREDENTIAL_TYPE}`

- **Profile Name**: Uppercase version of your profile name
- **Credential Types**:
  - `URL` - Your project URL
  - `ANON_KEY` or `PUBLISHABLE_KEY` - Public key for client operations
  - `SERVICE_KEY` or `SECRET_KEY` - Private key for admin operations

### 3. Make Variables Persistent

#### Option A: Add to your shell profile
```bash
# Add to ~/.bashrc, ~/.zshrc, or similar
echo 'export SUPABASE_FINDRY_URL="https://your-project.supabase.co"' >> ~/.bashrc
echo 'export SUPABASE_FINDRY_ANON_KEY="your-anon-key"' >> ~/.bashrc
echo 'export SUPABASE_FINDRY_SERVICE_KEY="your-service-key"' >> ~/.bashrc
source ~/.bashrc
```

#### Option B: Create a .env file (recommended)
```bash
# Create .env file in your project directory
cat > .env << 'EOF'
SUPABASE_FINDRY_URL=https://your-project.supabase.co
SUPABASE_FINDRY_ANON_KEY=eyJhbGciOiJIUzI1NiIs...
SUPABASE_FINDRY_SERVICE_KEY=eyJhbGciOiJIUzI1NiIs...
EOF

# Load the .env file
set -o allexport
source .env
set +o allexport
```

**Important**: Add `.env` to your `.gitignore` file!

## Creating Environment Profiles

### Method 1: Using the GUI
1. Open Varchiver
2. Go to Supabase tools
3. Click "Manage Connections..."
4. Click "Add Env Profile"
5. Name your profile (e.g., "Findry")
6. Set the corresponding environment variables

### Method 2: Manual Configuration
Add to your `~/.config/varchiver/config.json`:

```json
{
  "supabase_connections": [
    {
      "name": "Findry",
      "url": "",
      "use_env": true,
      "publishable_key": "",
      "secret_key": "",
      "anon_key": "",
      "service_role_key": ""
    }
  ]
}
```

## Verification

Test your environment variables:
```bash
# Check if variables are set
echo $SUPABASE_FINDRY_URL
echo $SUPABASE_FINDRY_ANON_KEY
echo $SUPABASE_FINDRY_SERVICE_KEY
```

When you run Varchiver, you should see:
```
SupabaseConnector initialized for profile: Findry (from environment variables)
```

## Troubleshooting

### Profile Not Found
- Check environment variable names match exactly (case-sensitive)
- Ensure profile name in config matches environment variable prefix

### Connection Fails  
- Verify URL format: `https://your-project-ref.supabase.co`
- Check keys are complete and not truncated
- Confirm keys have necessary permissions in Supabase dashboard

### Variables Not Loading
- Restart terminal/application after setting variables
- Check if variables are exported: `export VARIABLE_NAME=value`
- Ensure .env file is sourced if using that method

## Security Benefits

✅ **No secrets in config files**: Credentials never touch the filesystem  
✅ **No accidental commits**: Environment variables can't be committed  
✅ **Easy rotation**: Change environment variables without touching config  
✅ **Per-environment setup**: Different credentials for dev/staging/prod  

## Best Practices

1. **Use descriptive profile names**: `PRODUCTION`, `STAGING`, `DEV`
2. **Rotate keys regularly**: Update environment variables periodically  
3. **Use least privilege**: Service keys should have minimal required permissions
4. **Document your setup**: Keep track of which projects use which profiles
5. **Use .env files**: Keep credentials organized and easy to manage