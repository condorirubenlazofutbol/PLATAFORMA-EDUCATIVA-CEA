"""
certificados.py — Sistema de Certificados Digitales CEA Pro
Emite certificados por módulo, nivel completo, y validación pública por código QR.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from database import get_db_connection
from routes.auth import get_current_user

router = APIRouter()


def rows_to_dicts(cursor, rows):
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, r)) for r in rows]


# ─── ENDPOINTS DEL ESTUDIANTE ────────────────────────────────────────────────

@router.get("/mis-certificados")
def mis_certificados(current_user: dict = Depends(get_current_user)):
    """Retorna todos los certificados del estudiante con info completa."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.id, c.codigo_qr, c.fecha_emision,
                   m.nombre as modulo, m.nivel, m.area,
                   car.nombre as carrera, car.area as area_carrera,
                   p.nota_final, p.estado,
                   u.nombre as estudiante_nombre, u.apellido as estudiante_apellido,
                   u.carnet
            FROM certificados c
            JOIN modulos m ON c.modulo_id = m.id
            LEFT JOIN carreras car ON m.carrera_id = car.id
            LEFT JOIN progreso p ON (p.usuario_id = c.estudiante_id AND p.modulo_id = c.modulo_id)
            JOIN usuarios u ON c.estudiante_id = u.id
            WHERE c.estudiante_id = %s
            ORDER BY c.fecha_emision DESC
        """, (current_user["id"],))
        certificados = rows_to_dicts(cur, cur.fetchall())

        # Verificar niveles completados
        cur.execute("""
            SELECT m.nivel, COUNT(p.id) as modulos_aprobados,
                   COUNT(DISTINCT m.id) FILTER (WHERE p.nota_final >= 51) as aprobados
            FROM progreso p
            JOIN modulos m ON p.modulo_id = m.id
            WHERE p.usuario_id = %s AND p.nota_final IS NOT NULL
            GROUP BY m.nivel
        """, (current_user["id"],))
        niveles_progreso = rows_to_dicts(cur, cur.fetchall())

        return {
            "certificados": certificados,
            "niveles_progreso": niveles_progreso
        }
    finally:
        cur.close(); conn.close()


@router.post("/emitir/{modulo_id}")
def emitir_certificado(modulo_id: int, current_user: dict = Depends(get_current_user)):
    """Emite un certificado de aprobación de módulo (requiere nota >= 51)."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Verificar que el módulo existe
        cur.execute("""
            SELECT m.id, m.nombre, m.nivel, m.area, c.nombre as carrera
            FROM modulos m
            LEFT JOIN carreras c ON m.carrera_id = c.id
            WHERE m.id = %s
        """, (modulo_id,))
        mod_row = cur.fetchone()
        if not mod_row:
            raise HTTPException(404, "Módulo no encontrado")
        mod = dict(zip([d[0] for d in cur.description], mod_row))

        # Verificar progreso y nota
        cur.execute("""
            SELECT nota_final, estado FROM progreso
            WHERE usuario_id = %s AND modulo_id = %s
        """, (current_user["id"], modulo_id))
        prog = cur.fetchone()
        if not prog:
            raise HTTPException(400, "No estás inscrito en este módulo")
        nota_final, estado = prog
        if nota_final is None or float(nota_final) < 51:
            raise HTTPException(400, f"Nota insuficiente ({nota_final}/100). Requiere mínimo 51 para certificar")

        # Verificar si ya existe el certificado
        cur.execute(
            "SELECT id FROM certificados WHERE estudiante_id=%s AND modulo_id=%s",
            (current_user["id"], modulo_id)
        )
        if cur.fetchone():
            raise HTTPException(400, "Ya tienes el certificado para este módulo")

        # Generar código QR único
        codigo_qr = f"CEA-{str(uuid.uuid4()).upper()[:16]}"

        cur.execute(
            "INSERT INTO certificados (estudiante_id, modulo_id, codigo_qr) VALUES (%s,%s,%s) RETURNING id, fecha_emision",
            (current_user["id"], modulo_id, codigo_qr)
        )
        row = cur.fetchone()
        conn.commit()

        return {
            "id": row[0],
            "codigo_qr": codigo_qr,
            "fecha_emision": row[1],
            "modulo": mod["nombre"],
            "nivel": mod["nivel"],
            "carrera": mod.get("carrera", ""),
            "nota": float(nota_final),
            "mensaje": "Certificado emitido exitosamente"
        }
    except HTTPException:
        conn.rollback(); raise
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


# ─── VERIFICACIÓN PÚBLICA ────────────────────────────────────────────────────

@router.get("/verificar/{codigo}")
def verificar_certificado(codigo: str):
    """Verificación pública por código QR. No requiere autenticación."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.id, c.codigo_qr, c.fecha_emision,
                   u.nombre, u.apellido, u.carnet,
                   m.nombre as modulo, m.nivel, m.area,
                   car.nombre as carrera,
                   p.nota_final
            FROM certificados c
            JOIN usuarios u ON c.estudiante_id = u.id
            JOIN modulos m ON c.modulo_id = m.id
            LEFT JOIN carreras car ON m.carrera_id = car.id
            LEFT JOIN progreso p ON (p.usuario_id = c.estudiante_id AND p.modulo_id = c.modulo_id)
            WHERE c.codigo_qr = %s
        """, (codigo,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Certificado no encontrado o código inválido")

        cols = [d[0] for d in cur.description]
        cert = dict(zip(cols, row))
        cert["valido"] = True
        cert["institucion"] = "CEA Prof. Herman Ortiz Camargo - Pailón, Santa Cruz, Bolivia"
        return cert
    finally:
        cur.close(); conn.close()


# ─── PANEL ADMINISTRADOR ─────────────────────────────────────────────────────

@router.get("/all")
def todos_los_certificados(current_user: dict = Depends(get_current_user)):
    """Admin/Director: lista todos los certificados emitidos."""
    if current_user["rol"] not in ["director", "secretaria", "administrador"]:
        raise HTTPException(403, "Sin permisos")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.id, c.codigo_qr, c.fecha_emision,
                   u.nombre as estudiante, u.apellido, u.carnet,
                   m.nombre as modulo, m.nivel,
                   car.nombre as carrera,
                   p.nota_final
            FROM certificados c
            JOIN usuarios u ON c.estudiante_id = u.id
            JOIN modulos m ON c.modulo_id = m.id
            LEFT JOIN carreras car ON m.carrera_id = car.id
            LEFT JOIN progreso p ON (p.usuario_id = c.estudiante_id AND p.modulo_id = c.modulo_id)
            ORDER BY c.fecha_emision DESC
            LIMIT 200
        """)
        return {"certificados": rows_to_dicts(cur, cur.fetchall())}
    finally:
        cur.close(); conn.close()


@router.get("/stats")
def stats_certificados(current_user: dict = Depends(get_current_user)):
    """Estadísticas de certificados por carrera y nivel."""
    if current_user["rol"] not in ["director", "secretaria", "administrador"]:
        raise HTTPException(403, "Sin permisos")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT car.nombre as carrera, m.nivel,
                   COUNT(c.id) as total_certificados
            FROM certificados c
            JOIN modulos m ON c.modulo_id = m.id
            LEFT JOIN carreras car ON m.carrera_id = car.id
            GROUP BY car.nombre, m.nivel
            ORDER BY car.nombre, m.nivel
        """)
        return {"stats": rows_to_dicts(cur, cur.fetchall())}
    finally:
        cur.close(); conn.close()
