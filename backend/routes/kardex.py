"""
kardex.py — Expediente académico completo del estudiante (Kardex)
Incluye: notas por módulo, asistencia, certificados, constancias, evaluaciones.
"""
from fastapi import APIRouter, Depends, HTTPException
from database import get_db_connection
from routes.auth import get_current_user

router = APIRouter()

def rows_to_dicts(cursor, rows):
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, r)) for r in rows]


@router.get("/{estudiante_id}")
def get_kardex(estudiante_id: int, current_user: dict = Depends(get_current_user)):
    """Retorna el kardex completo de un estudiante."""
    if current_user["id"] != estudiante_id and current_user["rol"] not in ["director","secretaria","jefe_carrera","administrador"]:
        raise HTTPException(403,"Sin permisos para ver este kardex")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Datos del estudiante
        cur.execute("""
            SELECT u.id, u.nombre, u.apellido, u.email, u.carnet, u.rol, u.estado,
                   u.fecha_registro, u.nivel_asignado
            FROM usuarios u WHERE u.id=%s
        """, (estudiante_id,))
        row = cur.fetchone()
        if not row: raise HTTPException(404,"Estudiante no encontrado")
        est = dict(zip([d[0] for d in cur.description], row))

        # Inscripciones y notas por módulo
        cur.execute("""
            SELECT m.nombre as modulo, m.nivel, m.periodo, m.area,
                   c.nombre as carrera,
                   p.nota_ser, p.nota_saber, p.nota_hacer, p.nota_decidir,
                   p.nota_autoevaluacion, p.nota_final, p.estado
            FROM progreso p
            JOIN modulos m ON p.modulo_id=m.id
            LEFT JOIN carreras c ON m.carrera_id=c.id
            WHERE p.usuario_id=%s
            ORDER BY c.nombre, m.nivel, m.orden
        """, (estudiante_id,))
        modulos = rows_to_dicts(cur, cur.fetchall())

        # Resumen por carrera
        aprobados = sum(1 for m in modulos if m.get("estado")=="aprobado")
        promedio = sum(float(m.get("nota_final") or 0) for m in modulos if m.get("nota_final")) / max(len([m for m in modulos if m.get("nota_final")]),1)

        # Asistencia resumen
        cur.execute("""
            SELECT m.nombre as modulo,
                   COUNT(*) as sesiones,
                   COUNT(CASE WHEN a.estado='presente' THEN 1 END) as presentes,
                   ROUND(COUNT(CASE WHEN a.estado='presente' THEN 1 END)*100.0/NULLIF(COUNT(*),0),1) as porcentaje
            FROM asistencia a JOIN modulos m ON a.modulo_id=m.id
            WHERE a.estudiante_id=%s GROUP BY m.id,m.nombre
        """, (estudiante_id,))
        asistencia = rows_to_dicts(cur, cur.fetchall())

        # Certificados
        cur.execute("""
            SELECT c.codigo_qr, c.fecha_emision, m.nombre as modulo, m.nivel
            FROM certificados c JOIN modulos m ON c.modulo_id=m.id
            WHERE c.estudiante_id=%s ORDER BY c.fecha_emision DESC
        """, (estudiante_id,))
        certificados = rows_to_dicts(cur, cur.fetchall())

        # Constancias
        cur.execute("""
            SELECT co.codigo, co.fecha_generacion, p.titulo
            FROM constancias co JOIN plantillas_certificado p ON co.plantilla_id=p.id
            WHERE co.estudiante_id=%s ORDER BY co.fecha_generacion DESC
        """, (estudiante_id,))
        constancias = rows_to_dicts(cur, cur.fetchall())

        return {
            "estudiante": est,
            "modulos": modulos,
            "resumen": {
                "total_modulos": len(modulos),
                "aprobados": aprobados,
                "reprobados": len(modulos) - aprobados,
                "promedio_general": round(promedio, 1)
            },
            "asistencia": asistencia,
            "certificados": certificados,
            "constancias": constancias
        }
    finally: cur.close(); conn.close()


@router.get("/mi-kardex")
def mi_kardex(current_user: dict = Depends(get_current_user)):
    return get_kardex(current_user["id"], current_user)
