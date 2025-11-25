"""
Configuration file for PDFStream
"""

import os

class Config:
    """Application configuration"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'pdfstream-secret-key-change-in-production'
    
    # Upload settings
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    # Unified max upload size (700MB) aligned with app.py configuration
    MAX_CONTENT_LENGTH = 700 * 1024 * 1024  # 700MB max file size
    ALLOWED_EXTENSIONS = {'pdf'}
    
    # Database settings
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or 'pdfstream.db'
    
    # ML settings
    MAX_KEYWORDS = 50
    TFIDF_MAX_FEATURES = 1000
    DEFAULT_TOP_RESULTS = 10
    
    # Server settings
    HOST = os.environ.get('HOST') or '0.0.0.0'
    PORT = int(os.environ.get('PORT') or 5000)
    DEBUG = os.environ.get('DEBUG') == 'True'
