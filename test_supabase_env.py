#!/usr/bin/env python3
"""Test script to verify Supabase environment integration."""

import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from varchiver.utils.env_manager import EnvManager
from varchiver.utils.supabase_connector import SupabaseConnector, get_supabase_connector
from varchiver.utils.config import Config


def test_env_manager():
    """Test the EnvManager functionality."""
    print("🧪 Testing EnvManager...")
    print("-" * 50)

    try:
        env_manager = EnvManager()
        print(f"✅ EnvManager initialized")
        print(f"   Environment file: {env_manager.get_env_file_path()}")
        print(f"   File exists: {env_manager.get_env_file_path().exists()}")

        # Test profile detection
        profiles = env_manager.get_all_supabase_profiles()
        print(f"   Detected profiles: {profiles}")

        # Test profile validation for detected profiles
        for profile in profiles:
            is_valid, missing = env_manager.validate_profile_credentials(profile)
            status = "✅ Valid" if is_valid else f"❌ Missing: {', '.join(missing)}"
            print(f"   Profile '{profile}': {status}")

            # Show credential preview
            env_vars = env_manager.get_env_vars_for_profile(profile)
            for cred_type, value in env_vars.items():
                if value:
                    if cred_type == "url":
                        preview = value
                    else:
                        preview = (
                            f"{'*' * 20}...{value[-4:] if len(value) > 4 else '****'}"
                        )
                    print(f"     {cred_type}: {preview}")
                else:
                    print(f"     {cred_type}: (not set)")

        return True

    except Exception as e:
        print(f"❌ EnvManager test failed: {e}")
        return False


def test_config_integration():
    """Test Config integration with profiles."""
    print("\n🧪 Testing Config Integration...")
    print("-" * 50)

    try:
        config = Config()

        # Get configured profiles
        profiles = config.get_supabase_connections()
        print(f"✅ Config loaded")
        print(f"   Configured profiles: {len(profiles)}")

        for profile in profiles:
            name = profile.get("name", "Unknown")
            use_env = profile.get("use_env", False)
            source = "environment" if use_env else "direct config"
            print(f"   Profile '{name}': {source}")

        # Get active profile
        active_name = config.get_active_supabase_connection_name()
        active_profile = config.get_active_supabase_connection()

        print(f"   Active profile: {active_name or 'None'}")
        if active_profile:
            print(f"   Uses environment: {active_profile.get('use_env', False)}")

        return True

    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False


def test_supabase_connector():
    """Test SupabaseConnector functionality."""
    print("\n🧪 Testing SupabaseConnector...")
    print("-" * 50)

    try:
        connector = SupabaseConnector()
        print(f"✅ SupabaseConnector initialized")

        # Get profile info
        profile_info = connector.get_active_profile_info()
        print(f"   Active profile: {profile_info.get('name', 'None')}")
        print(f"   Source: {profile_info.get('source', 'N/A')}")
        print(f"   Has client: {profile_info.get('has_client', False)}")
        print(f"   Has service client: {profile_info.get('has_service_client', False)}")

        # Show credential status
        credentials = profile_info.get("credentials", {})
        for cred_type, has_cred in credentials.items():
            status = "✅" if has_cred else "❌"
            print(f"   {cred_type}: {status}")

        # Test connection if we have credentials
        client = connector.get_client()
        if client:
            print("   Testing connection...")
            success, message = connector.test_connection()
            status = "✅" if success else "❌"
            print(f"   Connection test: {status} {message}")

            # Test service client if available
            service_client = connector.get_service_client()
            if service_client:
                print("   Testing service connection...")
                success, message = connector.test_connection(use_service_key=True)
                status = "✅" if success else "❌"
                print(f"   Service connection test: {status} {message}")
        else:
            print("   ⚠️  No client available - check configuration")

        return True

    except Exception as e:
        print(f"❌ SupabaseConnector test failed: {e}")
        return False


def test_global_connector():
    """Test the global connector functions."""
    print("\n🧪 Testing Global Connector Functions...")
    print("-" * 50)

    try:
        from varchiver.utils.supabase_connector import (
            get_supabase_client,
            get_supabase_service_client,
            refresh_supabase_connection,
        )

        print("✅ Import successful")

        # Test global client access
        client = get_supabase_client()
        print(f"   Global client: {'Available' if client else 'Not available'}")

        service_client = get_supabase_service_client()
        print(
            f"   Global service client: {'Available' if service_client else 'Not available'}"
        )

        # Test refresh
        print("   Testing connection refresh...")
        refresh_supabase_connection()
        print("   ✅ Refresh completed")

        return True

    except Exception as e:
        print(f"❌ Global connector test failed: {e}")
        return False


def show_debug_info():
    """Show detailed debug information."""
    print("\n🔍 Debug Information...")
    print("-" * 50)

    try:
        connector = get_supabase_connector()
        debug_info = connector.get_connection_debug_info()

        print("Debug Info:")
        for key, value in debug_info.items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for sub_key, sub_value in value.items():
                    print(f"    {sub_key}: {sub_value}")
            else:
                print(f"  {key}: {value}")

    except Exception as e:
        print(f"❌ Debug info failed: {e}")


def show_recommendations():
    """Show setup recommendations."""
    print("\n💡 Setup Recommendations...")
    print("-" * 50)

    env_manager = EnvManager()
    env_path = env_manager.get_env_file_path()

    if not env_path.exists():
        print("📝 No .env file found. To set up:")
        print("   1. Copy .env.example to .env")
        print("   2. Fill in your Supabase credentials")
        print("   3. Use the Supabase Configuration Manager to create profiles")

    profiles = env_manager.get_all_supabase_profiles()
    if not profiles:
        print("📝 No environment profiles detected. To create one:")
        print("   1. Open Varchiver")
        print("   2. Go to Supabase tools -> Manage Connections")
        print("   3. Click 'Add Environment Profile'")
        print("   4. Fill in your credentials and save")

    config = Config()
    active_profile = config.get_active_supabase_connection_name()
    if not active_profile:
        print("📝 No active Supabase profile set.")
        print("   1. Open Supabase Configuration Manager")
        print("   2. Select a profile from the 'Active Profile' dropdown")
        print("   3. Click OK to save")


def main():
    """Run all tests."""
    print("🚀 Supabase Environment Integration Test")
    print("=" * 60)

    tests = [
        test_env_manager,
        test_config_integration,
        test_supabase_connector,
        test_global_connector,
    ]

    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test_func.__name__} crashed: {e}")
            results.append(False)

    # Show debug info
    show_debug_info()

    # Show recommendations
    show_recommendations()

    # Summary
    print(f"\n📊 Test Summary")
    print("-" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
