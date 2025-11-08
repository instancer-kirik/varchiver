#!/usr/bin/env python3
"""
Test script for Supabase export functionality.
This script tests the export tools without requiring actual Supabase credentials.
"""

import os
import sys
import tempfile
import json
from pathlib import Path

# Add the varchiver module to the path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))


def test_imports():
    """Test if all required modules can be imported."""
    print("🧪 Testing imports...")

    try:
        from varchiver.supamerge.export import SupabaseExporter, ExportOptions

        print("✅ Supamerge export module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Supamerge export: {e}")
        return False

    try:
        from varchiver.supamerge.core import SourceConfig

        print("✅ Supamerge core module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Supamerge core: {e}")
        return False

    try:
        from varchiver.utils.env_manager import EnvManager

        print("✅ Environment manager imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import EnvManager: {e}")
        return False

    try:
        import psycopg2

        print("✅ psycopg2 imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import psycopg2: {e}")
        return False

    try:
        import yaml

        print("✅ PyYAML imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import PyYAML: {e}")
        return False

    return True


def test_env_manager():
    """Test the environment manager functionality."""
    print("\n🧪 Testing environment manager...")

    try:
        from varchiver.utils.env_manager import EnvManager

        env_manager = EnvManager()
        profiles = env_manager.get_all_supabase_profiles()

        print(f"✅ Environment manager created successfully")
        print(f"📊 Found {len(profiles)} Supabase profiles")

        if profiles:
            print("📋 Available profiles:")
            for name, details in profiles.items():
                url = details.get("url", "No URL")
                print(f"   • {name}: {url}")
        else:
            print("💡 No profiles found. This is normal if you haven't set up any yet.")

        return True

    except Exception as e:
        print(f"❌ Environment manager test failed: {e}")
        return False


def test_export_config_creation():
    """Test creating export configuration objects."""
    print("\n🧪 Testing export configuration creation...")

    try:
        from varchiver.supamerge.export import ExportOptions
        from varchiver.supamerge.core import SourceConfig

        # Test ExportOptions
        export_options = ExportOptions(
            output_format="json",
            include_data=True,
            include_schema=True,
            schemas=["public"],
        )
        print("✅ ExportOptions created successfully")
        print(f"   Format: {export_options.output_format}")
        print(f"   Schemas: {export_options.schemas}")

        # Test SourceConfig (with dummy data)
        source_config = SourceConfig(
            project_ref="test-project",
            db_url="postgresql://user:pass@localhost:5432/test",
            supabase_url="https://test-project.supabase.co",
            anon_key="dummy_anon_key",
            service_role_key="dummy_service_key",
        )
        print("✅ SourceConfig created successfully")
        print(f"   Project: {source_config.project_ref}")
        print(f"   URL: {source_config.supabase_url}")

        return True

    except Exception as e:
        print(f"❌ Configuration creation test failed: {e}")
        return False


def test_export_template_creation():
    """Test creating export configuration templates."""
    print("\n🧪 Testing export template creation...")

    try:
        from varchiver.supamerge.export import create_export_config_template

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            template_path = f.name

        # Create template
        create_export_config_template(template_path)

        # Check if file was created
        if Path(template_path).exists():
            with open(template_path, "r") as f:
                template_content = f.read()

            print("✅ Export template created successfully")
            print(f"📁 Template file: {template_path}")
            print("📝 Template preview:")
            print("   " + "\n   ".join(template_content.split("\n")[:10]))

            # Cleanup
            os.unlink(template_path)

            return True
        else:
            print("❌ Template file was not created")
            return False

    except Exception as e:
        print(f"❌ Template creation test failed: {e}")
        return False


def test_cli_script_syntax():
    """Test if the CLI scripts have valid syntax."""
    print("\n🧪 Testing CLI script syntax...")

    scripts_to_test = ["export_supabase.py", "examples/widget_export_example.py"]

    all_good = True

    for script_path in scripts_to_test:
        full_path = current_dir / script_path

        if not full_path.exists():
            print(f"⚠️  Script not found: {script_path}")
            continue

        try:
            with open(full_path, "r") as f:
                script_content = f.read()

            # Try to compile the script
            compile(script_content, str(full_path), "exec")
            print(f"✅ Script syntax OK: {script_path}")

        except SyntaxError as e:
            print(f"❌ Syntax error in {script_path}: {e}")
            all_good = False
        except Exception as e:
            print(f"⚠️  Could not test {script_path}: {e}")

    return all_good


def create_sample_env_file():
    """Create a sample .env file template for testing."""
    print("\n🧪 Creating sample environment file template...")

    try:
        sample_env_path = current_dir / ".env.export_example"

        sample_content = """# Sample Supabase Environment Variables for Export Testing
# Copy this to .env and fill in your actual values

# Example Project 1 (Widget 1)
SUPABASE_WIDGET1_URL=https://your-widget1-project.supabase.co
SUPABASE_WIDGET1_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.your_anon_key_here
SUPABASE_WIDGET1_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.your_service_key_here

# Example Project 2 (Widget 2)
SUPABASE_WIDGET2_URL=https://your-widget2-project.supabase.co
SUPABASE_WIDGET2_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.your_anon_key_here
SUPABASE_WIDGET2_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.your_service_key_here

# How to find your keys:
# 1. Go to your Supabase project dashboard
# 2. Settings → API
# 3. Copy the Project URL, anon key, and service_role key
"""

        with open(sample_env_path, "w") as f:
            f.write(sample_content)

        print(f"✅ Sample environment file created: {sample_env_path}")
        print("💡 Copy this to .env and fill in your actual Supabase credentials")

        return True

    except Exception as e:
        print(f"❌ Failed to create sample env file: {e}")
        return False


def show_usage_examples():
    """Show usage examples for the export tools."""
    print("\n📖 Usage Examples:")
    print()
    print("1. List available Supabase profiles:")
    print("   uv run python export_supabase.py --list-profiles")
    print()
    print("2. Export a project as PostgreSQL dump:")
    print("   uv run python export_supabase.py --profile myproject")
    print()
    print("3. Export as JSON for analysis:")
    print("   uv run python export_supabase.py --profile widget1 --format json")
    print()
    print("4. Compare two widget projects:")
    print(
        "   uv run python examples/widget_export_example.py --compare widget1 widget2"
    )
    print()
    print("5. Prepare widget merge:")
    print(
        "   uv run python examples/widget_export_example.py --prepare-merge widget1 widget2"
    )
    print()
    print("6. Use Supamerge CLI directly:")
    print("   uv run supamerge export --from-env WIDGET1 --format dump")


def main():
    """Run all tests."""
    print("🚀 Testing Supabase Export Functionality")
    print("=" * 50)

    tests = [
        ("Import Tests", test_imports),
        ("Environment Manager", test_env_manager),
        ("Configuration Creation", test_export_config_creation),
        ("Template Creation", test_export_template_creation),
        ("Script Syntax", test_cli_script_syntax),
        ("Sample Environment File", create_sample_env_file),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print(f"\n🎯 {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Export functionality is ready to use.")
        show_usage_examples()
    else:
        print("⚠️  Some tests failed. Check the output above for details.")

        if passed > 0:
            print("\n💡 Partial functionality may still be available.")
            print("   Try running: uv run python export_supabase.py --list-profiles")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
