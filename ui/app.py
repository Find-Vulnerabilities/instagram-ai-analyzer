"""
Main Flask web application for Instagram AI Analyzer.
Provides a web interface for analyzing Instagram posts and their comments.
"""

import logging
import os
from typing import Optional

from flask import Flask, render_template, request, jsonify

from core.instagram_client import InstagramClientError
from core.graph_api_adapter import GraphAPIAdapter, get_business_account_id
from core.instagrapi_adapter import InstagrapiAdapter  # Legacy fallback
from config.settings import settings
from core.summarizer import CommentSummarizer
from models.summary import SummaryResult

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.FLASK_DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app():
    """
    Create and configure the Flask application.
    
    Returns:
        Flask: Configured Flask application instance
    """
    app = Flask(__name__,template_folder='.')
    app.config['SECRET_KEY'] = os.urandom(24)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
    
    # Initialize global components
    summarizer = None
    
    if settings.GEMINI_API_KEY:
        try:
            summarizer = CommentSummarizer()
            logger.info("Summarizer initialized with Gemini API")
        except Exception as e:
            logger.error(f"Failed to initialize summarizer: {e}")
    else:
        logger.warning("No Gemini API key found. AI features will be disabled.")
    
    @app.route('/')
    def index():
        """Render the main application interface."""
        return render_template('index.html')
    
    @app.route('/api/analyze', methods=['POST'])
    def analyze_post():
        """
        API endpoint to analyze an Instagram post.
        
        Expected JSON payload:
        {
            "post_url": "https://www.instagram.com/p/...",
            "comment_limit": 100,
            "include_replies": true
        }
        
        Returns:
            JSON response with analysis results
        """
        data = request.get_json()
        
        if not data or 'post_url' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing post_url parameter'
            }), 400
        
        post_url = data['post_url']
        comment_limit = min(data.get('comment_limit', 100), 500)
        include_replies = data.get('include_replies', True)
        
        # Validate Gemini availability
        if not summarizer:
            return jsonify({
                'success': False,
                'error': 'Gemini API is not configured. Please set GEMINI_API_KEY in .env file.'
            }), 503
        
        # Validate Instagram credentials
        instagram_client = None
        api_type = 'unknown'
        
        try:
            # Prefer Graph API if configured
            if settings.INSTAGRAM_ACCESS_TOKEN and settings.INSTAGRAM_BUSINESS_ACCOUNT_ID:
                logger.info("Initializing Graph API adapter...")
                instagram_client = GraphAPIAdapter(
                    settings.INSTAGRAM_ACCESS_TOKEN,
                    settings.INSTAGRAM_BUSINESS_ACCOUNT_ID
                )
                api_type = 'Graph API'
                logger.info("Successfully initialized Graph API adapter")
            
            # Fallback to legacy credentials
            elif settings.INSTAGRAM_USERNAME and settings.INSTAGRAM_PASSWORD:
                logger.warning("Using legacy Instagram credentials (instagrapi)")
                instagram_client = InstagrapiAdapter()
                api_type = 'instagrapi (legacy)'
                logger.info(f"Logging into Instagram as {settings.INSTAGRAM_USERNAME}")
                instagram_client.login(
                    settings.INSTAGRAM_USERNAME,
                    settings.INSTAGRAM_PASSWORD
                )
            
            else:
                return jsonify({
                    'success': False,
                    'error': 'Instagram credentials not configured. Please set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_BUSINESS_ACCOUNT_ID in .env file.'
                }), 503
            
            # Fetch post with comments
            logger.info(f"Fetching post: {post_url}")
            post = instagram_client.get_post_with_comments(
                post_url,
                comment_limit=comment_limit,
                include_replies=include_replies
            )
            
            logger.info(f"Fetched post by @{post.info.username} with {len(post.comments)} comments")
            
            # Generate AI summary
            logger.info("Generating AI summary...")
            summary = summarizer.summarize_post(post)
            
            # Prepare response
            response = {
                'success': summary.is_successful,
                'post': {
                    'username': post.info.username,
                    'caption': post.info.caption[:500] if post.info.caption else '',
                    'like_count': post.info.like_count,
                    'comment_count': post.info.comment_count,
                    'url': post.url,
                    'timestamp': post.info.timestamp.isoformat() if post.info.timestamp else None,
                },
                'comments_analyzed': len(post.comments),
                'summary': summary.to_dict(),
                'processing_time_ms': summary.processing_time_ms,
            }
            
            if summary.error:
                response['error'] = summary.error
                response['success'] = False
            
            return jsonify(response)
            
        except InstagramClientError as e:
            logger.error(f"Instagram client error: {e}")
            return jsonify({
                'success': False,
                'error': f'Instagram error: {str(e)}'
            }), 401
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }), 500
            
        finally:
            if instagram_client:
                try:
                    instagram_client.close()
                except Exception as e:
                    logger.warning(f"Error closing Instagram client: {e}")
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        return jsonify({
            'status': 'ok',
            'gemini_configured': bool(settings.GEMINI_API_KEY),
            'instagram_graph_api_configured': bool(settings.INSTAGRAM_ACCESS_TOKEN and settings.INSTAGRAM_BUSINESS_ACCOUNT_ID),
            'instagram_legacy_configured': bool(settings.INSTAGRAM_USERNAME and settings.INSTAGRAM_PASSWORD),
            'flask_debug': settings.FLASK_DEBUG,
            'flask_port': settings.FLASK_PORT,
        })
    
    @app.route('/api/config/status', methods=['GET'])
    def config_status():
        """
        Detailed configuration status endpoint.
        Useful for debugging configuration issues.
        """
        return jsonify(settings.get_status_dict())
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'success': False, 'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(500)
    def server_error(error):
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({'success': False, 'error': 'Method not allowed'}), 405
    
    return app


