from fastapi import APIRouter, Depends, HTTPException
from database import get_db_connection
from routes.auth import get_current_user
from pydantic import BaseModel

router = APIRouter()

class ContenidoUpdate(BaseModel):
    modulo_id: int
    tipo: str
    titulo: str
    url: str
    tema_num: int

def rows_to_dicts(cursor, rows):
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, r)) for r in rows]

@router.get("/")
def get_modulos(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    if not conn: raise HTTPException(status_code=500, detail="Error DB")
    try:
        cur = conn.cursor()
        
        # Filtro Nivel Pro: Mostrar solo lo que corresponde al usuario
        if current_user["rol"] == "estudiante":
            # Estudiante: Solo módulos de su carrera e inscripciones
            cur.execute("""
                SELECT m.id, m.nombre, m.nivel, m.subnivel, m.orden, 
                       m.carrera_id, m.periodo, c.nombre as carrera_nombre,
                       m.docente_id, (u.nombre || ' ' || u.apellido) as docente_nombre
                FROM modulos m
                JOIN carreras c ON m.carrera_id = c.id
                JOIN inscripciones i ON i.carrera_id = c.id
                LEFT JOIN usuarios u ON m.docente_id = u.id
                WHERE i.usuario_id = %s
                ORDER BY m.orden, m.id
            """, (current_user["id"],))
        elif current_user["rol"] in ["docente", "profesor"]:
            # Docente: Filtrar por módulos asignados a este docente
            cur.execute("""
                SELECT m.id, m.nombre, m.nivel, m.subnivel, m.orden, 
                       m.carrera_id, m.periodo, c.nombre as carrera_nombre,
                       m.docente_id, (u.nombre || ' ' || u.apellido) as docente_nombre
                FROM modulos m
                LEFT JOIN carreras c ON m.carrera_id = c.id
                LEFT JOIN usuarios u ON m.docente_id = u.id
                WHERE m.docente_id = %s
                ORDER BY m.orden, m.id
            """, (current_user["id"],))
        else:
            # Admin/Director: Ver todo el CEA
            cur.execute("""
                SELECT m.id, m.nombre, m.nivel, m.subnivel, m.orden, 
                       m.carrera_id, m.periodo, c.nombre as carrera_nombre,
                       m.docente_id, (u.nombre || ' ' || u.apellido) as docente_nombre
                FROM modulos m
                LEFT JOIN carreras c ON m.carrera_id = c.id
                LEFT JOIN usuarios u ON m.docente_id = u.id
                ORDER BY m.orden, m.id
            """)
            
        return {"modulos": rows_to_dicts(cur, cur.fetchall())}
    finally: conn.close()

class AsignarDocente(BaseModel):
    modulo_id: int
    docente_id: int

@router.post("/asignar-docente")
def asignar_docente(data: AsignarDocente, current_user: dict = Depends(get_current_user)):
    if current_user["rol"] not in ["jefe_carrera", "director", "admin", "administrador"]:
        raise HTTPException(status_code=403, detail="No autorizado")
    conn = get_db_connection()
    if not conn: raise HTTPException(status_code=500, detail="Error DB")
    try:
        cur = conn.cursor()
        cur.execute("UPDATE modulos SET docente_id = %s WHERE id = %s", (data.docente_id, data.modulo_id))
        conn.commit()
        return {"mensaje": "Docente asignado correctamente"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.get("/stats")
def get_stats():
    conn = get_db_connection()
    if not conn: raise HTTPException(status_code=500, detail="Error DB")
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM usuarios WHERE rol='estudiante'")
        estudiantes = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM usuarios WHERE rol='profesor'")
        profesores = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM modulos")
        modulos = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM contenidos WHERE url != ''")
        materiales = cur.fetchone()[0]
        
        return {
            "estudiantes": estudiantes,
            "profesores": profesores,
            "modulos": modulos,
            "materiales_publicados": materiales
        }
    finally: conn.close()

@router.get("/reset-ingenieria")
def reset_ingenieria():
    """Limpia TOTALMENTE la base de datos de módulos y carreras y re-siembra el CEA."""
    from database import get_db_connection
    from seed_cea import seed_cea_data
    conn = get_db_connection()
    if not conn: raise HTTPException(status_code=500, detail="Error DB")
    try:
        cur = conn.cursor()
        
        # 1. Limpieza total por tablas (independiente de FKs para asegurar)
        cur.execute("DELETE FROM inscripciones")
        cur.execute("DELETE FROM respuestas_alumno")
        cur.execute("DELETE FROM evaluaciones")
        cur.execute("DELETE FROM temas")
        cur.execute("DELETE FROM contenidos")
        cur.execute("DELETE FROM certificados")
        cur.execute("DELETE FROM planificaciones")
        cur.execute("DELETE FROM modulos")
        mods_del = cur.rowcount
        cur.execute("DELETE FROM carreras")
        cars_del = cur.rowcount
        cur.execute("DELETE FROM subsistemas WHERE id != 1")
        
        # 2. Reset secuencias
        try:
            cur.execute("ALTER SEQUENCE carreras_id_seq RESTART WITH 1")
            cur.execute("ALTER SEQUENCE modulos_id_seq RESTART WITH 1")
            cur.execute("ALTER SEQUENCE contenidos_id_seq RESTART WITH 1")
        except: pass
        
        conn.commit()
        
        # 3. Re-sembrar malla institucional oficial del CEA
        creados = seed_cea_data()
        
        return {
            "status": "success",
            "msg": f"SISTEMA DEPURADO: Se eliminaron {mods_del} módulos y {cars_del} carreras antiguas.",
            "seeding": f"Se generaron {creados} módulos institucionales oficiales del CEA.",
            "detalle": "Módulos de Ingeniería y Educación Superior eliminados permanentemente."
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.get("/{modulo_id}/contenidos")
def get_contenidos(modulo_id: int):
    conn = get_db_connection()
    if not conn: raise HTTPException(status_code=500, detail="Error DB")
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, modulo_id, tipo, titulo, url, tema_num FROM contenidos WHERE modulo_id=%s ORDER BY tema_num, tipo", (modulo_id,))
        return {"contenidos": rows_to_dicts(cur, cur.fetchall())}
    finally: conn.close()

@router.post("/contenido", dependencies=[Depends(get_current_user)])
def upsert_contenido(data: ContenidoUpdate):
    """Guarda o actualiza el material del profesor en un slot específico."""
    conn = get_db_connection()
    if not conn: raise HTTPException(status_code=500, detail="Error DB")
    try:
        cur = conn.cursor()
        # Verificar si ya existe ese slot (modulo + tema + tipo)
        cur.execute(
            "SELECT id FROM contenidos WHERE modulo_id=%s AND tema_num=%s AND tipo=%s",
            (data.modulo_id, data.tema_num, data.tipo)
        )
        row = cur.fetchone()
        if row:
            cur.execute(
                "UPDATE contenidos SET url=%s, titulo=%s WHERE id=%s",
                (data.url, data.titulo, row[0])
            )
            msg = "Actualizado"
        else:
            cur.execute(
                "INSERT INTO contenidos (modulo_id, tipo, titulo, url, tema_num) VALUES (%s,%s,%s,%s,%s)",
                (data.modulo_id, data.tipo, data.titulo, data.url, data.tema_num)
            )
            msg = "Creado"
        conn.commit()
        return {"mensaje": f"Material {msg} correctamente"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally: conn.close()

@router.delete("/usuarios/{id}", dependencies=[Depends(get_current_user)])
def delete_usuario(id: int):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM usuarios WHERE id=%s", (id,))
        conn.commit()
        return {"mensaje": "Usuario eliminado"}
    finally: conn.close()


class ContenidoSimple(BaseModel):
    titulo: str
    tipo: str
    url: str

@router.post("/{modulo_id}/contenidos", dependencies=[Depends(get_current_user)])
def add_contenido_a_modulo(modulo_id: int, data: ContenidoSimple, current_user: dict = Depends(get_current_user)):
    """Añade un material directamente a un módulo por su ID. Usado desde el Aula Virtual."""
    if current_user["rol"] not in ["docente", "profesor", "director", "jefe_carrera", "administrador"]:
        raise HTTPException(status_code=403, detail="Sin permisos para publicar materiales")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO contenidos (modulo_id, tipo, titulo, url, tema_num) VALUES (%s, %s, %s, %s, 1) RETURNING id",
            (modulo_id, data.tipo, data.titulo, data.url)
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        return {"id": new_id, "mensaje": "Material publicado correctamente"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close(); conn.close()

