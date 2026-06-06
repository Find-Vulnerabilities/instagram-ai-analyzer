"""
Main Flask/Dash web application for Instagram AI Analyzer.
Provides a web interface for analyzing Instagram posts and their comments.
"""

import logging
import os
from typing import Optional

from core.instagram_client import InstagramClientError
from core.instagrapi_adapter import InstagrapiAdapter
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
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.urandom(24)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
    
    # Initialize global components
    instagram_client = None
    summarizer = None
    
    if settings.GEMINI_API_KEY:
        summarizer = CommentSummarizer()
        logger.info("Summarizer initialized with Gemini API")
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
                'error': 'Gemini API is not configured. Please set GEMINI_API_KEY.'
            }), 503
        
        # Validate Instagram credentials
        if not settings.INSTAGRAM_USERNAME or not settings.INSTAGRAM_PASSWORD:
            return jsonify({
                'success': False,
                'error': 'Instagram credentials not configured. Please set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in .env file.'
            }), 503
        
        instagram_client = None
        
        try:
            # Initialize and login to Instagram
            instagram_client = InstagrapiAdapter()
            logger.info(f"Logging into Instagram as {settings.INSTAGRAM_USERNAME}")
            instagram_client.login(
                settings.INSTAGRAM_USERNAME,
                settings.INSTAGRAM_PASSWORD
            )
            
            # Fetch post with comments
            logger.info(f"Fetching post: {post_url}")
            post = instagram_client.get_post_with_comments(
                post_url,
                comment_limit=comment_limit,
                include_replies=include_replies
            )
            
            if post.error:
                return jsonify({
                    'success': False,
                    'error': post.error
                }), 404
            
            logger.info(f"Fetched post by {post.info.username} with {len(post.comments)} comments")
            
            # Generate AI summary
            logger.info("Generating AI summary...")
            summary = summarizer.summarize_post(post)
            
            # Prepare response
            response = {
                'success': summary.is_successful,
                'post': {
                    'username': post.info.username,
                    'caption': post.info.caption[:500],
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
                instagram_client.close()
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        return jsonify({
            'status': 'ok',
            'gemini_configured': bool(settings.GEMINI_API_KEY),
            'instagram_configured': bool(settings.INSTAGRAM_USERNAME and settings.INSTAGRAM_PASSWORD),
        })
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'success': False, 'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(500)
    def server_error(error):
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
    
    return app


def main():
    """Run the Flask application."""
    app = create_app()
    
    # Validate configuration
    if not settings.INSTAGRAM_USERNAME or not settings.INSTAGRAM_PASSWORD:
        logger.warning(
            "Instagram credentials not configured. "
            "Set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in .env file."
        )
    
    if not settings.GEMINI_API_KEY:
        logger.warning(
            "Gemini API key not configured. "
            "Set GEMINI_API_KEY in .env file. AI features will be disabled."
        )
    
    logger.info(f"Starting Instagram AI Analyzer on port {settings.FLASK_PORT}")
    app.run(
        host='0.0.0.0',
        port=settings.FLASK_PORT,
        debug=settings.FLASK_DEBUG
    )


if __name__ == '__main__':
    main()