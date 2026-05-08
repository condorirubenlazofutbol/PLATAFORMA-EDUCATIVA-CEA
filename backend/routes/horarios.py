"""
horarios.py — Gestión de horarios semanales por carrera/nivel
Director/Jefe crea, docentes y estudiantes consultan.
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

class HorarioCreate(BaseModel):
    carrera_id: int
    nivel: Optional[str] = None
    dia: str  # Lunes, Martes, ...
    hora_inicio: str  # "08:00"
    hora_fin: str     # "10:00"
    modulo_id: Optional[int] = None
    docente_id: Optional[int] = None
    aula: Optional[str] = ""


@router.get("/carrera/{carrera_id}")
def horario_carrera(carrera_id: int, nivel: Optional[str] = None):
    """Retorna el horario completo de una carrera, agrupado por día."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        query = """
            SELECT h.id, h.dia, h.hora_inicio, h.hora_fin, h.aula, h.nivel,
                   m.nombre as modulo, c.nombre as carrera,
                   u.nombre as docente, u.apellido as docente_apellido
            FROM horarios h
            LEFT JOIN modulos m ON h.modulo_id=m.id
            LEFT JOIN carreras c ON h.carrera_id=c.id
            LEFT JOIN usuarios u ON h.docente_id=u.id
            WHERE h.carrera_id=%s
        """
        params = [carrera_id]
        if nivel:
            query += " AND h.nivel=%s"
            params.append(nivel)
        query += " ORDER BY CASE h.dia WHEN 'Lunes' THEN 1 WHEN 'Martes' THEN 2 WHEN 'Miércoles' THEN 3 WHEN 'Jueves' THEN 4 WHEN 'Viernes' THEN 5 WHEN 'Sábado' THEN 6 ELSE 7 END, h.hora_inicio"
        cur.execute(query, params)
        rows = rows_to_dicts(cur, cur.fetchall())
        dias = {}
        for r in rows:
            d = r["dia"]
            if d not in dias: dias[d] = []
            dias[d].append(r)
        return {"horario": dias, "total": len(rows)}
    finally: cur.close(); conn.close()


@router.get("/mi-horario")
def mi_horario(current_user: dict = Depends(get_current_user)):
    """Horario del docente o estudiante autenticado."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if current_user["rol"] in ["docente","profesor"]:
            cur.execute("""
                SELECT h.id, h.dia, h.hora_inicio, h.hora_fin, h.aula, h.nivel,
                       m.nombre as modulo, c.nombre as carrera
                FROM horarios h
                LEFT JOIN modulos m ON h.modulo_id=m.id
                LEFT JOIN carreras c ON h.carrera_id=c.id
                WHERE h.docente_id=%s
                ORDER BY CASE h.dia WHEN 'Lunes' THEN 1 WHEN 'Martes' THEN 2 WHEN 'Miércoles' THEN 3 WHEN 'Jueves' THEN 4 WHEN 'Viernes' THEN 5 WHEN 'Sábado' THEN 6 ELSE 7 END, h.hora_inicio
            """, (current_user["id"],))
        else:
            # Estudiante: buscar su carrera desde progreso
            cur.execute("""
                SELECT DISTINCT m.carrera_id FROM progreso p
                JOIN modulos m ON p.modulo_id=m.id WHERE p.usuario_id=%s LIMIT 1
            """, (current_user["id"],))
            row = cur.fetchone()
            if not row: return {"horario": {}, "total": 0}
            cur.execute("""
                SELECT h.id, h.dia, h.hora_inicio, h.hora_fin, h.aula, h.nivel,
                       m.nombre as modulo, c.nombre as carrera,
                       u.nombre as docente, u.apellido as docente_apellido
                FROM horarios h
                LEFT JOIN modulos m ON h.modulo_id=m.id
                LEFT JOIN carreras c ON h.carrera_id=c.id
                LEFT JOIN usuarios u ON h.docente_id=u.id
                WHERE h.carrera_id=%s
                ORDER BY CASE h.dia WHEN 'Lunes' THEN 1 WHEN 'Martes' THEN 2 WHEN 'Miércoles' THEN 3 WHEN 'Jueves' THEN 4 WHEN 'Viernes' THEN 5 WHEN 'Sábado' THEN 6 ELSE 7 END, h.hora_inicio
            """, (row[0],))
        rows = rows_to_dicts(cur, cur.fetchall())
        dias = {}
        for r in rows:
            d = r["dia"]
            if d not in dias: dias[d] = []
            dias[d].append(r)
        return {"horario": dias, "total": len(rows)}
    finally: cur.close(); conn.close()


@router.post("/")
def crear_horario(data: HorarioCreate, current_user: dict = Depends(get_current_user)):
    if current_user["rol"] not in ["director","jefe_carrera","administrador"]:
        raise HTTPException(403,"Sin permisos")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO horarios (carrera_id,nivel,dia,hora_inicio,hora_fin,modulo_id,docente_id,aula)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """, (data.carrera_id,data.nivel,data.dia,data.hora_inicio,data.hora_fin,data.modulo_id,data.docente_id,data.aula or ""))
        hid = cur.fetchone()[0]
        conn.commit()
        return {"id":hid,"mensaje":"Horario creado"}
    except Exception as e:
        conn.rollback(); raise HTTPException(500,str(e))
    finally: cur.close(); conn.close()


@router.delete("/{hid}")
def eliminar_horario(hid: int, current_user: dict = Depends(get_current_user)):
    if current_user["rol"] not in ["director","jefe_carrera","administrador"]:
        raise HTTPException(403,"Sin permisos")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM horarios WHERE id=%s",(hid,))
        conn.commit()
        return {"mensaje":"Eliminado"}
    except Exception as e:
        conn.rollback(); raise HTTPException(500,str(e))
    finally: cur.close(); conn.close()
