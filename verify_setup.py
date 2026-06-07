#!/usr/bin/env python3
"""
Configuration and Connection Verification Script
Tests all components to ensure the application is properly configured.
"""

import sys
import os
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_banner():
    """Print welcome banner."""
    print("\n" + "="*70)
    print("Instagram AI Analyzer - Configuration Verification")
    print("="*70 + "\n")


def test_env_file():
    """Test if .env file exists and is readable."""
    print("📋 Test 1: .env File")
    print("-" * 70)
    
    env_path = Path(".env")
    
    if not env_path.exists():
        print("⚠️  .env file not found")
        print("   Create one by copying .env.example")
        return False
    
    print("✅ .env file found")
    
    try:
        with open(env_path, 'r') as f:
            content = f.read()
        print(f"✅ .env file readable ({len(content)} bytes)")
        return True
    except Exception as e:
        print(f"❌ Error reading .env file: {e}")
        return False


def test_config_loading():
    """Test if configuration loads successfully."""
    print("\n📋 Test 2: Configuration Loading")
    print("-" * 70)
    
    try:
        from config.settings import settings
        print("✅ Configuration loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return False


def test_environment_variables():
    """Test if required environment variables are set."""
    print("\n📋 Test 3: Environment Variables")
    print("-" * 70)
    
    try:
        from config.settings import settings
        
        all_ok = True
        
        # Check Graph API credentials
        if settings.INSTAGRAM_ACCESS_TOKEN:
            token_preview = settings.INSTAGRAM_ACCESS_TOKEN[:15] + "..."
            print(f"✅ INSTAGRAM_ACCESS_TOKEN set ({token_preview})")
        else:
            print("⚠️  INSTAGRAM_ACCESS_TOKEN not set")
        
        if settings.INSTAGRAM_BUSINESS_ACCOUNT_ID:
            print(f"✅ INSTAGRAM_BUSINESS_ACCOUNT_ID set ({settings.INSTAGRAM_BUSINESS_ACCOUNT_ID})")
        else:
            print("⚠️  INSTAGRAM_BUSINESS_ACCOUNT_ID not set")
        
        # Check legacy credentials as fallback
        if not (settings.INSTAGRAM_ACCESS_TOKEN and settings.INSTAGRAM_BUSINESS_ACCOUNT_ID):
            if settings.INSTAGRAM_USERNAME:
                print(f"✅ INSTAGRAM_USERNAME set (legacy: {settings.INSTAGRAM_USERNAME})")
            else:
                print("❌ No Instagram credentials found (Graph API or legacy)")
                all_ok = False
            
            if settings.INSTAGRAM_PASSWORD:
                print(f"✅ INSTAGRAM_PASSWORD set (legacy: ***)")
            else:
                print("❌ No Instagram password found")
                all_ok = False
        
        # Check Gemini
        if settings.GEMINI_API_KEY:
            key_preview = settings.GEMINI_API_KEY[:10] + "..."
            print(f"✅ GEMINI_API_KEY set ({key_preview})")
        else:
            print("❌ GEMINI_API_KEY not set")
            all_ok = False
        
        print(f"✅ GEMINI_MODEL: {settings.GEMINI_MODEL}")
        
        return all_ok
    except Exception as e:
        print(f"❌ Error checking environment variables: {e}")
        return False


def test_dependencies():
    """Test if all required dependencies are installed."""
    print("\n📋 Test 4: Python Dependencies")
    print("-" * 70)
    
    required = {
        'flask': 'Flask',
        'requests': 'requests',
        'google': 'google-genai',
        'dotenv': 'python-dotenv',
    }
    
    all_ok = True
    
    for module, package in required.items():
        try:
            __import__(module)
            print(f"✅ {package} is installed")
        except ImportError:
            print(f"❌ {package} is NOT installed")
            all_ok = False
    
    # Optional: Check for instagrapi (should not be needed anymore)
    try:
        __import__('instagrapi')
        print("⚠️  instagrapi is installed (legacy, no longer needed)")
    except ImportError:
        print("✅ instagrapi not installed (using Graph API)")
    
    return all_ok


def test_graph_api_connection():
    """Test connection to Graph API."""
    print("\n📋 Test 5: Graph API Connection")
    print("-" * 70)
    
    try:
        from config.settings import settings
        
        if not settings.INSTAGRAM_ACCESS_TOKEN:
            print("⚠️  Skipping (Graph API credentials not configured)")
            return False
        
        import requests
        
        print("🔗 Testing Graph API connection...")
        
        response = requests.get(
            "https://graph.instagram.com/v18.0/me",
            params={
                'fields': 'id,username,name',
                'access_token': settings.INSTAGRAM_ACCESS_TOKEN
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Graph API connection successful")
            print(f"   User: {data.get('name', 'Unknown')}")
            print(f"   Username: {data.get('username', 'Unknown')}")
            return True
        else:
            error = response.json()
            print(f"❌ Graph API returned error: {error.get('error', {}).get('message', 'Unknown')}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Graph API request timed out")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Graph API (check internet connection)")
        return False
    except Exception as e:
        print(f"❌ Error testing Graph API: {e}")
        return False


def test_gemini_connection():
    """Test connection to Gemini API."""
    print("\n📋 Test 6: Gemini API Connection")
    print("-" * 70)
    
    try:
        from config.settings import settings
        
        if not settings.GEMINI_API_KEY:
            print("⚠️  Skipping (Gemini API key not configured)")
            return False
        
        import google.generativeai as genai
        
        print("🔗 Testing Gemini API connection...")
        
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        
        # Test with a simple prompt
        response = model.generate_content(
            "Say 'Hello' in exactly one word.",
            generation_config={"max_output_tokens": 10}
        )
        
        if response.text:
            print(f"✅ Gemini API connection successful")
            print(f"   Model: {settings.GEMINI_MODEL}")
            print(f"   Response: {response.text[:50]}")
            return True
        else:
            print(f"❌ Gemini API returned empty response")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Gemini API: {e}")
        return False


def test_adapter_import():
    """Test if adapters can be imported."""
    print("\n📋 Test 7: Adapter Imports")
    print("-" * 70)
    
    try:
        from core.graph_api_adapter import GraphAPIAdapter
        print("✅ GraphAPIAdapter imported successfully")
    except Exception as e:
        print(f"❌ Error importing GraphAPIAdapter: {e}")
        return False
    
    try:
        from core.instagrapi_adapter import InstagrapiAdapter
        print("✅ InstagrapiAdapter available (legacy fallback)")
    except Exception as e:
        print(f"⚠️  InstagrapiAdapter import failed (expected if instagrapi not installed): {e}")
    
    try:
        from core.summarizer import CommentSummarizer
        print("✅ CommentSummarizer imported successfully")
    except Exception as e:
        print(f"❌ Error importing CommentSummarizer: {e}")
        return False
    
    return True


def test_models():
    """Test if data models can be imported."""
    print("\n📋 Test 8: Data Models")
    print("-" * 70)
    
    try:
        from models.post import Post, PostInfo
        print("✅ Post models imported successfully")
        
        from models.comment import Comment, CommentThread
        print("✅ Comment models imported successfully")
        
        from models.summary import SummaryResult
        print("✅ Summary model imported successfully")
        
        return True
    except Exception as e:
        print(f"❌ Error importing models: {e}")
        return False


def print_summary(results):
    """Print summary of all tests."""
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    tests = [
        ("ENV File", results.get("env", False)),
        ("Configuration", results.get("config", False)),
        ("Environment Variables", results.get("env_vars", False)),
        ("Dependencies", results.get("deps", False)),
        ("Graph API Connection", results.get("graph_api", False)),
        ("Gemini API Connection", results.get("gemini", False)),
        ("Adapter Imports", results.get("adapters", False)),
        ("Data Models", results.get("models", False)),
    ]
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    for name, result in tests:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    print("\n" + "="*70)
    print(f"Result: {passed}/{total} tests passed")
    print("="*70)
    
    if passed == total:
        print("\n🎉 All tests passed! Your application is ready to use.")
        print("\nNext steps:")
        print("   1. Run: python main.py")
        print("   2. Open: http://localhost:5000")
        print("   3. Enter an Instagram post URL to analyze")
        return 0
    elif passed >= total - 2:
        print("\n⚠️  Some tests failed. Please review the errors above.")
        print("\nFor detailed setup instructions, see README_MIGRATION.md")
        return 1
    else:
        print("\n❌ Multiple tests failed. Please resolve the issues above.")
        print("\nFor detailed setup instructions, see README_MIGRATION.md")
        return 1


def main():
    """Run all tests."""
    print_banner()
    
    results = {
        "env": test_env_file(),
        "config": test_config_loading(),
        "env_vars": test_environment_variables(),
        "deps": test_dependencies(),
        "graph_api": test_graph_api_connection(),
        "gemini": test_gemini_connection(),
        "adapters": test_adapter_import(),
        "models": test_models(),
    }
    
    return print_summary(results)


if __name__ == '__main__':
    sys.exit(main())
