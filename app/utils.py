# app/utils.py
from functools import wraps
from flask import session, redirect, url_for, flash
from app import mysql

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Debes iniciar sesión para acceder a esta página.", "danger")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Debes iniciar sesión para acceder a esta página.", "danger")
            return redirect(url_for("auth.login"))
        
        # Si ya tenemos el rol en la sesión, usemos eso
        if session.get("rol") == "admin":
            return f(*args, **kwargs)
        
        # Si no, consultamos la base de datos
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT r.nombre 
            FROM usuario u
            JOIN roles r ON u.rol_id = r.id_rol
            WHERE u.id_usuario = %s
        """, (session["usuario_id"],))
        
        usuario = cursor.fetchone()
        cursor.close()
        
        if not usuario or usuario[0] != "admin":
            flash("No tienes permisos de administrador para acceder a esta página.", "danger")
            return redirect(url_for("notes.cargar_nota"))
            
        # Almacenamos el rol en la sesión para futuras verificaciones
        session["rol"] = usuario[0]
        return f(*args, **kwargs)
    return decorated_function
