# app/__init__.py
from flask import Flask
from flask_mysqldb import MySQL
from app.config import Config
import os
from app.session import configure_session_management

mysql = MySQL()

def create_app(config_class=Config):
    app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
    static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
)
    app.config.from_object(config_class)
    
    mysql.init_app(app)
    
    # Configurar manejo de sesión
    configure_session_management(app)
    
    # Importar y registrar blueprints
    from app.auth import auth as auth_blueprint
    from app.main import main as main_blueprint
    from app.notes import notes as notes_blueprint
    
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(main_blueprint)
    app.register_blueprint(notes_blueprint)
    
    return app