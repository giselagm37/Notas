# app/session.py
from flask import session

def configure_session_management(app):
    @app.before_request
    def session_management():
        session.permanent = True  # Habilita la duración de sesión configurada