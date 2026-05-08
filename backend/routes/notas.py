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
    nota_ser: float = 0
    nota_saber: float = 0
    nota_hacer: float = 0
    nota_decidir: float = 0
    nota_autoevaluacion: float = 0
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
            SELECT p.id, m.nombre AS modulo, m.nivel, p.estado, 
                   p.nota_ser, p.nota_saber, p.nota_hacer, p.nota_decidir, p.nota_autoevaluacion, p.nota_final as nota
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
            SELECT p.id, u.nombre, u.apellido, u.carnet, p.estado, 
                   p.nota_ser, p.nota_saber, p.nota_hacer, p.nota_decidir, p.nota_autoevaluacion, p.nota_final as nota,
                   p.modulo_id
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

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # Validar área para límites de notas
        cur.execute("""
            SELECT c.area 
            FROM modulos m 
            LEFT JOIN carreras c ON m.carrera_id = c.id 
            WHERE m.id = %s
        """, (data.modulo_id,))
        row = cur.fetchone()
        area = row[0] if row and row[0] else "Humanística" # Por defecto

        if area == "Técnica":
            if data.nota_saber > 30 or data.nota_hacer > 40:
                raise HTTPException(status_code=400, detail="En Área Técnica: Saber (max 30) y Hacer (max 40).")
        else:
            if data.nota_saber > 40 or data.nota_hacer > 30:
                raise HTTPException(status_code=400, detail="En Área Humanística: Saber (max 40) y Hacer (max 30).")
        
        if data.nota_ser > 10 or data.nota_decidir > 10 or data.nota_autoevaluacion > 10:
             raise HTTPException(status_code=400, detail="Ser, Decidir y Autoevaluación tienen un máximo de 10 puntos cada uno.")

        nota_final = data.nota_ser + data.nota_saber + data.nota_hacer + data.nota_decidir + data.nota_autoevaluacion

        # Calcular estado automáticamente si no viene
        estado = data.estado
        if estado is None:
            estado = "aprobado" if nota_final >= 60 else "reprobado"

        # Upsert: actualizar si existe, insertar si no
        cur.execute("""
            INSERT INTO progreso (usuario_id, modulo_id, nota_ser, nota_saber, nota_hacer, nota_decidir, nota_autoevaluacion, nota_final, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (usuario_id, modulo_id)
            DO UPDATE SET 
                nota_ser = EXCLUDED.nota_ser,
                nota_saber = EXCLUDED.nota_saber,
                nota_hacer = EXCLUDED.nota_hacer,
                nota_decidir = EXCLUDED.nota_decidir,
                nota_autoevaluacion = EXCLUDED.nota_autoevaluacion,
                nota_final = EXCLUDED.nota_final,
                estado = EXCLUDED.estado
        """, (data.usuario_id, data.modulo_id, data.nota_ser, data.nota_saber, data.nota_hacer, data.nota_decidir, data.nota_autoevaluacion, nota_final, estado))
        conn.commit()
        return {"mensaje": "Nota actualizada", "estado": estado, "nota_final": nota_final}
    except HTTPException as he:
        raise he
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
