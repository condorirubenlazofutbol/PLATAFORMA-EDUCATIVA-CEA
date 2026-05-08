"""
constancias.py — Sistema de Plantillas de Certificados/Constancias CEA
El director crea plantillas con texto personalizable por nivel/carrera.
Los estudiantes generan sus constancias con fecha actual y datos propios.
"""
import uuid
import json
from fastapi import APIRouter, Depends, HTTPException
from database import get_db_connection
from routes.auth import get_current_user
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


def rows_to_dicts(cursor, rows):
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, r)) for r in rows]


# ─── MODELOS ──────────────────────────────────────────────────────────────────

class PlantillaCreate(BaseModel):
    titulo: str
    nivel: Optional[str] = None
    carrera_id: Optional[int] = None
    area: Optional[str] = None
    cuerpo_texto: str
    pie_texto: Optional[str] = ""
    activa: Optional[bool] = True


class PlantillaUpdate(BaseModel):
    titulo: Optional[str] = None
    nivel: Optional[str] = None
    cuerpo_texto: Optional[str] = None
    pie_texto: Optional[str] = None
    activa: Optional[bool] = None


# ─── DIRECTOR: GESTIÓN DE PLANTILLAS ─────────────────────────────────────────

@router.get("/plantillas")
def listar_plantillas(current_user: dict = Depends(get_current_user)):
    """Lista todas las plantillas. Director/Admin ven todas; docentes las activas."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if current_user["rol"] in ["director", "administrador"]:
            cur.execute("""
                SELECT p.id, p.titulo, p.nivel, p.area, p.activa,
                       c.nombre as carrera, p.cuerpo_texto, p.pie_texto,
                       p.fecha_creacion, u.nombre as creado_por
                FROM plantillas_certificado p
                LEFT JOIN carreras c ON p.carrera_id = c.id
                LEFT JOIN usuarios u ON p.creado_por = u.id
                ORDER BY p.fecha_creacion DESC
            """)
        else:
            cur.execute("""
                SELECT p.id, p.titulo, p.nivel, p.area, p.activa,
                       c.nombre as carrera, p.cuerpo_texto, p.pie_texto,
                       p.fecha_creacion
                FROM plantillas_certificado p
                LEFT JOIN carreras c ON p.carrera_id = c.id
                WHERE p.activa = TRUE
                ORDER BY p.fecha_creacion DESC
            """)
        return {"plantillas": rows_to_dicts(cur, cur.fetchall())}
    finally:
        cur.close(); conn.close()


@router.post("/plantillas")
def crear_plantilla(data: PlantillaCreate, current_user: dict = Depends(get_current_user)):
    """El director crea una plantilla de certificado/constancia."""
    if current_user["rol"] not in ["director", "administrador"]:
        raise HTTPException(403, "Solo el director puede crear plantillas de certificados")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO plantillas_certificado
                (titulo, nivel, carrera_id, area, cuerpo_texto, pie_texto, activa, creado_por)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """, (
            data.titulo, data.nivel, data.carrera_id, data.area,
            data.cuerpo_texto, data.pie_texto or "", data.activa, current_user["id"]
        ))
        pid = cur.fetchone()[0]
        conn.commit()
        return {"id": pid, "mensaje": "Plantilla creada correctamente"}
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


@router.put("/plantillas/{pid}")
def editar_plantilla(pid: int, data: PlantillaUpdate, current_user: dict = Depends(get_current_user)):
    if current_user["rol"] not in ["director", "administrador"]:
        raise HTTPException(403, "Sin permisos")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        updates, vals = [], []
        for field in ["titulo", "nivel", "cuerpo_texto", "pie_texto", "activa"]:
            v = getattr(data, field)
            if v is not None:
                updates.append(f"{field}=%s"); vals.append(v)
        if updates:
            vals.append(pid)
            cur.execute(f"UPDATE plantillas_certificado SET {','.join(updates)} WHERE id=%s", vals)
        conn.commit()
        return {"mensaje": "Plantilla actualizada"}
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


