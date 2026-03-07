from flask import Flask, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from dotenv import load_dotenv
import os
import datetime

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
mail = Mail()

def create_app():
    app = Flask(__name__, instance_relative_config=False)

    # Load configuration from the Config class in config.py
    app.config.from_object('config.Config')

    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    # Import models to ensure they are known to SQLAlchemy
    from . import models

    # import and register blueprints
    from .routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    from .routes.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)

    from .routes.transactions import transactions_bp
    app.register_blueprint(transactions_bp)

    from .routes.budget import budget_bp
    app.register_blueprint(budget_bp)

    from .routes.income_savings import income_bp
    app.register_blueprint(income_bp)

    from .routes.debt import debt_bp
    app.register_blueprint(debt_bp)

    from .routes.reports import reports_bp
    app.register_blueprint(reports_bp)

    from .routes.settings import settings_bp
    app.register_blueprint(settings_bp)

    from .routes.notifications import notifications_bp
    app.register_blueprint(notifications_bp)

    # --- NEW: Public Homepage Route ---
    @app.route('/')
    def index():
        # If user is already logged in, send them straight to the dashboard!
        if "user_id" in session:
            return redirect(url_for('dashboard.index'))

        # Otherwise, show them the beautiful public landing page
        # UPDATED: Pointing to the new 'homepage' folder
        return render_template('homepage/index.html')

    # FIX: Make datetime.datetime.now() available as 'now()' in all templates
    @app.context_processor
    def inject_now():
        return {'now': datetime.datetime.now}

    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
        print("Database tables created/verified")

    return app
