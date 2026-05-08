"""
estadisticas.py — Dashboard de estadísticas institucionales CEA
KPIs en tiempo real: matriculados, aprobados, deserción, por carrera/nivel/área.
"""
from fastapi import APIRouter, Depends, HTTPException
from database import get_db_connection
from routes.auth import get_current_user

router = APIRouter()

def rows_to_dicts(cursor, rows):
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, r)) for r in rows]


@router.get("/resumen")
def resumen_general(current_user: dict = Depends(get_current_user)):
    if current_user["rol"] not in ["director","administrador","jefe_carrera","secretaria"]:
        raise HTTPException(403,"Sin permisos")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM usuarios WHERE rol='estudiante' AND estado='activo'")
        total_estudiantes = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM usuarios WHERE rol IN ('docente','profesor')")
        total_docentes = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM modulos")
        total_modulos = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM carreras")
        total_carreras = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM progreso WHERE estado='aprobado'")
        total_aprobados = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM progreso WHERE nota_final IS NOT NULL AND nota_final < 51")
        total_reprobados = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM certificados")
        total_certificados = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM constancias")
        total_constancias = cur.fetchone()[0]

        return {
            "total_estudiantes": total_estudiantes,
            "total_docentes": total_docentes,
            "total_modulos": total_modulos,
            "total_carreras": total_carreras,
            "total_aprobados": total_aprobados,
            "total_reprobados": total_reprobados,
            "total_certificados": total_certificados,
            "total_constancias": total_constancias,
            "tasa_aprobacion": round(total_aprobados / max(total_aprobados + total_reprobados, 1) * 100, 1)
        }
    finally: cur.close(); conn.close()


@router.get("/por-carrera")
def por_carrera(current_user: dict = Depends(get_current_user)):
    if current_user["rol"] not in ["director","administrador","jefe_carrera","secretaria"]:
        raise HTTPException(403,"Sin permisos")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.nombre as carrera, c.area,
                   COUNT(DISTINCT p.usuario_id) as inscritos,
                   COUNT(DISTINCT CASE WHEN p.estado='aprobado' THEN p.usuario_id END) as aprobados,
                   COUNT(DISTINCT CASE WHEN p.nota_final IS NOT NULL AND p.nota_final<51 THEN p.usuario_id END) as reprobados,
                   COUNT(DISTINCT m.id) as modulos
            FROM carreras c
            LEFT JOIN modulos m ON m.carrera_id = c.id
            LEFT JOIN progreso p ON p.modulo_id = m.id
            GROUP BY c.id, c.nombre, c.area
            ORDER BY c.area, c.nombre
        """)
        return {"carreras": rows_to_dicts(cur, cur.fetchall())}
    finally: cur.close(); conn.close()


@router.get("/por-nivel")
def por_nivel(current_user: dict = Depends(get_current_user)):
    if current_user["rol"] not in ["director","administrador","jefe_carrera","secretaria"]:
        raise HTTPException(403,"Sin permisos")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT m.nivel,
                   COUNT(DISTINCT p.usuario_id) as inscritos,
                   COUNT(DISTINCT CASE WHEN p.estado='aprobado' THEN p.usuario_id END) as aprobados,
                   ROUND(AVG(p.nota_final)::numeric, 1) as promedio
            FROM progreso p
            JOIN modulos m ON p.modulo_id = m.id
            WHERE p.nota_final IS NOT NULL
            GROUP BY m.nivel
            ORDER BY m.nivel
        """)
        return {"niveles": rows_to_dicts(cur, cur.fetchall())}
    finally: cur.close(); conn.close()


@router.get("/actividad-reciente")
def actividad_reciente(current_user: dict = Depends(get_current_user)):
    if current_user["rol"] not in ["director","administrador","secretaria"]:
        raise HTTPException(403,"Sin permisos")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT u.nombre, u.apellido, u.rol,
                   u.fecha_registro::date as fecha
            FROM usuarios u
            ORDER BY u.fecha_registro DESC LIMIT 10
        """)
        recientes = rows_to_dicts(cur, cur.fetchall())
        cur.execute("""
            SELECT c.codigo, u.nombre, u.apellido, m.nombre as modulo,
                   c.fecha_emision::date as fecha
            FROM certificados c
            JOIN usuarios u ON c.estudiante_id=u.id
            JOIN modulos m ON c.modulo_id=m.id
            ORDER BY c.fecha_emision DESC LIMIT 8
        """)
        certs = rows_to_dicts(cur, cur.fetchall())
        return {"usuarios_recientes": recientes, "certificados_recientes": certs}
    finally: cur.close(); conn.close()

@router.get("/directorio-exportar")
def directorio_exportar(current_user: dict = Depends(get_current_user)):
    if current_user["rol"] not in ["director","administrador","secretaria"]:
        raise HTTPException(403,"Sin permisos")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Estudiantes (inferimos carrera por su último progreso o sub-consulta rápida)
        cur.execute("""
            SELECT u.id, u.nombre, u.apellido, u.carnet, u.email, u.estado, u.fecha_registro::date as fecha_inscripcion,
                   COALESCE((
                       SELECT c.nombre 
                       FROM progreso p 
                       JOIN modulos m ON p.modulo_id = m.id 
                       JOIN carreras c ON m.carrera_id = c.id 
                       WHERE p.usuario_id = u.id 
                       ORDER BY p.id DESC LIMIT 1
                   ), 'Sin Carrera Asignada') as carrera,
                   COALESCE((
                       SELECT m.nivel 
                       FROM progreso p 
                       JOIN modulos m ON p.modulo_id = m.id 
                       WHERE p.usuario_id = u.id 
                       ORDER BY p.id DESC LIMIT 1
                   ), u.nivel_asignado) as nivel
            FROM usuarios u
            WHERE u.rol = 'estudiante'
            ORDER BY carrera, nivel, u.apellido
        """)
        estudiantes = rows_to_dicts(cur, cur.fetchall())
        
        # Profesores
        cur.execute("""
            SELECT id, nombre, apellido, carnet, email, estado, nivel_asignado as area_especialidad, fecha_registro::date as fecha_ingreso
            FROM usuarios 
            WHERE rol IN ('docente','profesor')
            ORDER BY apellido
        """)
        profesores = rows_to_dicts(cur, cur.fetchall())
        
        return {"estudiantes": estudiantes, "profesores": profesores}
    finally: cur.close(); conn.close()