@router.delete("/plantillas/{pid}")
def eliminar_plantilla(pid: int, current_user: dict = Depends(get_current_user)):
    if current_user["rol"] not in ["director", "administrador"]:
        raise HTTPException(403, "Sin permisos")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM plantillas_certificado WHERE id=%s", (pid,))
        conn.commit()
        return {"mensaje": "Plantilla eliminada"}
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


# ─── ESTUDIANTE: GENERAR CONSTANCIA ──────────────────────────────────────────

@router.get("/disponibles")
def plantillas_disponibles(current_user: dict = Depends(get_current_user)):
    """
    Plantillas disponibles para el estudiante según su carrera/nivel inscrito.
    Incluye qué constancias ya generó.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Obtener inscripciones activas del estudiante
        cur.execute("""
            SELECT m.nivel, m.carrera_id, c.nombre as carrera, c.area
            FROM progreso p
            JOIN modulos m ON p.modulo_id = m.id
            LEFT JOIN carreras c ON m.carrera_id = c.id
            WHERE p.usuario_id = %s
            GROUP BY m.nivel, m.carrera_id, c.nombre, c.area
        """, (current_user["id"],))
        inscripciones = rows_to_dicts(cur, cur.fetchall())

        niveles = [i["nivel"] for i in inscripciones]
        carreras = [i["carrera_id"] for i in inscripciones if i["carrera_id"]]

        # Plantillas que aplican al estudiante
        if niveles or carreras:
            cur.execute("""
                SELECT p.id, p.titulo, p.nivel, p.area, p.cuerpo_texto, p.pie_texto,
                       c.nombre as carrera
                FROM plantillas_certificado p
                LEFT JOIN carreras c ON p.carrera_id = c.id
                WHERE p.activa = TRUE
                  AND (
                    p.nivel IS NULL
                    OR p.nivel = ANY(%s)
                    OR p.carrera_id = ANY(%s)
                  )
                ORDER BY p.titulo
            """, (niveles if niveles else [''], carreras if carreras else [0]))
        else:
            # Sin inscripciones: mostrar plantillas sin nivel/carrera específica
            cur.execute("""
                SELECT p.id, p.titulo, p.nivel, p.area, p.cuerpo_texto, p.pie_texto,
                       c.nombre as carrera
                FROM plantillas_certificado p
                LEFT JOIN carreras c ON p.carrera_id = c.id
                WHERE p.activa = TRUE AND p.nivel IS NULL AND p.carrera_id IS NULL
            """)
        plantillas = rows_to_dicts(cur, cur.fetchall())

        # Marcar cuáles ya generó el estudiante
        cur.execute("""
            SELECT plantilla_id, codigo, fecha_generacion
            FROM constancias WHERE estudiante_id=%s
        """, (current_user["id"],))
        generadas = {r[0]: {"codigo": r[1], "fecha": r[2]} for r in cur.fetchall()}

        for p in plantillas:
            p["ya_generada"] = p["id"] in generadas
            if p["ya_generada"]:
                p["codigo"] = generadas[p["id"]]["codigo"]
                p["fecha_generacion"] = generadas[p["id"]]["fecha"]

        return {"plantillas": plantillas, "inscripciones": inscripciones}
    finally:
        cur.close(); conn.close()


@router.post("/generar/{plantilla_id}")
def generar_constancia(plantilla_id: int, current_user: dict = Depends(get_current_user)):
    """El estudiante genera su constancia. Si ya existe, la retorna."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Verificar si ya existe
        cur.execute(
            "SELECT id, codigo, fecha_generacion FROM constancias WHERE estudiante_id=%s AND plantilla_id=%s",
            (current_user["id"], plantilla_id)
        )
        existing = cur.fetchone()

        # Datos del estudiante
        cur.execute("""
            SELECT u.nombre, u.apellido, u.carnet, u.email,
                   m.nivel, c.nombre as carrera, c.area
            FROM usuarios u
            LEFT JOIN progreso p ON p.usuario_id = u.id
            LEFT JOIN modulos m ON p.modulo_id = m.id
            LEFT JOIN carreras c ON m.carrera_id = c.id
            WHERE u.id = %s
            LIMIT 1
        """, (current_user["id"],))
        row = cur.fetchone()
        est = dict(zip([d[0] for d in cur.description], row)) if row else {}

        # Plantilla
        cur.execute("SELECT * FROM plantillas_certificado WHERE id=%s AND activa=TRUE", (plantilla_id,))
        prow = cur.fetchone()
        if not prow:
            raise HTTPException(404, "Plantilla no encontrada o inactiva")
        plantilla = dict(zip([d[0] for d in cur.description], prow))

        if existing:
            return {
                "codigo": existing[1],
                "fecha_generacion": existing[2],
                "estudiante": est,
                "plantilla": plantilla,
                "es_nueva": False
            }

        codigo = f"CEA-C-{str(uuid.uuid4()).upper()[:14]}"
        snapshot = {
            "nombre": est.get("nombre", ""),
            "apellido": est.get("apellido", ""),
            "carnet": est.get("carnet", ""),
            "nivel": est.get("nivel", ""),
            "carrera": est.get("carrera", ""),
            "plantilla_titulo": plantilla["titulo"]
        }
        cur.execute("""
            INSERT INTO constancias (estudiante_id, plantilla_id, codigo, datos_snapshot)
            VALUES (%s,%s,%s,%s) RETURNING id, fecha_generacion
        """, (current_user["id"], plantilla_id, codigo, json.dumps(snapshot)))
        row2 = cur.fetchone()
        conn.commit()

        return {
            "codigo": codigo,
            "fecha_generacion": row2[1],
            "estudiante": est,
            "plantilla": plantilla,
            "es_nueva": True
        }
    except HTTPException:
        conn.rollback(); raise
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


