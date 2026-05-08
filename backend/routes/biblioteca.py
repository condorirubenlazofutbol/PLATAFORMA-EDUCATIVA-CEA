"""
biblioteca.py — Repositorio de recursos digitales CEA
Docentes suben materiales (PDF, video, enlace) por módulo/tema.
Estudiantes y todo el personal pueden consultar.
"""
from fastapi import APIRouter, Depends, HTTPException
from database import get_db_connection
from routes.auth import get_current_user
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

def rows_to_dicts(cursor, rows):
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, r)) for r in rows]

TIPOS_VALIDOS = ["enlace","pdf","video","documento","imagen","presentacion","otro"]

class RecursoCreate(BaseModel):
    modulo_id: Optional[int] = None
    tema_id: Optional[int] = None
    titulo: str
    tipo: str = "enlace"
    url: str
    descripcion: Optional[str] = ""


@router.get("/")
def listar_recursos(modulo_id: Optional[int] = None, tipo: Optional[str] = None, q: Optional[str] = None):
    """Búsqueda pública de recursos. Filtros opcionales."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        filters, params = [], []
        if modulo_id:
            filters.append("r.modulo_id=%s"); params.append(modulo_id)
        if tipo:
            filters.append("r.tipo=%s"); params.append(tipo)
        if q:
            filters.append("(r.titulo ILIKE %s OR r.descripcion ILIKE %s)"); params += [f"%{q}%",f"%{q}%"]
        where = ("WHERE " + " AND ".join(filters)) if filters else ""
        cur.execute(f"""
            SELECT r.id, r.titulo, r.tipo, r.url, r.descripcion, r.fecha,
                   m.nombre as modulo, m.nivel,
                   c.nombre as carrera,
                   t.titulo as tema,
                   u.nombre as subido_por
            FROM recursos r
            LEFT JOIN modulos m ON r.modulo_id=m.id
            LEFT JOIN carreras c ON m.carrera_id=c.id
            LEFT JOIN temas t ON r.tema_id=t.id
            LEFT JOIN usuarios u ON r.subido_por=u.id
            {where}
            ORDER BY r.fecha DESC LIMIT 100
        """, params)
        return {"recursos": rows_to_dicts(cur, cur.fetchall())}
    finally: cur.close(); conn.close()


@router.post("/")
def subir_recurso(data: RecursoCreate, current_user: dict = Depends(get_current_user)):
    if current_user["rol"] not in ["docente","profesor","director","jefe_carrera","administrador"]:
        raise HTTPException(403,"Solo facilitadores y directivos pueden subir recursos")
    if data.tipo not in TIPOS_VALIDOS:
        raise HTTPException(400,f"Tipo inválido. Usa: {', '.join(TIPOS_VALIDOS)}")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO recursos (modulo_id,tema_id,titulo,tipo,url,descripcion,subido_por)
            VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """, (data.modulo_id,data.tema_id,data.titulo,data.tipo,data.url,data.descripcion or "",current_user["id"]))
        rid = cur.fetchone()[0]
        conn.commit()
        return {"id":rid,"mensaje":"Recurso publicado correctamente"}
    except Exception as e:
        conn.rollback(); raise HTTPException(500,str(e))
    finally: cur.close(); conn.close()


@router.delete("/{rid}")
def eliminar_recurso(rid: int, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT subido_por FROM recursos WHERE id=%s",(rid,))
        row = cur.fetchone()
        if not row: raise HTTPException(404,"Recurso no encontrado")
        if row[0] != current_user["id"] and current_user["rol"] not in ["director","administrador"]:
            raise HTTPException(403,"Sin permisos")
        cur.execute("DELETE FROM recursos WHERE id=%s",(rid,))
        conn.commit()
        return {"mensaje":"Recurso eliminado"}
    except HTTPException: raise
    except Exception as e:
        conn.rollback(); raise HTTPException(500,str(e))
    finally: cur.close(); conn.close()


@router.get("/mis-recursos")
def mis_recursos(current_user: dict = Depends(get_current_user)):
    """Recursos subidos por el docente autenticado."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT r.id, r.titulo, r.tipo, r.url, r.descripcion, r.fecha,
                   m.nombre as modulo
            FROM recursos r
            LEFT JOIN modulos m ON r.modulo_id=m.id
            WHERE r.subido_por=%s ORDER BY r.fecha DESC
        """, (current_user["id"],))
        return {"recursos": rows_to_dicts(cur, cur.fetchall())}
    finally: cur.close(); conn.close()
