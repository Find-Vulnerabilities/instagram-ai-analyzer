"""
Configuration management module.
Loads environment variables and provides application settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv


env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class Settings:
    """Application configuration settings."""
    
    # Instagram Graph API settings (Official API)
    INSTAGRAM_ACCESS_TOKEN: str = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
    INSTAGRAM_BUSINESS_ACCOUNT_ID: str = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")
    
    # Legacy settings (for backward compatibility, deprecated)
    INSTAGRAM_USERNAME: str = os.getenv("INSTAGRAM_USERNAME", "")
    INSTAGRAM_PASSWORD: str = os.getenv("INSTAGRAM_PASSWORD", "")
    
    # Gemini AI settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
   
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    
    # Application settings
    FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    FLASK_PORT: int = int(os.getenv("FLASK_PORT", "5000"))
    SUMMARY_MAX_LENGTH: int = int(os.getenv("SUMMARY_MAX_LENGTH", "2000"))
    
    # Instagram API limits
    MAX_COMMENTS_PER_POST: int = 100
    MAX_POSTS_TO_ANALYZE: int = 10
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that required settings are configured."""
        valid = True
        
        def color_text(text, color_code):
            try:
                return f"\033[{color_code}m{text}\033[0m"
            except:
                return text
        
        print("\n🔍 Validating Configuration...")
        
        if not cls.GEMINI_API_KEY:
            print(color_text("   ❌ ERROR: GEMINI_API_KEY not set. AI features will not work.", "91"))
            valid = False
        else:
            key_preview = cls.GEMINI_API_KEY[:8] + "..." if len(cls.GEMINI_API_KEY) > 8 else "***"
            print(color_text(f"   ✅ GEMINI_API_KEY is configured ({key_preview})", "92"))
        
        # Check for Graph API configuration (preferred)
        if cls.INSTAGRAM_ACCESS_TOKEN and cls.INSTAGRAM_BUSINESS_ACCOUNT_ID:
            token_preview = cls.INSTAGRAM_ACCESS_TOKEN[:8] + "..." if len(cls.INSTAGRAM_ACCESS_TOKEN) > 8 else "***"
            print(color_text(f"   ✅ Instagram Graph API configured ({token_preview})", "92"))
        # Fallback to legacy configuration
        elif cls.INSTAGRAM_USERNAME and cls.INSTAGRAM_PASSWORD:
            print(color_text(f"   ⚠️  WARNING: Using legacy Instagram credentials (deprecated). ", "93"))
            print(color_text(f"      Please migrate to Graph API with INSTAGRAM_ACCESS_TOKEN.", "93"))
        else:
            print(color_text("   ❌ ERROR: Instagram authentication not configured. ", "91"))
            print(color_text("      Please set either INSTAGRAM_ACCESS_TOKEN (preferred) ", "91"))
            print(color_text("      or INSTAGRAM_USERNAME/PASSWORD (legacy).", "91"))
            valid = False
        
        print(f"   ✅ Summary max length: {cls.SUMMARY_MAX_LENGTH}")
        print(f"   ✅ Flask debug mode: {'ON' if cls.FLASK_DEBUG else 'OFF'}")
        print(f"   ✅ Flask port: {cls.FLASK_PORT}")
        print(f"   ✅ Gemini model: {cls.GEMINI_MODEL}")
        
        return valid
    
    @classmethod
    def get_status_dict(cls) -> dict:
        """Returns a dictionary of configuration status for use in API responses."""
        return {
            "gemini_configured": bool(cls.GEMINI_API_KEY),
            "instagram_graph_api_configured": bool(cls.INSTAGRAM_ACCESS_TOKEN and cls.INSTAGRAM_BUSINESS_ACCOUNT_ID),
            "instagram_legacy_configured": bool(cls.INSTAGRAM_USERNAME and cls.INSTAGRAM_PASSWORD),
            "flask_debug": cls.FLASK_DEBUG,
            "flask_port": cls.FLASK_PORT,
            "summary_max_length": cls.SUMMARY_MAX_LENGTH,
            "gemini_model": cls.GEMINI_MODEL,
        }


settings = Settings()