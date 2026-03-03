import os
from pathlib import Path

# Define the base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    # Secret key - required for CSRF and sessions
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-please-change-in-production")
    
    # Session settings for production
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # DATABASE CONFIGURATION
    # Get database URL from environment variable
    database_url = os.getenv('DATABASE_URL')
    
    # Fix for Render's postgres:// vs SQLAlchemy's postgresql://
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    # Use PostgreSQL if available, otherwise fallback to SQLite
    SQLALCHEMY_DATABASE_URI = database_url or f"sqlite:///{BASE_DIR / 'finance.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # For PostgreSQL connection pool settings (optional but recommended)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 300,
        'pool_pre_ping': True
    }

    # EMAIL SETTINGS
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = MAIL_USERNAME or os.getenv('MAIL_DEFAULT_SENDER')
