# Multi-Project Merge Guide

A comprehensive guide for safely merging complex Supabase projects using Varchiver's advanced merge workflow system.

## 🎯 Overview

This guide helps you merge two Supabase projects that may have:
- 100+ tables across multiple domains
- Shared critical dependencies (like `projects`, `users`, etc.)
- Complex foreign key relationships
- Mixed data states (empty schemas vs populated tables)

## 🚀 Quick Start

### 1. Analyze Your Projects

```bash
# Analyze development → production merge
python multi_project_merge_workflow.py analyze \
    --source-profile development \
    --target-profile production \
    --output merge_strategy_dev_to_prod \
    --verbose

# This generates:
# - merge_strategy_dev_to_prod_20241215_143022.json (machine readable)
# - merge_strategy_dev_to_prod_20241215_143022.yaml (human editable)
# - merge_strategy_dev_to_prod_summary_20241215_143022.md (executive summary)
```

### 2. Review the Analysis Results

The analysis will tell you:
- **Safety Score**: 0.0 (dangerous) to 1.0 (safe)
- **Total Conflicts**: How many tables exist in both projects
- **Critical Conflicts**: Tables with many dependencies (auto-detected)
- **Manual Resolution Required**: Conflicts needing human decisions
- **Estimated Duration**: Time needed for the merge

### 3. Test with Dry Run

```bash
# Test the merge strategy (no actual changes)
python multi_project_merge_workflow.py execute \
    --strategy merge_strategy_dev_to_prod_20241215_143022.yaml \
    --dry-run \
    --verbose

# Reviews what WOULD happen without making changes
```

### 4. Execute Production Merge

```bash
# Execute the actual merge (requires --confirmed)
python multi_project_merge_workflow.py execute \
    --strategy merge_strategy_dev_to_prod_20241215_143022.yaml \
    --confirmed \
    --verbose

# Creates backups and executes merge with rollback capabilities
```

## 📊 Understanding Analysis Results

### Safety Score Interpretation

| Score | Risk Level | Recommendation |
|-------|------------|----------------|
| 0.8-1.0 | Low | Safe to proceed with standard precautions |
| 0.6-0.7 | Medium | Proceed with extra validation and testing |
| 0.3-0.5 | High | Requires careful review and staging tests |
| 0.0-0.2 | Critical | Do not proceed without manual intervention |

### Conflict Types

**Data Conflicts**
- Both projects have data in the same table
- Resolution: Merge, prioritize source/target, or namespace

**Schema Mismatches**
- Same table name but different structures
- Resolution: Schema alignment or table renaming

**Critical Shared Dependencies**
- Tables that many other tables depend on (auto-detected based on foreign keys)
- Resolution: Manual strategy selection required

**Circular Dependencies**
- Tables that reference each other in cycles
- Resolution: Temporary constraint removal during merge

## 🔧 Resolution Strategies

The system offers multiple strategies for each conflict:

### 1. Union Merge (Recommended for most cases)
- Combines all records from both projects
- Handles ID conflicts with UUID remapping
- Updates all foreign key references
- **Best for**: Different datasets that should coexist

### 2. Source Priority
- Keeps source project data
- Migrates target dependencies to source records
- **Best for**: When source has the "correct" data

### 3. Target Priority
- Keeps target project data
- Migrates source dependencies to target records
- **Best for**: When target (production) should be preserved

### 4. Namespace Separation
- Adds source identifiers to distinguish records
- Creates views for backward compatibility
- **Best for**: When you need to keep datasets separate

### 5. Manual Review
- Pauses for human decision
- Generates detailed conflict reports
- **Best for**: Critical business data requiring human judgment

## 🛡️ Safety Features

### Automatic Backups
- Full database backup before any changes
- Timestamped and easily restorable
- Includes verification of backup integrity

### Dependency Mapping
- Analyzes all foreign key relationships
- Identifies circular dependencies
- Plans execution order to maintain referential integrity

### Rollback Capabilities
- Automatic rollback on failure
- Manual rollback procedures documented
- Validation queries to verify success

### Dry Run Mode
- Preview all changes without executing
- Validate strategy before production
- Estimate execution time and resources

## 📋 Pre-Merge Checklist

- [ ] **Environment Setup**
  - [ ] Verify both project connections work
  - [ ] Ensure sufficient database permissions
  - [ ] Check available disk space for backups

