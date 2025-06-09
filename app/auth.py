# app/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from app import mysql

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        legajo = request.form['legajo']
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        password = request.form['password']
        rol_id = int(request.form.get('rol', 2))  # Toma del form o default a 2


        cursor = mysql.connection.cursor()

        # Verificar si el legajo ya existe
        cursor.execute("SELECT * FROM usuario WHERE legajo = %s", (legajo,))
        existente = cursor.fetchone()
        


        if existente:
            flash("Ese legajo ya está registrado.", "danger")
            return redirect(url_for('auth.register'))

        hashed_password = generate_password_hash(password)


        cursor.execute("INSERT INTO usuario (legajo, nombre, apellido, contraseña, rol_id) VALUES (%s, %s, %s, %s, %s)", 
                       (legajo, nombre, apellido, hashed_password, rol_id))
        mysql.connection.commit()
        cursor.close()

        flash("Registro exitoso. Ahora puedes iniciar sesión.", "success")
        return redirect(url_for('auth.login'))

    return render_template('register.html')



@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        contraseña = request.form['contraseña']  # Aquí usas "contraseña", no "password"
        print(session)  # Agrega esto después de iniciar sesión

       

        # Si el usuario y contraseña son 9999, es administrador
        if usuario == "9999" and contraseña == "9999":
            session["usuario_id"] = usuario
            session["nombre"] = "Administrador"  # <--- Esto hará que aparezca bien en el panel
            session["rol"] = "admin"
            flash("Bienvenido, administrador.", "success")
            print(session)
            return redirect(url_for("main.admin_dashboard"))


        

        # Abrir cursor para hacer la consulta
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT u.id_usuario, u.nombre, r.nombre, u.contraseña, r.id_rol

            FROM usuario u
            JOIN roles r ON u.rol_id = r.id_rol
            WHERE u.legajo = %s
        """, (usuario,))
        
        user = cursor.fetchone()
        print("user:", user)

        
        cursor.close()

        if user:
            if check_password_hash(user[3], contraseña):
                session['usuario_id'] = user[0]
                session['nombre'] = user[1]
                session['rol'] = 'admin' if user[2] == "Administrador" else 'usuario'
                session['rol_id'] = user[4]  # Guardamos el ID del rol numérico (1 o 2)

                if user[2] == "Administrador":
                    return redirect(url_for('main.admin_dashboard'))
                else:
                    return redirect(url_for('notes.cargar_nota'))


            else:
                flash("Credenciales incorrectas, intenta de nuevo.", "danger")
        else:
            flash("Credenciales incorrectas, intenta de nuevo.", "danger")
    
    return render_template("login.html")

@auth.route("/logout")
def logout():
    session.clear()  # Limpiar toda la sesión
    flash("Has cerrado sesión correctamente.", "success")
    return redirect(url_for("auth.login"))