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
    
    # Instagram credentials (instagrapi)
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
        
        if not cls.INSTAGRAM_USERNAME:
            print(color_text("   ❌ ERROR: INSTAGRAM_USERNAME not set", "91"))
            valid = False
        else:
            print(color_text(f"   ✅ INSTAGRAM_USERNAME: {cls.INSTAGRAM_USERNAME}", "92"))
        
        if not cls.INSTAGRAM_PASSWORD:
            print(color_text("   ❌ ERROR: INSTAGRAM_PASSWORD not set", "91"))
            valid = False
        else:
            print(color_text("   ✅ INSTAGRAM_PASSWORD is set", "92"))
        
        if not cls.GEMINI_API_KEY:
            print(color_text("   ❌ ERROR: GEMINI_API_KEY not set", "91"))
            valid = False
        else:
            key_preview = cls.GEMINI_API_KEY[:8] + "..." if len(cls.GEMINI_API_KEY) > 8 else "***"
            print(color_text(f"   ✅ GEMINI_API_KEY is configured ({key_preview})", "92"))
        
        print(f"   ✅ Summary max length: {cls.SUMMARY_MAX_LENGTH}")
        print(f"   ✅ Flask debug mode: {'ON' if cls.FLASK_DEBUG else 'OFF'}")
        print(f"   ✅ Flask port: {cls.FLASK_PORT}")
        print(f"   ✅ Gemini model: {cls.GEMINI_MODEL}")
        
        return valid


settings = Settings()