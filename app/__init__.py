# /lost_and_found_app/app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import DevelopmentConfig
import os
import os # This might already be there

# ---- TEMPORARY DEBUG CODE ----
print("---- CHECKING ENVIRONMENT ----")
database_url_from_env = os.environ.get('postgresql://lost_and_found_db_6eu5_user:rKmaHFkuzmHKXMahEkJzJQ9pCkLfxDoo@dpg-d2oqka8gjchc73f3fvg0-a/lost_and_found_db_6eu5')
print(f"The DATABASE_URL Render sees is: {database_url_from_env}")
# --------------------------------

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'main.login' # Where to redirect if user is not logged in
login_manager.login_message_category = 'info' # Flash message category

def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure the instance folder exists for the db
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    db.init_app(app)
    login_manager.init_app(app)
    
    # Create upload folder if it doesn't exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    from .routes import main_bp
    app.register_blueprint(main_bp)
    
    from .models import User, Item

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        db.create_all()

    return app