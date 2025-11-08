#!/usr/bin/env python3
"""Test script to verify .env file updating behavior."""

import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from varchiver.utils.env_manager import EnvManager


def test_env_file_creation_and_update():
    """Test creating and updating .env file."""
    print("🧪 Testing .env file creation and updates...")
    print("-" * 60)

    # Initialize env manager
    env_manager = EnvManager()
    env_path = env_manager.get_env_file_path()

    print(f"Environment file path: {env_path}")
    print(f"File exists: {env_path.exists()}")

    # Show current content
    if env_path.exists():
        content = env_path.read_text()
        print(f"\nCurrent .env content ({len(content)} chars):")
        print("=" * 40)
        print(content)
        print("=" * 40)

    # Test setting credentials for a test profile
    test_profile = "TestProfile"
    test_credentials = {
        "url": "https://test-project.supabase.co",
        "anon_key": "eyJtest_anon_key_here",
        "service_key": "eyJtest_service_key_here",
    }

    print(f"\n📝 Setting credentials for profile: {test_profile}")
    env_manager.set_env_vars_for_profile(test_profile, test_credentials)

    # Show updated content
    if env_path.exists():
        content = env_path.read_text()
        print(f"\nUpdated .env content ({len(content)} chars):")
        print("=" * 40)
        print(content)
        print("=" * 40)

    # Verify the credentials were set correctly
    print(f"\n🔍 Verifying credentials for profile: {test_profile}")
    retrieved_credentials = env_manager.get_env_vars_for_profile(test_profile)

    for cred_type, expected_value in test_credentials.items():
        actual_value = retrieved_credentials.get(cred_type)
        match = "✅" if actual_value == expected_value else "❌"
        print(
            f"  {cred_type}: {match} Expected: {expected_value[:20]}... Got: {actual_value[:20] if actual_value else 'None'}..."
        )

    # Test updating existing credentials
    print(f"\n📝 Updating credentials for existing profile: {test_profile}")
    updated_credentials = {
        "url": "https://updated-project.supabase.co",
        "anon_key": "eyJupdated_anon_key_here",
        "service_key": "eyJupdated_service_key_here",
    }

    env_manager.set_env_vars_for_profile(test_profile, updated_credentials)

    # Show final content
    if env_path.exists():
        content = env_path.read_text()
        print(f"\nFinal .env content ({len(content)} chars):")
        print("=" * 40)
        print(content)
        print("=" * 40)

    # Verify updated credentials
    print(f"\n🔍 Verifying updated credentials for profile: {test_profile}")
    final_credentials = env_manager.get_env_vars_for_profile(test_profile)

    for cred_type, expected_value in updated_credentials.items():
        actual_value = final_credentials.get(cred_type)
        match = "✅" if actual_value == expected_value else "❌"
        print(
            f"  {cred_type}: {match} Expected: {expected_value[:20]}... Got: {actual_value[:20] if actual_value else 'None'}..."
        )

    # Test adding a second profile
    print(f"\n📝 Adding second profile: Production")
    prod_credentials = {
        "url": "https://prod-project.supabase.co",
        "anon_key": "eyJprod_anon_key_here",
        "service_key": "eyJprod_service_key_here",
    }

    env_manager.set_env_vars_for_profile("Production", prod_credentials)

    # Show final state
    if env_path.exists():
        content = env_path.read_text()
        print(f"\nFinal .env with multiple profiles ({len(content)} chars):")
        print("=" * 40)
        print(content)
        print("=" * 40)

    # List all detected profiles
    all_profiles = env_manager.get_all_supabase_profiles()
    print(f"\n📋 All detected profiles: {all_profiles}")

    # Clean up test profiles
    print(f"\n🧹 Cleaning up test profiles...")
    env_manager.remove_profile_env_vars("TestProfile")
    env_manager.remove_profile_env_vars("Production")

    # Show cleaned content
    if env_path.exists():
        content = env_path.read_text()
        print(f"\nCleaned .env content ({len(content)} chars):")
        print("=" * 40)
        print(content)
        print("=" * 40)

    print("\n✅ .env file update test completed!")


def test_env_permissions():
    """Test if we can write to the .env file location."""
    print("\n🔒 Testing file permissions...")
    print("-" * 60)

    env_manager = EnvManager()
    env_path = env_manager.get_env_file_path()

    print(f"Environment file path: {env_path}")
    print(f"Parent directory: {env_path.parent}")
    print(f"Parent exists: {env_path.parent.exists()}")
    print(f"Parent is writable: {os.access(env_path.parent, os.W_OK)}")

    if env_path.exists():
        print(f"File is readable: {os.access(env_path, os.R_OK)}")
        print(f"File is writable: {os.access(env_path, os.W_OK)}")

        # Show file stats
        stat = env_path.stat()
        print(f"File size: {stat.st_size} bytes")
        print(f"File mode: {oct(stat.st_mode)}")
        print(f"File owner: {stat.st_uid}")
    else:
        print("File doesn't exist - will be created")

    # Test creating a backup
    try:
        backup_path = env_manager.backup_env_file()
        if backup_path:
            print(f"✅ Backup created: {backup_path}")
            backup_path.unlink()  # Clean up
        else:
            print("ℹ️  No backup needed (file doesn't exist)")
    except Exception as e:
        print(f"❌ Backup failed: {e}")


def main():
    """Run all tests."""
    print("🚀 Environment File Update Test")
    print("=" * 60)

    try:
        test_env_permissions()
        test_env_file_creation_and_update()

        print("\n🎉 All tests completed successfully!")
        return 0

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