- [ ] **Analysis Review**
  - [ ] Run analysis and review safety score
  - [ ] Understand all critical conflicts
  - [ ] Review execution time estimate
  - [ ] Plan maintenance window if needed

- [ ] **Testing**
  - [ ] Run dry-run and review results
  - [ ] Test on staging environment if possible
  - [ ] Verify rollback procedures

- [ ] **Communication**
  - [ ] Notify stakeholders of maintenance window
  - [ ] Prepare communication for any downtime
  - [ ] Have emergency contacts ready

## 🔍 Troubleshooting

### Common Issues

**"Safety score too low"**
- Review critical conflicts manually
- Consider resolving conflicts in smaller batches
- Test individual table merges first

**"Manual resolution required"**
- Check which tables need manual decisions
- Use the generated conflict reports
- Resolve critical dependencies first

**"Connection failed"**
- Verify environment variables are correct
- Check database permissions
- Ensure network connectivity

**"Foreign key constraint violations"**
- Usually handled automatically by dependency analysis
- May indicate circular dependencies
- Check execution order in strategy file

### Emergency Procedures

**If merge fails mid-execution:**
1. Check logs for specific error
2. Automatic rollback should initiate
3. If rollback fails, restore from backup manually
4. Contact database administrator if needed

**If data appears corrupted:**
1. Stop all application access immediately
2. Run validation queries from the execution report
3. Compare row counts before/after merge
4. Restore from backup if integrity is compromised

## 🎯 Real-World Example

Let's say you have:
- **Development project**: 48 tables, 95 rows, includes contract management and civic systems
- **Production project**: 114 tables, 300+ rows, includes creative platform and game systems
- **Shared tables**: `projects`, `profiles`, `users` (critical dependencies)

### Step 1: Analysis
```bash
python multi_project_merge_workflow.py analyze \
    --source-profile development \
    --target-profile production \
    --output contract_platform_merge
```

**Results:**
- Safety Score: 0.65 (Medium Risk)
- Critical Conflicts: 3 (`projects`, `profiles`, `users`)
- Manual Resolution: `projects` table (affects 12 other tables)
- Estimated Duration: 45 minutes

### Step 2: Strategy Selection
The system recommends:
- `profiles`: Union merge (different user sets)
- `users`: Target priority (production users are canonical)
- `projects`: Manual review (business decision required)

### Step 3: Manual Resolution
For the `projects` table, you decide:
- Keep production projects (active business)
- Map development contracts to existing production projects
- Create new projects for unmapped development contracts

### Step 4: Execution
```bash
# Test first
python multi_project_merge_workflow.py execute \
    --strategy contract_platform_merge_20241215.yaml \
    --dry-run

# Execute when satisfied
python multi_project_merge_workflow.py execute \
    --strategy contract_platform_merge_20241215.yaml \
    --confirmed
```

## 🔧 Advanced Configuration

### Custom Resolution Strategies

You can add custom resolvers for specific table patterns:

```python
from varchiver.supamerge.shared_dependency_resolver import SharedDependencyResolver

resolver = SharedDependencyResolver()

def custom_projects_resolver(conflict_data, source_db, target_db):
    # Your custom logic here
    return {"success": True, "rows_merged": 42}

resolver.register_custom_resolver("projects", custom_projects_resolver)
```

### Batch Processing

For very large merges, process in batches:

```bash
# Process only specific schemas
python multi_project_merge_workflow.py analyze \
    --source-profile dev \
    --target-profile prod \
    --include-schemas public,auth

# Process specific table patterns
python multi_project_merge_workflow.py execute \
    --strategy merge_strategy.yaml \
    --table-pattern "contract_*"
```

## 📚 Additional Resources

- **API Documentation**: `/varchiver/supamerge/` module docs
- **Troubleshooting Logs**: `logs/multi_merge_*.log`
- **Example Configurations**: `/examples/supamerge_*.yaml`
- **Database Schema Analysis**: Use `dependency_analyzer.py` standalone

## 🤝 Getting Help

1. **Check the logs**: Always review the detailed logs first
2. **Use dry-run mode**: Test thoroughly before production
3. **Start small**: Try merging individual tables first
4. **Create issues**: Report bugs with logs and config files
5. **Community support**: Share anonymized examples for help

---

*This workflow has successfully handled merges of 100+ tables across multiple production systems. The key is thorough analysis, careful testing, and having solid rollback procedures.*

**Remember: When in doubt, dry-run first! 🧪**