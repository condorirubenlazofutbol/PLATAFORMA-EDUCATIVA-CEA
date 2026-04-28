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
        cur.execute("SELECT id, nombre, nivel, subnivel, orden FROM modulos ORDER BY orden, id")
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
