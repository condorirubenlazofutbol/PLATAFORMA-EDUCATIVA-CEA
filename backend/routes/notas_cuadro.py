"""
notas_cuadro.py — Endpoint para el Cuadro de Valoración Final CEA
Retorna todos los datos necesarios para generar el cuadro según área (Técnica/Humanística).
Soporta guardado masivo (batch) y descarga como JSON para Excel.
"""
from fastapi import APIRouter, Depends, HTTPException
from database import get_db_connection
from routes.auth import get_current_user
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter()


def rows_to_dicts(cursor, rows):
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, r)) for r in rows]


class NotaBatch(BaseModel):
    usuario_id: int
    nota_ser: float = 0
    nota_saber: float = 0
    nota_hacer: float = 0
    nota_decidir: float = 0
    auto_ser: float = 0        # Autoevaluación SER (max 5)
    auto_decidir: float = 0   # Autoevaluación DECIDIR (max 5)
    observacion: Optional[str] = None  # 'PROMOVIDO/A', 'POSTERGADO/A', 'RETIRADO/A'


class GuardarCuadroBody(BaseModel):
    modulo_id: int
    notas: List[NotaBatch]


@router.get("/cuadro/{modulo_id}")
def get_cuadro(modulo_id: int, current_user: dict = Depends(get_current_user)):
    """
    Retorna el cuadro de valoración completo para un módulo:
    - Info del módulo, carrera y área
    - Lista de estudiantes con sus notas (si ya tienen)
    - Formato correcto para Técnica vs Humanística
    """
    if current_user["rol"] not in ["docente", "profesor", "director", "jefe_carrera", "administrador"]:
        raise HTTPException(403, "Sin permisos")

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Info del módulo
        cur.execute("""
            SELECT m.id, m.nombre, m.nivel, m.subnivel, m.periodo, m.area,
                   c.nombre as carrera, c.area as carrera_area, c.descripcion as campo_saber,
                   u.nombre as facilitador, u.apellido as facilitador_apellido
            FROM modulos m
            LEFT JOIN carreras c ON m.carrera_id = c.id
            LEFT JOIN usuarios u ON u.id = %s
            WHERE m.id = %s
        """, (current_user["id"], modulo_id))
        mod_row = cur.fetchone()
        if not mod_row:
            raise HTTPException(404, "Módulo no encontrado")
        mod = dict(zip([d[0] for d in cur.description], mod_row))

        # Determinar área (puede venir del módulo o de la carrera)
        area = mod.get("area") or mod.get("carrera_area") or "Humanística"
        mod["area_efectiva"] = area

        # Temas del módulo
        cur.execute("SELECT numero, titulo FROM temas WHERE modulo_id=%s ORDER BY numero", (modulo_id,))
        mod["temas"] = rows_to_dicts(cur, cur.fetchall())

        # Estudiantes con sus notas en este módulo
        cur.execute("""
            SELECT
                u.id, u.nombre, u.apellido, u.carnet, u.estado as estado_usuario,
                p.nota_ser, p.nota_saber, p.nota_hacer, p.nota_decidir,
                p.nota_autoevaluacion, p.nota_final, p.estado as estado_progreso,
                COALESCE(p.nota_ser, 0) as ser_h,
                COALESCE(p.nota_saber, 0) as saber_h,
                COALESCE(p.nota_hacer, 0) as hacer_h,
                COALESCE(p.nota_decidir, 0) as decidir_h
            FROM progreso p
            JOIN usuarios u ON p.usuario_id = u.id
            WHERE p.modulo_id = %s AND u.rol = 'estudiante'
            ORDER BY u.apellido, u.nombre
        """, (modulo_id,))
        estudiantes = rows_to_dicts(cur, cur.fetchall())

        # Calcular auto_ser y auto_decidir desde nota_autoevaluacion (split 5/5)
        for e in estudiantes:
            auto = float(e.get("nota_autoevaluacion") or 0)
            e["auto_ser"] = min(auto / 2, 5) if auto > 0 else 0
            e["auto_decidir"] = auto - e["auto_ser"] if auto > 0 else 0

            # Calcular observación
            nota = float(e.get("nota_final") or 0)
            if e.get("estado_usuario") == "retirado" or e.get("estado_progreso") == "retirado":
                e["observacion"] = "RETIRADO/A"
            elif nota >= 51:
                e["observacion"] = "PROMOVIDO/A"
            elif nota > 0:
                e["observacion"] = "POSTERGADO/A"
            else:
                e["observacion"] = ""

        return {
            "modulo": mod,
            "area": area,
            "estudiantes": estudiantes,
            "formato": {
                "tecnica": {"saber_max": 30, "hacer_max": 40},
                "humanistica": {"saber_max": 40, "hacer_max": 30}
            }
        }
    finally:
        cur.close(); conn.close()


