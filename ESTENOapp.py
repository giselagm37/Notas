from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import bcrypt
from datetime import timedelta
from functools import wraps

app = Flask(__name__)

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = "admid"
app.config["MYSQL_DB"] = "notas"
app.config["SECRET_KEY"] = "secreto"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=5)  # Sesión expira después de 5 minutos de inactividad
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"  # Asegura que la sesión se almacene en disco




mysql = MySQL(app)

# Decorador para verificar si el usuario está logueado
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Debes iniciar sesión para acceder a esta página.", "danger")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# Decorador para verificar si el usuario es administrador
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Debes iniciar sesión para acceder a esta página.", "danger")
            return redirect(url_for("login"))
        
        # Verificar si el usuario tiene rol de administrador
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT role FROM usuario WHERE id_usuario = %s", (session["usuario_id"],))
        usuario = cursor.fetchone()
        cursor.close()
        
        if not usuario or usuario[0] != "admin":
            flash("No tienes permisos de administrador para acceder a esta página.", "danger")
            return redirect(url_for("cargar_nota"))
            
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def index():
    

    if "usuario_id" in session:
        # Verificar el rol del usuario y redirigir según corresponda
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT rol_id FROM usuario WHERE id_usuario = %s", (session["usuario_id"],))
        usuario = cursor.fetchone()
        if not usuario or usuario[0] != "admin":
            cursor.close()
        
        if usuario and usuario[0] == "admin":
            return redirect(url_for("admin_dashboard"))
        else:
            return redirect(url_for("cargar_nota"))
    else:
        return redirect(url_for("login"))
    

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        legajo = request.form['legajo']
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        password = request.form['password']
        rol_id = request.form['role']  # Debe coincidir con los valores en el <select>

        # Hash de la contraseña
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO usuario (legajo, nombre, apellido, contraseña, rol_id) VALUES (%s, %s, %s, %s, %s)", 
               (legajo, nombre, apellido, hashed_password.decode('utf-8'), rol_id))
        mysql.connection.commit()
        cursor.close()

        flash("Registro exitoso. Ahora puedes iniciar sesión.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        contraseña = request.form['contraseña']  # Aquí usas "contraseña", no "password"
        print(session)  # Agrega esto después de iniciar sesión


        # Si el usuario y contraseña son 9999, es administrador
        if usuario == "9999" and contraseña == "9999":
            session["usuario"] = usuario
            session["rol"] = "admin"  # Asegura que se guarde el rol correctamente
            flash("Bienvenido, administrador.", "success")
            
            print(session)  # <-- Verifica que la sesión contiene los datos antes de redirigir
            
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Credenciales incorrectas.", "danger")

        # Abrir cursor para hacer la consulta
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT u.id_usuario, u.nombre, r.nombre, u.contraseña
            FROM usuario u
            JOIN roles r ON u.rol_id = r.id_rol
            WHERE u.legajo = %s
        """, (usuario,))
        
        user = cursor.fetchone()
        cursor.close()

        if user:
            # Aquí corregimos el uso de "contraseña" en lugar de "password"
            if bcrypt.checkpw(contraseña.encode('utf-8'), user[3].encode('utf-8')):
                session['usuario_id'] = user[0]
                session['nombre'] = user[1]
                session['rol'] = user[2]  # Guardamos el rol en la sesión

                if user[2] == "admin":
                    return redirect(url_for('admin_dashboard'))  # Redirige al panel de administración
                else:
                    return redirect(url_for('cargar_nota'))  # Redirige a la página de carga de notas
            else:
                flash("Credenciales incorrectas, intenta de nuevo.", "danger")
        else:
            flash("Credenciales incorrectas, intenta de nuevo.", "danger")
    
    return render_template("login.html")



@app.route("/logout")
def logout():
    session.clear()  # Limpiar toda la sesión
    flash("Has cerrado sesión correctamente.", "success")
    return redirect(url_for("login"))


#Administrador
@app.route('/admin_dashboard')
def admin_dashboard():
    if "usuario" not in session or session.get("rol") != "admin":
        flash("Acceso no autorizado", "danger")
        return redirect(url_for("login"))
    
    cursor = mysql.connection.cursor()

    # Obtener filtros de query string
    estado = request.args.get('estado')
    fecha = request.args.get('fecha')

    # Obtener usuarios
    cursor.execute("""
        SELECT usuario.id_usuario, usuario.legajo, usuario.nombre, usuario.apellido, roles.nombre AS rol 
        FROM usuario 
        LEFT JOIN roles ON usuario.rol_id = roles.id_rol
    """)
    usuarios = cursor.fetchall()

    # Base del query para notas
    query = """
        SELECT n.id, n.anio, n.estado, p.nombre AS nombre_programa, 
               o.nombre AS nombre_oficina, n.numero_oficina, 
               n.detalle, n.fechaIngreso, u.nombre AS nombre_usuario, u.apellido
        FROM notas n
        JOIN programa p ON n.id_programa = p.id_programa
        JOIN oficina o ON n.id_oficina = o.id_oficina
        JOIN usuario u ON n.id_usuario = u.id_usuario
        WHERE 1=1
    """
    params = []

    # Agregar filtros si existen
    if estado:
        query += " AND n.estado = %s"
        params.append(estado)
    if fecha:
        query += " AND DATE(n.fechaIngreso) = %s"
        params.append(fecha)

    query += " ORDER BY n.fechaIngreso DESC"
    cursor.execute(query, params)
    notas = cursor.fetchall()
    cursor.close()

    # Transformar a dicts para facilitar renderizado
    notas_dict = []
    for nota in notas:
        notas_dict.append({
            'id': nota[0],
            'anio': nota[1],
            'estado': nota[2],
            'nombre_programa': nota[3],
            'nombre_oficina': nota[4],
            'numero_oficina': nota[5],
            'detalle': nota[6],
            'fechaIngreso': nota[7].strftime('%Y-%m-%d') if nota[7] else '',
            'nombre_usuario': nota[8] + ' ' + nota[9]
        })

    return render_template("admin_dashboard.html", usuarios=usuarios, notas=notas_dict)


@app.route('/eliminar_nota/<int:id>', methods=['POST'])
@admin_required
def eliminar_nota(id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM notas WHERE id = %s", (id,))
        mysql.connection.commit()
        flash("Nota eliminada correctamente.", "success")
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error al eliminar la nota: {str(e)}", "danger")
    finally:
        cursor.close()

    return redirect(url_for('admin_dashboard'))


@app.route('/delete_user/<int:id>', methods=['GET'])
@admin_required
def delete_user(id):
    # Evitar que se elimine a sí mismo
    if id == session["usuario_id"]:
        flash("No puedes eliminar tu propio usuario.", "danger")
        return redirect(url_for('admin_dashboard'))
    
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM usuario WHERE id_usuario = %s", (id,))
    mysql.connection.commit()
    cursor.close()

    flash("Usuario eliminado correctamente.", "success")
    return redirect(url_for('admin_dashboard'))


#Notas pendientes/resueltas
@app.route('/notas/<estado>')
def notas_estado(estado):
    #if session.get('rol') != 'usuario':
    #    return redirect(url_for('login'))
    


    if estado not in ['pendiente', 'resuelto']:
        return redirect(url_for('notas_estado', estado='pendiente'))

    cursor = mysql.connection.cursor()

    # Traer notas filtradas por estado (de cualquier usuario)
    sql = """
    SELECT n.id, n.anio, n.estado, p.nombre AS nombre_programa, 
           o.nombre AS nombre_oficina, n.numero_oficina, 
           n.detalle, n.fechaIngreso, u.nombre AS nombre_usuario
    FROM notas n
    JOIN programa p ON n.id_programa = p.id_programa
    JOIN oficina o ON n.id_oficina = o.id_oficina
    JOIN usuario u ON n.id_usuario = u.id_usuario
    WHERE n.estado = %s
    ORDER BY n.fechaIngreso DESC
    """
    cursor.execute(sql, (estado,))
    notas = cursor.fetchall()

    notas_dict = []
    for nota in notas:
        notas_dict.append({
            'id': nota[0],
            'anio': nota[1],
            'estado': nota[2],
            'nombre_programa': nota[3],
            'nombre_oficina': nota[4],
            'numero_oficina': nota[5],
            'detalle': nota[6],
            'fechaIngreso': nota[7].strftime('%Y-%m-%d') if nota[7] else '',
            'nombre_usuario': nota[8]
        })

    cursor.close()
    return render_template('notas_genericas.html', notas=notas_dict, estado=estado)


@app.route('/cargar_nota', methods=['GET', 'POST'])
def cargar_nota():
    # Verificar si el usuario está autenticado
    if "usuario_id" not in session:
        flash("Debes iniciar sesión para acceder a esta página.", "danger")
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()

    if request.method == "POST":
        try:
            # Verificar si estamos agregando un nuevo programa
            if "accion" in request.form and request.form["accion"] == "nuevo_programa":
                nombre_programa = request.form.get("nuevo_programa")
                
                if nombre_programa:
                    # Generar un número automático para el programa
                    cursor.execute("SELECT MAX(CAST(numero AS UNSIGNED)) FROM programa")
                    max_numero = cursor.fetchone()[0]
                    
                    # Si no hay registros o el valor es NULL, empezar desde 1
                    if max_numero is None:
                        nuevo_numero = "1"
                    else:
                        nuevo_numero = str(int(max_numero) + 1)
                    
                    # Insertar el nuevo programa en la base de datos
                    cursor.execute("INSERT INTO programa (nombre, numero) VALUES (%s, %s)", 
                                  (nombre_programa, nuevo_numero))
                    mysql.connection.commit()
                    flash("Nuevo programa agregado correctamente.", "success")
                else:
                    flash("Error: Nombre de programa es requerido.", "danger")
                
                # Redireccionar para mostrar el formulario actualizado
                return redirect(url_for("cargar_nota"))
            
            # Verificar si estamos agregando una nueva oficina
            elif "accion" in request.form and request.form["accion"] == "nueva_oficina":
                nombre_oficina = request.form.get("nueva_oficina")
                
                if nombre_oficina:
                    # Insertar la nueva oficina en la base de datos
                    cursor.execute("INSERT INTO oficina (nombre) VALUES (%s)", (nombre_oficina,))
                    mysql.connection.commit()
                    flash("Nueva oficina agregada correctamente.", "success")
                else:
                    flash("Error: Nombre de oficina es requerido.", "danger")
                
                # Redireccionar para mostrar el formulario actualizado
                return redirect(url_for("cargar_nota"))
            
            # Verificar si estamos actualizando una nota existente
            elif "nota_id" in request.form:
                nota_id = request.form["nota_id"]
                id_usuario = session["usuario_id"]
                anio = request.form["anio"]
                estado = request.form["estado"]
                id_programa = request.form.get("id_programa")
                id_oficina = request.form.get("id_oficina")
                numero_oficina = request.form["numero_oficina"]
                detalle = request.form["detalle"]
                fechaIngreso = request.form["fechaIngreso"]
                
                # Validar campos
                if not _validar_campos_nota(cursor, id_programa, id_oficina):
                    return redirect(url_for("cargar_nota"))
                
                # Actualizar la nota en la base de datos
                sql = """
                    UPDATE notas
                    SET anio = %s, estado = %s, id_programa = %s, id_oficina = %s, 
                        numero_oficina = %s, detalle = %s, fechaIngreso = %s
                    WHERE id = %s AND id_usuario = %s
                """
                cursor.execute(sql, (anio, estado, id_programa, id_oficina, numero_oficina, 
                                    detalle, fechaIngreso, nota_id, id_usuario))
                mysql.connection.commit()
                
                flash("Nota actualizada correctamente.", "success")
                return redirect(url_for("cargar_nota"))
            
            # Procesamiento normal de la nota (nueva nota)
            else:
                id_usuario = session["usuario_id"]
                anio = request.form["anio"]
                estado = request.form["estado"]
                id_programa = request.form.get("id_programa")
                id_oficina = request.form.get("id_oficina")
                numero_oficina = request.form["numero_oficina"]
                detalle = request.form["detalle"]
                fechaIngreso = request.form["fechaIngreso"]

                # Validar campos
                if not _validar_campos_nota(cursor, id_programa, id_oficina):
                    return redirect(url_for("cargar_nota"))

                # Insertar la nota en la base de datos
                sql = """
                    INSERT INTO notas (id_usuario, anio, estado, id_programa, id_oficina, numero_oficina, detalle, fechaIngreso)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (id_usuario, anio, estado, id_programa, id_oficina, numero_oficina, detalle, fechaIngreso))
                mysql.connection.commit()

                flash("Nota cargada correctamente.", "success")
                return redirect(url_for("cargar_nota"))

        except Exception as e:
            mysql.connection.rollback()
            flash(f"Error al procesar la nota: {str(e)}", "danger")
            return redirect(url_for("cargar_nota"))

        finally:
            cursor.close()

    # Obtener programas y oficinas para mostrar en el formulario
    cursor.execute("SELECT id_programa, nombre FROM programa")
    programas = cursor.fetchall()

    cursor.execute("SELECT id_oficina, nombre FROM oficina")
    oficinas = cursor.fetchall()
    
    # Obtener todas las notas con información de programa y oficina
    sql_notas = """
    SELECT n.id, n.anio, n.estado, p.nombre AS nombre_programa, 
        o.nombre AS nombre_oficina, n.numero_oficina, 
        n.detalle, n.fechaIngreso, u.nombre AS nombre_usuario
    FROM notas n
    JOIN programa p ON n.id_programa = p.id_programa
    JOIN oficina o ON n.id_oficina = o.id_oficina
    JOIN usuario u ON n.id_usuario = u.id_usuario
    WHERE n.id_usuario = %s
    ORDER BY n.fechaIngreso DESC
"""
    cursor.execute(sql_notas, (session["usuario_id"],))
    notas = cursor.fetchall()
    
    # Convertir los resultados a una lista de diccionarios para facilitar el acceso
    notas_dict = []
    for nota in notas:
        notas_dict.append({
            'id': nota[0],      # Añadir el ID de la nota
            'anio': nota[1],
            'estado': nota[2],
            'nombre_programa': nota[3],
            'nombre_oficina': nota[4],
            'numero_oficina': nota[5],
            'detalle': nota[6],  
            'fechaIngreso': nota[7].strftime('%Y-%m-%d') if nota[7] else '',
            'nombre_usuario': nota[8]
        })


    cursor.close()

    return render_template("cargar_nota.html", 
                          programas=programas, 
                          oficinas=oficinas, 
                          notas=notas_dict,
                          nota=None,
                          nota_id=None,
                          titulo_formulario="Cargar Nueva Nota")