def main():
    """Run the Flask application."""
    app = create_app()
    
    # Validate configuration and print warnings
    print("\n" + "="*60)
    print("Instagram AI Analyzer - Starting Up (Graph API Edition)")
    print("="*60)
    
    # Instagram configuration
    if settings.INSTAGRAM_ACCESS_TOKEN and settings.INSTAGRAM_BUSINESS_ACCOUNT_ID:
        print("✅ Instagram Graph API configured (RECOMMENDED)")
        token_preview = settings.INSTAGRAM_ACCESS_TOKEN[:8] + "..."
        print(f"   Token: {token_preview}")
        print(f"   Account ID: {settings.INSTAGRAM_BUSINESS_ACCOUNT_ID}\n")
    elif settings.INSTAGRAM_USERNAME and settings.INSTAGRAM_PASSWORD:
        print("⚠️  WARNING: Using legacy Instagram credentials (instagrapi)")
        print(f"   Username: {settings.INSTAGRAM_USERNAME}")
        print("   Please migrate to Graph API as soon as possible.\n")
    else:
        print("❌ ERROR: Instagram credentials not configured.")
        print("   Please set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_BUSINESS_ACCOUNT_ID")
        print("   or legacy INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in .env file.\n")
    
    # Gemini configuration
    if not settings.GEMINI_API_KEY:
        print("⚠️  WARNING: Gemini API key not configured.")
        print("   Set GEMINI_API_KEY in .env file.")
        print("   AI summarization features will be disabled.\n")
    else:
        print(f"✅ Gemini API key configured (using model: {settings.GEMINI_MODEL})\n")
    
    print(f"🚀 Starting server on http://0.0.0.0:{settings.FLASK_PORT}")
    print(f"📊 Debug mode: {'ON' if settings.FLASK_DEBUG else 'OFF'}")
    print("="*60 + "\n")
    
    try:
        app.run(
            host='0.0.0.0',
            port=settings.FLASK_PORT,
            debug=settings.FLASK_DEBUG
        )
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\n❌ ERROR: Port {settings.FLASK_PORT} is already in use.")
            print(f"   Either stop the other process or change FLASK_PORT in .env file.\n")
        raise
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}\n")
        raise


if __name__ == '__main__':
    main()