@router.get("/verificar-constancia/{codigo}")
def verificar_constancia(codigo: str):
    """Verificación pública de constancia por código."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.codigo, c.fecha_generacion, c.datos_snapshot,
                   u.nombre, u.apellido, u.carnet,
                   p.titulo as plantilla_titulo, p.nivel, p.area
            FROM constancias c
            JOIN usuarios u ON c.estudiante_id = u.id
            JOIN plantillas_certificado p ON c.plantilla_id = p.id
            WHERE c.codigo = %s
        """, (codigo,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Constancia no encontrada")
        cols = [d[0] for d in cur.description]
        data = dict(zip(cols, row))
        data["valido"] = True
        return data
    finally:
        cur.close(); conn.close()


@router.get("/mis-constancias")
def mis_constancias(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.id, c.codigo, c.fecha_generacion, c.datos_snapshot,
                   p.titulo, p.nivel, p.area, p.cuerpo_texto, p.pie_texto
            FROM constancias c
            JOIN plantillas_certificado p ON c.plantilla_id = p.id
            WHERE c.estudiante_id = %s
            ORDER BY c.fecha_generacion DESC
        """, (current_user["id"],))
        return {"constancias": rows_to_dicts(cur, cur.fetchall())}
    finally:
        cur.close(); conn.close()


@router.get("/admin/todas-constancias")
def todas_constancias(current_user: dict = Depends(get_current_user)):
    if current_user["rol"] not in ["director", "administrador", "secretaria"]:
        raise HTTPException(403, "Sin permisos")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.codigo, c.fecha_generacion,
                   u.nombre, u.apellido, u.carnet,
                   p.titulo as plantilla, p.nivel
            FROM constancias c
            JOIN usuarios u ON c.estudiante_id = u.id
            JOIN plantillas_certificado p ON c.plantilla_id = p.id
            ORDER BY c.fecha_generacion DESC LIMIT 300
        """)
        return {"constancias": rows_to_dicts(cur, cur.fetchall())}
    finally:
        cur.close(); conn.close()
