"""
asistencia.py — Control de asistencia por sesión CEA
Docente registra asistencia. Estudiante y director ven reportes.
"""
from fastapi import APIRouter, Depends, HTTPException
from database import get_db_connection
from routes.auth import get_current_user
from pydantic import BaseModel
from typing import List, Optional
from datetime import date

router = APIRouter()

def rows_to_dicts(cursor, rows):
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, r)) for r in rows]

class RegistroAsistencia(BaseModel):
    estudiante_id: int
    estado: str = "presente"  # presente | ausente | tardanza | justificado
    observacion: Optional[str] = ""

class BatchAsistencia(BaseModel):
    modulo_id: int
    fecha: str  # YYYY-MM-DD
    registros: List[RegistroAsistencia]


@router.post("/registrar")
def registrar_asistencia(data: BatchAsistencia, current_user: dict = Depends(get_current_user)):
    if current_user["rol"] not in ["docente","profesor","director","administrador"]:
        raise HTTPException(403,"Sin permisos")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        guardados = 0
        for r in data.registros:
            cur.execute("""
                INSERT INTO asistencia (modulo_id,docente_id,estudiante_id,fecha,estado,observacion)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (modulo_id,estudiante_id,fecha)
                DO UPDATE SET estado=EXCLUDED.estado,observacion=EXCLUDED.observacion
            """, (data.modulo_id, current_user["id"], r.estudiante_id, data.fecha, r.estado, r.observacion or ""))
            guardados += 1
        conn.commit()
        return {"mensaje":f"✅ Asistencia registrada: {guardados} estudiantes","guardados":guardados}
    except Exception as e:
        conn.rollback(); raise HTTPException(500,str(e))
    finally: cur.close(); conn.close()


@router.get("/modulo/{modulo_id}")
def asistencia_modulo(modulo_id: int, fecha: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """Lista asistencia de un módulo. Opcionalmente filtra por fecha."""
    if current_user["rol"] not in ["docente","profesor","director","jefe_carrera","administrador"]:
        raise HTTPException(403,"Sin permisos")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Estudiantes del módulo
        cur.execute("""
            SELECT DISTINCT u.id, u.nombre, u.apellido, u.carnet
            FROM progreso p JOIN usuarios u ON p.usuario_id=u.id
            WHERE p.modulo_id=%s AND u.rol='estudiante'
            ORDER BY u.apellido
        """, (modulo_id,))
        estudiantes = rows_to_dicts(cur, cur.fetchall())

        # Fechas de sesiones
        cur.execute("SELECT DISTINCT fecha FROM asistencia WHERE modulo_id=%s ORDER BY fecha DESC LIMIT 30", (modulo_id,))
        fechas = [str(r[0]) for r in cur.fetchall()]

        # Asistencia de la fecha específica o la última
        fecha_q = fecha or (fechas[0] if fechas else str(date.today()))
        cur.execute("""
            SELECT a.estudiante_id, a.estado, a.observacion
            FROM asistencia a WHERE a.modulo_id=%s AND a.fecha=%s
        """, (modulo_id, fecha_q))
        hoy = {r[0]: {"estado": r[1], "obs": r[2]} for r in cur.fetchall()}

        for e in estudiantes:
            a = hoy.get(e["id"], {})
            e["estado"] = a.get("estado", "")
            e["observacion"] = a.get("obs", "")

        return {"estudiantes": estudiantes, "fechas": fechas, "fecha_actual": fecha_q}
    finally: cur.close(); conn.close()


@router.get("/reporte-estudiante/{estudiante_id}")
def reporte_estudiante(estudiante_id: int, current_user: dict = Depends(get_current_user)):
    """Reporte de asistencia por módulo para un estudiante."""
    if current_user["rol"] not in ["docente","director","administrador","jefe_carrera"] and current_user["id"] != estudiante_id:
        raise HTTPException(403,"Sin permisos")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT m.nombre as modulo, m.nivel,
                   COUNT(*) as total_sesiones,
                   COUNT(CASE WHEN a.estado='presente' THEN 1 END) as presentes,
                   COUNT(CASE WHEN a.estado='ausente' THEN 1 END) as ausentes,
                   COUNT(CASE WHEN a.estado='tardanza' THEN 1 END) as tardanzas,
                   COUNT(CASE WHEN a.estado='justificado' THEN 1 END) as justificados,
                   ROUND(COUNT(CASE WHEN a.estado='presente' THEN 1 END)*100.0/NULLIF(COUNT(*),0),1) as porcentaje
            FROM asistencia a
            JOIN modulos m ON a.modulo_id=m.id
            WHERE a.estudiante_id=%s
            GROUP BY m.id,m.nombre,m.nivel
            ORDER BY m.nivel
        """, (estudiante_id,))
        return {"modulos": rows_to_dicts(cur, cur.fetchall())}
    finally: cur.close(); conn.close()


@router.get("/mis-sesiones/{modulo_id}")
def mis_sesiones(modulo_id: int, current_user: dict = Depends(get_current_user)):
    """Mis sesiones de asistencia en un módulo (vista estudiante)."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT fecha, estado, observacion FROM asistencia
            WHERE modulo_id=%s AND estudiante_id=%s ORDER BY fecha DESC
        """, (modulo_id, current_user["id"]))
        return {"sesiones": rows_to_dicts(cur, cur.fetchall())}
    finally: cur.close(); conn.close()
