# Supamerge Security & Credential Handling Guide

This document outlines how Supamerge handles sensitive credentials and ensures secure migration operations.

## 🔐 Security Principles

**1. No Hardcoded Credentials**
- No database passwords, API keys, or tokens are stored in source code
- All examples use placeholder values or environment variables
- Real credentials are only stored in encrypted configuration files

**2. Secure Storage**
- Credentials are stored in `~/.config/varchiver/config.json` with appropriate file permissions
- Sensitive fields are masked in the GUI (password fields)
- Configuration supports both direct storage and environment variable references

**3. Multiple Security Layers**
- Environment variables for CI/CD and automated deployments
- Local encrypted config for desktop usage
- Option to use temporary credentials that expire

## 🔑 Credential Types Supported

### Supabase API Keys
```
Publishable Key: sb_publishable_[key]  - Safe for client-side use
Secret Key:      sb_secret_[key]       - Server-side only, privileged access
```

### Legacy JWT Format (Still Supported)
```
Anon Key:        eyJhbGciOiJIUzI1NiIs...  - Public, RLS-protected
Service Role:    eyJ[full-jwt-token]...     - Bypasses RLS, admin access
```

## 📁 Where Credentials Are Stored

### Local Configuration File
```
~/.config/varchiver/config.json
```

**File Structure:**
```json
{
  "supabase_connections": [
    {
      "name": "My Project",
      "url": "https://project-ref.supabase.co",
      "anon_key": "eyJhbGciOiJIUzI1NiIs...",
      "service_role_key": "eyJhbGciOiJIUzI1NiIs..."
    }
  ],
  "active_supabase_connection_name": "My Project"
}
```

### Environment Variables (Recommended for Production)
```bash
# Source Project
export SOURCE_PROJECT_REF="your-source-ref"
export SOURCE_SUPABASE_URL="https://your-source.supabase.co"
export SOURCE_ANON_KEY="eyJhbGciOiJIUzI1NiIs..."
export SOURCE_SERVICE_KEY="eyJhbGciOiJIUzI1NiIs..."

# Target Project  
export TARGET_PROJECT_REF="your-target-ref"
export TARGET_SUPABASE_URL="https://your-target.supabase.co"
export TARGET_ANON_KEY="eyJhbGciOiJIUzI1NiIs..."
export TARGET_SERVICE_KEY="eyJhbGciOiJIUzI1NiIs..."
```

## 🛡️ Security Best Practices

### 1. Use Environment Variables for Production
```yaml
# In config files, reference environment variables:
source:
  db_url: "${SOURCE_DB_URL}"
  publishable_key: "${SOURCE_PUBLISHABLE_KEY}"
  secret_key: "${SOURCE_SECRET_KEY}"
```

### 2. Rotate Keys Regularly
- Generate new API keys periodically in Supabase Dashboard
- Update stored credentials when keys are rotated
- Revoke old keys after updating configurations

### 3. Use Least Privilege Principle
- Use publishable keys for read operations when possible
- Only use secret/service role keys for privileged operations
- Consider creating dedicated service accounts for migrations

### 4. Secure Database Passwords
- Never commit database passwords to version control
- Use environment variables or secure secret management
- Consider using connection pooling with temporary credentials

### 5. Network Security
- Run migrations from secure networks
- Use VPN when accessing production databases
- Consider IP allowlisting in Supabase settings

## 🔒 GUI Security Features

### Password Field Masking
- Secret keys are masked with `•••••` in input fields
- Database URLs with passwords are masked
- Anon/publishable keys remain visible (they're designed to be public)

### Connection Testing
- Test connections use temporary client instances
- No credentials are logged during connection tests
- Failed connection messages don't expose credential details

### Secure Form Handling
```python
# Example: How the GUI handles sensitive data
def _get_profile_from_form(self) -> dict:
    profile = {
        "name": self.name_input.text().strip(),
        "url": self.url_input.text().strip(),
        "db_url": self.db_url_input.text().strip(),  # Masked in UI
    }
    
    if self.api_format_combo.currentText() == "New Format":
        profile.update({
            "publishable_key": self.publishable_key_input.text().strip(),
            "secret_key": self.secret_key_input.text().strip(),  # Masked
        })
```

## 🚨 Security Warnings

### ❌ What NOT To Do
- Don't commit `.env` files with real credentials
- Don't share config files containing credentials
- Don't use production credentials in development
- Don't store service role keys in client applications
- Don't log or display full credential values

### ⚠️ Migration-Specific Risks
- Backup files may contain sensitive data - secure them properly
- Migration logs might contain schema information - review before sharing
- Failed migrations may leave target database in inconsistent state
- Always test migrations in non-production environments first

## 🔍 Credential Validation

### Required for Each Project
```
✅ Project URL (https://[ref].supabase.co)
✅ API Keys (anon_key and service_role_key)
```

### Validation Checks
- URL format validation
- API key format validation (sb_publishable_/sb_secret_ or JWT format)
- Database connection testing
- Permission verification

## 🛠️ Troubleshooting Security Issues

### "Connection Failed" Errors
1. Verify API keys are correctly copied (no extra spaces)
2. Check that database password is correct
3. Ensure network connectivity to Supabase
4. Verify project URL matches your actual project

### "Permission Denied" Errors  
1. Confirm secret/service role key has sufficient permissions
2. Check RLS policies aren't blocking migration operations
3. Verify database user has schema modification rights

### "Invalid API Key" Errors
1. Ensure using correct key format (new vs legacy)
2. Check if keys have been rotated/expired
3. Verify key corresponds to correct project

## 📋 Security Checklist

Before running migrations:

- [ ] Credentials stored securely (not hardcoded)
- [ ] Using environment variables for sensitive deployments
- [ ] API keys have appropriate permissions
- [ ] Database backup created and secured
- [ ] Migration tested in non-production environment
- [ ] Network connection is secure
- [ ] Logs will be handled securely
- [ ] Recovery plan prepared in case of issues

## 🔄 Key Rotation Process

1. **Generate new keys** in Supabase Dashboard → Settings → API
2. **Update stored credentials** in Varchiver or environment variables
3. **Test connection** with new keys
4. **Run migration** with new keys
5. **Revoke old keys** in Supabase Dashboard
6. **Document the rotation** for audit purposes

## 📞 Support & Reporting Security Issues

If you discover security vulnerabilities in Supamerge:

1. **Do NOT** create public GitHub issues for security problems
2. **Do NOT** share credentials in support requests
3. **Do** report security issues privately to the maintainers
4. **Do** provide steps to reproduce (with placeholder credentials)

---

**Remember: Security is everyone's responsibility. Always err on the side of caution when handling production credentials.**