# Función auxiliar para validar campos de nota
def _validar_campos_nota(cursor, id_programa, id_oficina):
    # Validar que id_programa sea un número válido
    if id_programa:
        try:
            id_programa = int(id_programa)
        except ValueError:
            flash("Error: id_programa debe ser un número válido.", "danger")
            return False

        # Verificar que el programa exista en la base de datos
        cursor.execute("SELECT id_programa FROM programa WHERE id_programa = %s", (id_programa,))
        if cursor.fetchone() is None:
            flash("Error: El programa seleccionado no existe.", "danger")
            return False

    # Validar que id_oficina sea un número válido
    if id_oficina:
        try:
            id_oficina = int(id_oficina)
        except ValueError:
            flash("Error: id_oficina debe ser un número válido.", "danger")
            return False

        # Verificar que la oficina exista en la base de datos
        cursor.execute("SELECT id_oficina FROM oficina WHERE id_oficina = %s", (id_oficina,))
        if cursor.fetchone() is None:
            flash("Error: La oficina seleccionada no existe.", "danger")
            return False
    
    return True

@app.route('/editar_nota/<int:nota_id>')
def editar_nota(nota_id):
    # Verificar si el usuario está autenticado
    if "usuario_id" not in session:
        flash("Debes iniciar sesión para acceder a esta página.", "danger")
        return redirect(url_for("login"))
    
    cursor = mysql.connection.cursor()
    
    try:
        # Obtener la nota con la información de programa y oficina
        sql = """
            SELECT n.id, n.anio, n.estado, n.id_programa, p.nombre AS nombre_programa, 
                   n.id_oficina, o.nombre AS nombre_oficina, n.numero_oficina, 
                   n.detalle, n.fechaIngreso
            FROM notas n
            JOIN programa p ON n.id_programa = p.id_programa
            JOIN oficina o ON n.id_oficina = o.id_oficina
            WHERE n.id = %s AND n.id_usuario = %s
        """
        cursor.execute(sql, (nota_id, session["usuario_id"]))
        nota_result = cursor.fetchone()
        
        if not nota_result:
            flash("No se encontró la nota o no tienes permisos para editarla.", "danger")
            return redirect(url_for("cargar_nota"))
        
        # Convertir el resultado a un diccionario
        nota = {
            'id': nota_result[0],
            'anio': nota_result[1],
            'estado': nota_result[2],
            'id_programa': nota_result[3],
            'nombre_programa': nota_result[4],
            'id_oficina': nota_result[5],
            'nombre_oficina': nota_result[6],
            'numero_oficina': nota_result[7],
            'detalle': nota_result[8],
            'fechaIngreso': nota_result[9].strftime('%Y-%m-%d') if nota_result[9] else ''
        }
        
        # Obtener programas y oficinas para mostrar en el formulario
        cursor.execute("SELECT id_programa, nombre FROM programa")
        programas = cursor.fetchall()

        cursor.execute("SELECT id_oficina, nombre FROM oficina")
        oficinas = cursor.fetchall()
        
        # Obtener todas las notas con información de programa y oficina
        sql_notas = """
            SELECT n.id, n.anio, n.estado, n.id_programa, p.nombre AS nombre_programa, 
                   n.id_oficina, o.nombre AS nombre_oficina, n.numero_oficina, 
                   n.detalle, n.fechaIngreso
            FROM notas n
            JOIN programa p ON n.id_programa = p.id_programa
            JOIN oficina o ON n.id_oficina = o.id_oficina
            WHERE n.id_usuario = %s
            ORDER BY n.fechaIngreso DESC
        """
        cursor.execute(sql_notas, (session["usuario_id"],))
        notas = cursor.fetchall()
        
        # Convertir los resultados a una lista de diccionarios para facilitar el acceso
        notas_dict = []
        for n in notas:
            notas_dict.append({
                'id': n[0],
                'anio': n[1],
                'estado': n[2],
                'id_programa': n[3],
                'nombre_programa': n[4],
                'id_oficina': n[5],
                'nombre_oficina': n[6],
                'numero_oficina': n[7],
                'detalle': n[8],
                'fechaIngreso': n[9].strftime('%Y-%m-%d') if n[9] else ''
            })
        
        return render_template("cargar_nota.html", 
                              programas=programas, 
                              oficinas=oficinas, 
                              notas=notas_dict,
                              nota=nota,
                              nota_id=nota_id,
                              titulo_formulario="Editar Nota")
        
    except Exception as e:
        flash(f"Error al cargar la nota para edición: {str(e)}", "danger")
        return redirect(url_for("cargar_nota"))
    
    finally:
        cursor.close() 

# Para mantener la sesión activa
@app.before_request
def session_management():
    session.permanent = True  # Habilita la duración de sesión configurada

if __name__ == "__main__":
    app.run(debug=True)