# app/config.py
from datetime import timedelta

class Config:
    MYSQL_HOST = "localhost"
    MYSQL_USER = "root"
    MYSQL_PASSWORD = ""
    MYSQL_DB = "notas"
    SECRET_KEY = "secreto"
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=5)  # Sesión expira después de 5 minutos de inactividad
    SESSION_PERMANENT = True
    SESSION_TYPE = "filesystem"  # Asegura que la sesión se almacene en disco