@router.post("/cuadro/guardar-batch")
def guardar_cuadro_batch(body: GuardarCuadroBody, current_user: dict = Depends(get_current_user)):
    """Guarda las notas de todos los estudiantes del cuadro de una sola vez."""
    if current_user["rol"] not in ["docente", "profesor", "director", "jefe_carrera", "administrador"]:
        raise HTTPException(403, "Sin permisos")

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Determinar área del módulo para validar límites
        cur.execute("SELECT c.area FROM modulos m LEFT JOIN carreras c ON m.carrera_id=c.id WHERE m.id=%s",
                    (body.modulo_id,))
        row = cur.fetchone()
        area = row[0] if row and row[0] else "Humanística"

        guardados = 0
        for nota in body.notas:
            # Autoevaluación = auto_ser + auto_decidir (max 10 total)
            nota_auto = min(nota.auto_ser + nota.auto_decidir, 10)
            nota_final = nota.nota_ser + nota.nota_saber + nota.nota_hacer + nota.nota_decidir + nota_auto

            # Estado según nota final (≥51 = aprobado en CEA)
            estado = "aprobado" if nota_final >= 51 else "reprobado"
            if nota.observacion == "RETIRADO/A":
                estado = "retirado"

            cur.execute("""
                INSERT INTO progreso
                    (usuario_id, modulo_id, nota_ser, nota_saber, nota_hacer, nota_decidir, nota_autoevaluacion, nota_final, estado)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (usuario_id, modulo_id) DO UPDATE SET
                    nota_ser = EXCLUDED.nota_ser,
                    nota_saber = EXCLUDED.nota_saber,
                    nota_hacer = EXCLUDED.nota_hacer,
                    nota_decidir = EXCLUDED.nota_decidir,
                    nota_autoevaluacion = EXCLUDED.nota_autoevaluacion,
                    nota_final = EXCLUDED.nota_final,
                    estado = EXCLUDED.estado
            """, (nota.usuario_id, body.modulo_id,
                  nota.nota_ser, nota.nota_saber, nota.nota_hacer, nota.nota_decidir,
                  nota_auto, nota_final, estado))
            guardados += 1

        conn.commit()
        return {"mensaje": f"✅ Notas guardadas: {guardados} estudiantes", "guardados": guardados}
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


@router.get("/mis-modulos-docente")
def mis_modulos_docente(current_user: dict = Depends(get_current_user)):
    """
    Retorna los módulos asignados al docente según su nivel_asignado.
    Para directores/admins retorna todos los módulos.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        if current_user["rol"] in ["director", "administrador"]:
            cur.execute("""
                SELECT m.id, m.nombre, m.nivel, m.periodo, m.area,
                       c.nombre as carrera, c.area as carrera_area,
                       COUNT(p.id) as total_estudiantes
                FROM modulos m
                LEFT JOIN carreras c ON m.carrera_id = c.id
                LEFT JOIN progreso p ON p.modulo_id = m.id
                GROUP BY m.id, m.nombre, m.nivel, m.periodo, m.area, c.nombre, c.area
                ORDER BY c.nombre, m.nivel, m.orden
            """)
        else:
            nivel = current_user.get("nivel_asignado", "")
            cur.execute("""
                SELECT m.id, m.nombre, m.nivel, m.periodo, m.area,
                       c.nombre as carrera, c.area as carrera_area,
                       COUNT(p.id) as total_estudiantes
                FROM modulos m
                LEFT JOIN carreras c ON m.carrera_id = c.id
                LEFT JOIN progreso p ON p.modulo_id = m.id
                WHERE m.nivel ILIKE %s OR m.nivel ILIKE %s
                GROUP BY m.id, m.nombre, m.nivel, m.periodo, m.area, c.nombre, c.area
                ORDER BY c.nombre, m.nivel, m.orden
            """, (f"%{nivel}%", f"%{nivel.split('-')[0].strip() if '-' in nivel else nivel}%"))

        return {"modulos": rows_to_dicts(cur, cur.fetchall())}
    finally:
        cur.close(); conn.close()
