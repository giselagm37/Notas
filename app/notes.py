# app/notes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app import mysql
from app.utils import login_required

notes = Blueprint('notes', __name__)

# Definir la función fuera para que esté disponible en todo el código
def validar_programa_y_oficina(cursor, id_programa, id_oficina):

    # Lógica para validar el programa y la oficina
    if not id_programa or not id_oficina:
        flash("Error: Programa y oficina son requeridos.", "danger")
        return False
    
    try:
        id_programa = int(id_programa)
        id_oficina = int(id_oficina)
    except ValueError:
        flash("Error: Programa u oficina inválidos.", "danger")
        return False
    
    # Verificar que el programa existe
    cursor.execute("SELECT id_programa FROM programa WHERE id_programa = %s", (id_programa,))
    if not cursor.fetchone():
        flash("Error: El programa seleccionado no existe.", "danger")
        return False
    
    # Verificar que la oficina existe
    cursor.execute("SELECT id_oficina FROM oficina WHERE id_oficina = %s", (id_oficina,))
    if not cursor.fetchone():
        flash("Error: La oficina seleccionada no existe.", "danger")
        return False
    
    return True

@notes.route('/cargar_nota', methods=['GET', 'POST'])
@login_required
def cargar_nota():
    cursor = mysql.connection.cursor()
    es_admin = session.get('rol') == 'admin'

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
                return redirect(url_for("notes.cargar_nota"))
            
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
                return redirect(url_for("notes.cargar_nota"))
            
            # Verificar si estamos actualizando una nota existente
            elif "nota_id" in request.form:
                nota_id = request.form["nota_id"]
                
                # Si es admin, puede usar el usuario seleccionado en el formulario
                if es_admin and "usuario_seleccionado" in request.form:
                    id_usuario = request.form["usuario_seleccionado"]
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
                if not validar_programa_y_oficina(cursor, id_programa, id_oficina):
                    return redirect(url_for("notes.cargar_nota"))
                
                # Actualizar la nota en la base de datos
                sql = """
                    UPDATE notas
                    SET anio = %s, estado = %s, id_programa = %s, id_oficina = %s, 
                        numero_oficina = %s, detalle = %s, fechaIngreso = %s
                    WHERE id = %s
                """
                valores = (anio, estado, id_programa, id_oficina, numero_oficina, 
                          detalle, fechaIngreso, nota_id)
                
                # Si no es admin, restringir a sus propias notas
                if not es_admin:
                    sql += " AND id_usuario = %s"
                    valores = valores + (id_usuario,)
                
                cursor.execute(sql, valores)
                mysql.connection.commit()
                
                flash("Nota actualizada correctamente.", "success")
                return redirect(url_for("notes.cargar_nota"))
            
            # Procesamiento normal de la nota (nueva nota)
            else:
                # Si es admin, puede usar el usuario seleccionado en el formulario
                if es_admin and "usuario_seleccionado" in request.form:
                    id_usuario = request.form["usuario_seleccionado"]
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
                if not validar_programa_y_oficina(cursor, id_programa, id_oficina):
                    return redirect(url_for("notes.cargar_nota"))

                # Insertar la nota en la base de datos
                sql = """
                    INSERT INTO notas (id_usuario, anio, estado, id_programa, id_oficina, numero_oficina, detalle, fechaIngreso)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (id_usuario, anio, estado, id_programa, id_oficina, numero_oficina, detalle, fechaIngreso))
                mysql.connection.commit()

                flash("Nota cargada correctamente.", "success")
                return redirect(url_for("notes.cargar_nota"))

        except Exception as e:
            mysql.connection.rollback()
            flash(f"Error al procesar la nota: {str(e)}", "danger")
            return redirect(url_for("notes.cargar_nota"))

        finally:
            cursor.close()

    # Obtener programas y oficinas para mostrar en el formulario
    cursor.execute("SELECT id_programa, nombre FROM programa")
    programas = cursor.fetchall()

    cursor.execute("SELECT id_oficina, nombre FROM oficina")
    oficinas = cursor.fetchall()
    
    # Obtener lista de usuarios para el dropdown (solo para administradores)
    usuarios = []
    if es_admin:
        cursor.execute("SELECT id_usuario, nombre, apellido FROM usuario")
        usuarios = cursor.fetchall()
    
    # Obtener todas las notas con información de programa y oficina
    sql_notas = """
    SELECT n.id, n.anio, n.estado, p.nombre AS nombre_programa, 
        o.nombre AS nombre_oficina, n.numero_oficina, 
        n.detalle, n.fechaIngreso, u.nombre AS nombre_usuario,
        u.id_usuario
    FROM notas n
    JOIN programa p ON n.id_programa = p.id_programa
    JOIN oficina o ON n.id_oficina = o.id_oficina
    JOIN usuario u ON n.id_usuario = u.id_usuario
    """
    
    # Si no es admin, sólo mostrar sus propias notas
    if not es_admin:
        sql_notas += " WHERE n.id_usuario = %s"
        cursor.execute(sql_notas, (session["usuario_id"],))
    else:
        cursor.execute(sql_notas)
    
    notas = cursor.fetchall()
    
    # Convertir los resultados a una lista de diccionarios para facilitar el acceso
    notas_dict = []
    for fila in notas:
        notas_dict.append({
            'id': fila[0],
            'anio': fila[1],
            'estado': fila[2],
            'nombre_programa': fila[3],
            'nombre_oficina': fila[4],
            'numero_oficina': fila[5],
            'detalle': fila[6],  
            'fechaIngreso': fila[7].strftime('%Y-%m-%d') if fila[7] else '',
            'nombre_usuario': fila[8],
            'id_usuario': fila[9]
        })


    cursor.close()

    return render_template("cargar_nota.html", 
                          programas=programas, 
                          oficinas=oficinas, 
                          notas=notas_dict,
                          nota=None,
                          nota_id=None,
                          titulo_formulario="Cargar Nueva Nota",
                          es_admin=es_admin,
                          usuarios=usuarios)

@notes.route('/editar_nota/<int:nota_id>')
@login_required
def editar_nota(nota_id):
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
        if session.get("rol") == "admin":
            cursor.execute("""
                SELECT n.id, n.anio, n.estado, n.id_programa, p.nombre AS nombre_programa, 
                       n.id_oficina, o.nombre AS nombre_oficina, n.numero_oficina, 
                       n.detalle, n.fechaIngreso
                FROM notas n
                JOIN programa p ON n.id_programa = p.id_programa
                JOIN oficina o ON n.id_oficina = o.id_oficina
                WHERE n.id = %s
            """, (nota_id,))
        else:
            cursor.execute(sql, (nota_id, session["usuario_id"]))

        nota_result = cursor.fetchone()
        
        if not nota_result:
            flash("No se encontró la nota o no tienes permisos para editarla.", "danger")
            return redirect(url_for("notes.cargar_nota"))
        
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
        return redirect(url_for("notes.cargar_nota"))
    
    finally:
        cursor.close() 

@notes.route('/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_nota(id):
    if session.get('rol') != 'admin':
        flash("Acceso denegado. Solo los administradores pueden eliminar notas.", "danger")
        return redirect(url_for('main.admin_dashboard'))

    try:
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM notas WHERE id = %s", (id,))
        mysql.connection.commit()
        cursor.close()

        flash("Nota eliminada correctamente.", "success")
    except Exception as e:
        flash(f"Error al eliminar la nota: {str(e)}", "danger")

    return redirect(url_for('main.admin_dashboard'))


