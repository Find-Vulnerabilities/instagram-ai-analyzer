#!/usr/bin/env python3
"""
Graph API Credentials Helper
Helps users obtain and validate Graph API credentials.
"""

import sys
import requests
import json
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
    print("Instagram AI Analyzer - Graph API Credentials Setup Helper")
    print("="*70 + "\n")


def print_step(step_num, title):
    """Print a numbered step."""
    print(f"\n📋 STEP {step_num}: {title}")
    print("-" * 70)


def validate_access_token(access_token: str) -> dict:
    """
    Validate an access token and retrieve account information.
    
    Args:
        access_token: Facebook access token
        
    Returns:
        dict: Account information or None if invalid
    """
    try:
        response = requests.get(
            "https://graph.instagram.com/v18.0/me",
            params={
                'fields': 'id,username,name,email',
                'access_token': access_token
            },
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            error_data = response.json()
            logger.error(f"Token validation failed: {error_data}")
            return None
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        return None


def get_business_accounts(access_token: str) -> list:
    """
    Get Instagram Business Account IDs connected to the token.
    
    Args:
        access_token: Facebook access token
        
    Returns:
        list: List of business accounts
    """
    try:
        response = requests.get(
            "https://graph.instagram.com/v18.0/me/accounts",
            params={
                'fields': 'id,name,instagram_business_account',
                'access_token': access_token
            },
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json().get('data', [])
        else:
            error_data = response.json()
            logger.error(f"Failed to fetch accounts: {error_data}")
            return []
    except Exception as e:
        logger.error(f"Error fetching accounts: {e}")
        return []


def step_1_generate_token():
    """Step 1: Guide user to generate access token."""
    print_step(1, "Generate Access Token from Facebook App")
    
    print("""
Follow these steps to generate your access token:

1. Visit: https://developers.facebook.com/apps/
   (or create a new app if you don't have one)

2. Select your app and go to: Settings > Basic
   Note down your:
   - App ID
   - App Secret

3. Go to: Tools > Graph API Explorer
   - Select your app from the dropdown
   - Click "Generate Access Token"
   - Select permissions:
     ✓ instagram_basic
     ✓ instagram_content_publishing
     ✓ pages_manage_posts
   - Accept and copy the token

4. For production, convert to long-lived token using:
   https://developers.facebook.com/docs/facebook-login/access-tokens/refreshing

This will give you a SHORT-LIVED token. For production use, 
follow Facebook's documentation to get a LONG-LIVED token 
(lasts ~60 days and can be refreshed).
""")
    
    token = input("\n🔑 Paste your access token here: ").strip()
    
    if not token:
        print("\n❌ No token provided. Exiting.")
        return None
    
    print("\n🔍 Validating token...")
    user_info = validate_access_token(token)
    
    if not user_info:
        print("❌ Invalid token. Please check and try again.")
        return None
    
    print(f"\n✅ Token validated!")
    print(f"   User: {user_info.get('name', 'Unknown')}")
    print(f"   Email: {user_info.get('email', 'N/A')}")
    print(f"   User ID: {user_info.get('id', 'Unknown')}")
    
    return token


def step_2_get_business_account(access_token: str):
    """Step 2: Get Instagram Business Account ID."""
    print_step(2, "Get Instagram Business Account ID")
    
    print("\n🔍 Fetching connected Instagram Business Accounts...")
    accounts = get_business_accounts(access_token)
    
    if not accounts:
        print("❌ No business accounts found.")
        print("\nPossible solutions:")
        print("1. Ensure your app has Instagram Graph API product added")
        print("2. Connect an Instagram Business Account to your Facebook Page")
        print("3. Check that your token has required permissions")
        print("\nVisit: https://developers.facebook.com/docs/instagram-api/get-started")
        return None
    
    print(f"\n✅ Found {len(accounts)} account(s):\n")
    
    for idx, account in enumerate(accounts, 1):
        print(f"   {idx}. Page: {account.get('name', 'Unknown')}")
        if 'instagram_business_account' in account:
            ig_account = account['instagram_business_account']
            print(f"      Instagram ID: {ig_account.get('id', 'N/A')}")
        else:
            print(f"      ⚠️  No Instagram Business Account linked")
    
    if len(accounts) == 1 and 'instagram_business_account' in accounts[0]:
        return accounts[0]['instagram_business_account']['id']
    
    choice = input("\n📌 Select account number (or 'q' to quit): ").strip()
    
    if choice.lower() == 'q':
        return None
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(accounts):
            account = accounts[idx]
            if 'instagram_business_account' in account:
                business_id = account['instagram_business_account']['id']
                print(f"\n✅ Selected Business Account ID: {business_id}")
                return business_id
            else:
                print("❌ This account has no Instagram Business Account linked.")
                return None
        else:
            print("❌ Invalid selection.")
            return None
    except ValueError:
        print("❌ Invalid input.")
        return None


def step_3_save_credentials(access_token: str, business_account_id: str):
    """Step 3: Save credentials to .env file."""
    print_step(3, "Save Credentials to .env")
    
    env_path = Path(".env")
    
    print(f"\n📁 .env file location: {env_path.absolute()}")
    
    # Read existing .env if it exists
    existing_content = ""
    if env_path.exists():
        with open(env_path, 'r') as f:
            existing_content = f.read()
    
    # Prepare new content
    new_lines = []
    
    # Remove old Graph API settings if they exist
    for line in existing_content.split('\n'):
        if not any(line.startswith(key) for key in [
            'INSTAGRAM_ACCESS_TOKEN',
            'INSTAGRAM_BUSINESS_ACCOUNT_ID',
        ]):
            new_lines.append(line)
    
    # Add new settings
    new_lines.extend([
        '',
        '# ============================================================',
        '# Instagram Graph API Configuration (Updated)',
        '# ============================================================',
        f'INSTAGRAM_ACCESS_TOKEN={access_token}',
        f'INSTAGRAM_BUSINESS_ACCOUNT_ID={business_account_id}',
    ])
    
    new_content = '\n'.join(new_lines).strip() + '\n'
    
    # Ask for confirmation
    print("\n📝 New .env content to be added:")
    print("-" * 70)
    print(f"INSTAGRAM_ACCESS_TOKEN={access_token[:20]}...")
    print(f"INSTAGRAM_BUSINESS_ACCOUNT_ID={business_account_id}")
    print("-" * 70)
    
    confirm = input("\n✅ Save to .env? (y/n): ").strip().lower()
    
    if confirm == 'y':
        with open(env_path, 'w') as f:
            f.write(new_content)
        print(f"\n✅ Credentials saved to .env")
        return True
    else:
        print("\n⏭️  Skipped. You can manually add these to your .env file:")
        print(f"   INSTAGRAM_ACCESS_TOKEN={access_token}")
        print(f"   INSTAGRAM_BUSINESS_ACCOUNT_ID={business_account_id}")
        return False


def step_4_verify_setup():
    """Step 4: Verify the setup."""
    print_step(4, "Verify Setup")
    
    try:
        from config.settings import settings
        
        print("\n🔍 Checking configuration...\n")
        
        if settings.INSTAGRAM_ACCESS_TOKEN and settings.INSTAGRAM_BUSINESS_ACCOUNT_ID:
            print("✅ Graph API credentials found!")
            print(f"   Token: {settings.INSTAGRAM_ACCESS_TOKEN[:20]}...")
            print(f"   Account ID: {settings.INSTAGRAM_BUSINESS_ACCOUNT_ID}")
            
            # Try to validate
            print("\n🔗 Testing connection...")
            user_info = validate_access_token(settings.INSTAGRAM_ACCESS_TOKEN)
            
            if user_info:
                print("✅ Connection successful!")
                return True
            else:
                print("❌ Connection failed. Check your token.")
                return False
        else:
            print("❌ Graph API credentials not found in .env")
            return False
    except Exception as e:
        logger.error(f"Error verifying setup: {e}")
        return False


def main():
    """Main function."""
    print_banner()
    
    # Step 1: Get token
    access_token = step_1_generate_token()
    if not access_token:
        print("\n❌ Setup aborted.")
        sys.exit(1)
    
    # Step 2: Get business account
    business_account_id = step_2_get_business_account(access_token)
    if not business_account_id:
        print("\n❌ Setup aborted.")
        sys.exit(1)
    
    # Step 3: Save credentials
    step_3_save_credentials(access_token, business_account_id)
    
    # Step 4: Verify
    if step_4_verify_setup():
        print("\n" + "="*70)
        print("✅ SUCCESS! Your credentials are set up correctly.")
        print("="*70)
        print("\n🚀 Next steps:")
        print("   1. Run: pip install -r requirements.txt")
        print("   2. Run: python main.py")
        print("\n📚 For more info, see README_MIGRATION.md")
        print("="*70 + "\n")
    else:
        print("\n❌ Verification failed. Please check your setup.")
        sys.exit(1)


if __name__ == '__main__':
    main()
