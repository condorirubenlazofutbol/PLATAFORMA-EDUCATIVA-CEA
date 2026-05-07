from fastapi import APIRouter, Depends, HTTPException
from database import get_db_connection
from routes.auth import get_current_user
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

def rows_to_dicts(cursor, rows):
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, r)) for r in rows]

class NotaUpdate(BaseModel):
    usuario_id: int
    modulo_id: int
    nota: float
    estado: Optional[str] = None  # 'aprobado', 'reprobado', 'cursando'

class InscribirEstudiante(BaseModel):
    usuario_id: int
    modulo_id: int


# ── GET: Mis notas (Estudiante) ────────────────────────────────────────────
@router.get("/mis-notas")
def mis_notas(current_user: dict = Depends(get_current_user)):
    """Devuelve el progreso académico del estudiante autenticado."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.id, m.nombre AS modulo, m.nivel, p.estado, p.nota
            FROM progreso p
            JOIN modulos m ON p.modulo_id = m.id
            WHERE p.usuario_id = %s
            ORDER BY m.nivel, m.orden
        """, (current_user["id"],))
        rows = rows_to_dicts(cur, cur.fetchall())
        return {"progreso": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close(); conn.close()


# ── GET: Notas de un módulo (Docente/Director) ────────────────────────────
@router.get("/modulo/{modulo_id}")
def notas_por_modulo(modulo_id: int, current_user: dict = Depends(get_current_user)):
    """Lista todos los estudiantes y sus notas para un módulo dado."""
    if current_user["rol"] not in ["docente", "profesor", "director", "jefe_carrera", "administrador"]:
        raise HTTPException(status_code=403, detail="Sin permisos")

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.id, u.nombre, u.apellido, u.carnet, p.estado, p.nota, p.modulo_id
            FROM progreso p
            JOIN usuarios u ON p.usuario_id = u.id
            WHERE p.modulo_id = %s
            ORDER BY u.apellido
        """, (modulo_id,))
        rows = rows_to_dicts(cur, cur.fetchall())
        return {"alumnos": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close(); conn.close()


# ── PUT: Actualizar nota de un estudiante (Docente) ──────────────────────
@router.put("/actualizar")
def actualizar_nota(data: NotaUpdate, current_user: dict = Depends(get_current_user)):
    """Permite al docente guardar o actualizar la nota de un estudiante."""
    if current_user["rol"] not in ["docente", "profesor", "director", "administrador"]:
        raise HTTPException(status_code=403, detail="Sin permisos para calificar")

    # Calcular estado automáticamente si no viene
    estado = data.estado
    if estado is None:
        estado = "aprobado" if data.nota >= 60 else "reprobado"

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Upsert: actualizar si existe, insertar si no
        cur.execute("""
            INSERT INTO progreso (usuario_id, modulo_id, nota, estado)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (usuario_id, modulo_id)
            DO UPDATE SET nota = EXCLUDED.nota, estado = EXCLUDED.estado
        """, (data.usuario_id, data.modulo_id, data.nota, estado))
        conn.commit()
        return {"mensaje": "Nota actualizada", "estado": estado}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close(); conn.close()


# ── POST: Inscribir un estudiante en un módulo ───────────────────────────
@router.post("/inscribir")
def inscribir_estudiante(data: InscribirEstudiante, current_user: dict = Depends(get_current_user)):
    """Inscribe a un estudiante en un módulo (Secretaria o Docente)."""
    if current_user["rol"] not in ["secretaria", "director", "jefe_carrera", "administrador"]:
        raise HTTPException(status_code=403, detail="Sin permisos para inscribir")

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO progreso (usuario_id, modulo_id, estado)
            VALUES (%s, %s, 'cursando')
            ON CONFLICT (usuario_id, modulo_id) DO NOTHING
        """, (data.usuario_id, data.modulo_id))
        conn.commit()
        return {"mensaje": "Estudiante inscrito correctamente"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close(); conn.close()


# ── GET: Resumen de estadísticas globales ────────────────────────────────
@router.get("/estadisticas")
def estadisticas(current_user: dict = Depends(get_current_user)):
    """Resumen de aprobados, reprobados y en curso del subsistema."""
    if current_user["rol"] not in ["director", "jefe_carrera", "secretaria", "administrador"]:
        raise HTTPException(status_code=403, detail="Sin permisos")

    subsistema_id = current_user.get("subsistema_id")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Filtrar por subsistema si aplica
        filtro = "AND u.subsistema_id = %s" if subsistema_id else ""
        params = (subsistema_id,) if subsistema_id else ()

        cur.execute(f"""
            SELECT p.estado, COUNT(*) AS total
            FROM progreso p
            JOIN usuarios u ON p.usuario_id = u.id
            WHERE u.rol = 'estudiante' {filtro}
            GROUP BY p.estado
        """, params)
        rows = cur.fetchall()
        stats = {r[0]: r[1] for r in rows}

        return {
            "aprobados": stats.get("aprobado", 0),
            "reprobados": stats.get("reprobado", 0),
            "cursando": stats.get("cursando", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close(); conn.close()
