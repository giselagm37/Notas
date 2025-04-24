# app/main.py
from flask import Blueprint, redirect, url_for, session, render_template, request, flash
from app import mysql
from app.utils import admin_required, login_required


main = Blueprint('main', __name__)

@main.route("/")
def index():
    if "usuario_id" in session:
        # Verificar el rol del usuario y redirigir según corresponda
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT rol_id FROM usuario WHERE id_usuario = %s", (session["usuario_id"],))
        usuario = cursor.fetchone()
        cursor.close()
        
        if usuario and usuario[0] == "admin":
            return redirect(url_for("main.admin_dashboard"))
        else:
            return redirect(url_for("notes.cargar_nota"))
    else:
        return redirect(url_for("auth.login"))

@main.route('/admin_dashboard')
@admin_required
def admin_dashboard():
    print("Entrando al panel de admin")
    print("Usuario en sesión:", session.get("usuario_id"))
    
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






@main.route('/delete_user/<int:id>', methods=['GET'])
@admin_required
def delete_user(id):
    # Evitar que se elimine a sí mismo
    if id == session.get("usuario_id"):
        flash("No puedes eliminar tu propio usuario.", "danger")
        return redirect(url_for('main.admin_dashboard'))
    
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM usuario WHERE id_usuario = %s", (id,))
    mysql.connection.commit()
    cursor.close()

    flash("Usuario eliminado correctamente.", "success")
    return redirect(url_for('main.admin_dashboard'))


from werkzeug.security import generate_password_hash

@main.route('/editar_usuario/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar_usuario(id):
    cursor = mysql.connection.cursor()
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        legajo = request.form['legajo']
        rol_id = request.form['rol_id']
        contraseña = request.form.get('contraseña')

        if contraseña:
            # Aquí generamos el hash de la nueva contraseña
            hash_pass = generate_password_hash(contraseña)
            cursor.execute(""" 
                UPDATE usuario 
                SET nombre = %s, apellido = %s, legajo = %s, rol_id = %s, contraseña = %s 
                WHERE id_usuario = %s
            """, (nombre, apellido, legajo, rol_id, hash_pass, id))
        else:
            cursor.execute(""" 
                UPDATE usuario 
                SET nombre = %s, apellido = %s, legajo = %s, rol_id = %s 
                WHERE id_usuario = %s
            """, (nombre, apellido, legajo, rol_id, id))
        
        mysql.connection.commit()
        cursor.close()
        flash("Usuario actualizado correctamente.", "success")
        return redirect(url_for('main.admin_dashboard'))
    
    # GET: mostrar el formulario con los datos actuales
    cursor.execute("SELECT * FROM usuario WHERE id_usuario = %s", (id,))
    usuario = cursor.fetchone()

    cursor.execute("SELECT * FROM roles")
    roles = cursor.fetchall()

    cursor.close()
    return render_template("editar_usuario.html", usuario=usuario, roles=roles)

@main.route('/notas/<estado>')
@login_required
def notas_estado(estado):
    if estado not in ['pendiente', 'resuelto']:
        return redirect(url_for('main.notas_estado', estado='pendiente'))

    # Obtener filtros desde query params
    programa = request.args.get('programa', '').strip()
    oficina = request.args.get('oficina', '').strip()
    fecha = request.args.get('fecha', '').strip()
    usuario = request.args.get('usuario', '').strip()

    # Base de la consulta
    sql = """
    SELECT n.id, n.anio, n.estado, p.nombre AS nombre_programa, 
           o.nombre AS nombre_oficina, n.numero_oficina, 
           n.detalle, n.fechaIngreso, u.nombre AS nombre_usuario
    FROM notas n
    JOIN programa p ON n.id_programa = p.id_programa
    JOIN oficina o ON n.id_oficina = o.id_oficina
    JOIN usuario u ON n.id_usuario = u.id_usuario
    WHERE n.estado = %s
    """
    params = [estado]

    if programa:
        sql += " AND p.nombre LIKE %s"
        params.append(f"%{programa}%")
    if oficina:
        sql += " AND o.nombre LIKE %s"
        params.append(f"%{oficina}%")
    if fecha:
        sql += " AND DATE(n.fechaIngreso) = %s"
        params.append(fecha)
    if usuario:
        sql += " AND u.nombre LIKE %s"
        params.append(f"%{usuario}%")

    sql += " ORDER BY n.fechaIngreso DESC"

    cursor = mysql.connection.cursor()
    cursor.execute(sql, params)
    notas = cursor.fetchall()

    notas_dict = [{
        'id': nota[0],
        'anio': nota[1],
        'estado': nota[2],
        'nombre_programa': nota[3],
        'nombre_oficina': nota[4],
        'numero_oficina': nota[5],
        'detalle': nota[6],
        'fechaIngreso': nota[7].strftime('%Y-%m-%d') if nota[7] else '',
        'nombre_usuario': nota[8]
    } for nota in notas]

        # Obtener valores únicos para filtros
    cursor.execute("SELECT DISTINCT nombre FROM programa ORDER BY nombre")
    programas = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT nombre FROM oficina ORDER BY nombre")
    oficinas = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT nombre FROM usuario ORDER BY nombre")
    usuarios = [row[0] for row in cursor.fetchall()]


    cursor.close()
    return render_template(
        'notas_genericas.html',
        notas=notas_dict,
        estado=estado,
        programas=programas,
        oficinas=oficinas,
        usuarios=usuarios
    )


import pandas as pd
from flask import send_file
from io import BytesIO

@main.route('/exportar_notas_excel')
@admin_required
def exportar_notas_excel():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT n.id, n.anio, n.estado, p.nombre AS programa, 
               o.nombre AS oficina, n.numero_oficina, 
               n.detalle, n.fechaIngreso, u.nombre, u.apellido
        FROM notas n
        JOIN programa p ON n.id_programa = p.id_programa
        JOIN oficina o ON n.id_oficina = o.id_oficina
        JOIN usuario u ON n.id_usuario = u.id_usuario
        ORDER BY n.fechaIngreso DESC
    """)
    datos = cursor.fetchall()
    cursor.close()

    columnas = [
        'ID', 'Año', 'Estado', 'Programa', 'Oficina',
        'N° Oficina', 'Detalle', 'Fecha de Ingreso', 'Nombre', 'Apellido'
    ]
    df = pd.DataFrame(datos, columns=columnas)

    # Crear archivo en memoria
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Notas')

    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='notas.xlsx'
    )
