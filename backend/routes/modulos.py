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
def get_modulos():
    conn = get_db_connection()
    if not conn: raise HTTPException(status_code=500, detail="Error DB")
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT m.id, m.nombre, m.nivel, m.subnivel, m.orden, 
                   m.carrera_id, m.periodo, c.nombre as carrera_nombre 
            FROM modulos m
            LEFT JOIN carreras c ON m.carrera_id = c.id
            ORDER BY m.orden, m.id
        """)
        return {"modulos": rows_to_dicts(cur, cur.fetchall())}
    finally: conn.close()

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
    """Limpia los módulos de ingeniería de la base de datos y re-siembra los módulos del CEA."""
    from database import get_db_connection
    from seed_cea import seed_cea_data
    conn = get_db_connection()
    if not conn: raise HTTPException(status_code=500, detail="Error DB")
    try:
        cur = conn.cursor()
        carreras_oficiales = [
            'Sistemas Informáticos', 'Veterinaria', 'Educación Parvularia', 
            'Fisioterapia', 'Contabilidad General', 'Corte y Confección', 
            'Belleza Integral', 'Gastronomía', 'Matemática', 'Lenguaje', 
            'Ciencias Naturales', 'Ciencias Sociales'
        ]
        format_strings = ','.join(['%s'] * len(carreras_oficiales))
        cur.execute(f"SELECT id FROM carreras WHERE nombre NOT IN ({format_strings})", tuple(carreras_oficiales))
        carreras_a_borrar = cur.fetchall()
        
        if carreras_a_borrar:
            carrera_ids = tuple(c[0] for c in carreras_a_borrar)
            cur.execute(f"SELECT id FROM modulos WHERE carrera_id IN %s", (carrera_ids,))
            modulos_a_borrar = cur.fetchall()
            
            if modulos_a_borrar:
                modulo_ids = tuple(m[0] for m in modulos_a_borrar)
                cur.execute(f"DELETE FROM temas WHERE modulo_id IN %s", (modulo_ids,))
                cur.execute(f"DELETE FROM modulos WHERE carrera_id IN %s", (carrera_ids,))
            
            cur.execute(f"DELETE FROM carreras WHERE id IN %s", (carrera_ids,))
            
        cur.execute("DELETE FROM temas WHERE modulo_id IN (SELECT id FROM modulos WHERE nombre LIKE '%Cloud Computing%' OR nombre LIKE '%Algoritmos%' OR nombre LIKE '%Módulo Emergente%' OR nombre LIKE '%Base de Datos%')")
        cur.execute("DELETE FROM modulos WHERE nombre LIKE '%Cloud Computing%' OR nombre LIKE '%Algoritmos%' OR nombre LIKE '%Módulo Emergente%' OR nombre LIKE '%Base de Datos%'")
        
        conn.commit()
        seed_cea_data()
        return {"msg": "Módulos de ingeniería borrados exitosamente. Se restablecieron los módulos del CEA."}
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

