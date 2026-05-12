"""
estadisticas.py â€” Dashboard de estadÃ­sticas institucionales CEA
KPIs en tiempo real: matriculados, aprobados, deserciÃ³n, por carrera/nivel/Ã¡rea.
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
            SELECT c.codigo_qr as codigo, u.nombre, u.apellido, m.nombre as modulo,
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
        # Estudiantes
        # Multi-inscripción: JOIN directo sin DISTINCT para que aparezca en cada carrera inscrita
        cur.execute("""
            SELECT u.id, u.nombre, u.apellido, u.carnet, u.email, u.estado,
                   COALESCE(i.fecha_inscripcion::date, u.fecha_registro::date) as fecha_inscripcion,
                   COALESCE(c.nombre, 'Sin Carrera Asignada') as carrera,
                   LOWER(COALESCE(c.area, 'humanistica')) as area,
                   COALESCE(i.nivel, u.nivel_asignado, 'Sin Nivel') as nivel,
                   COALESCE(i.paralelo, 'A') as paralelo,
                   COALESCE(i.turno, 'Noche') as turno
            FROM usuarios u
            JOIN inscripciones i ON i.usuario_id = u.id
            JOIN carreras c ON c.id = i.carrera_id
            WHERE u.rol = 'estudiante' AND COALESCE(i.estado, 'activo') = 'activo'
            ORDER BY area, carrera, nivel, paralelo, u.apellido
        """)
        estudiantes = rows_to_dicts(cur, cur.fetchall())
        
        # Profesores
        cur.execute("""
            SELECT id, nombre, apellido, carnet, email, estado, rol, nivel_asignado as area_especialidad, fecha_registro::date as fecha_ingreso
            FROM usuarios 
            WHERE rol IN ('docente','profesor','jefe_carrera')
            ORDER BY apellido
        """)
        profesores = rows_to_dicts(cur, cur.fetchall())
        
        return {"estudiantes": estudiantes, "profesores": profesores}
    finally: cur.close(); conn.close()


@router.get("/directorio-agrupado")
def directorio_agrupado(current_user: dict = Depends(get_current_user)):
    """Devuelve estudiantes agrupados por Ã¡rea > carrera/especialidad > nivel con conteo."""
    if current_user["rol"] not in ["director", "administrador", "secretaria"]:
        raise HTTPException(403, "Sin permisos")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Multi-inscripción: un estudiante aparece en CADA carrera donde esté inscrito
        cur.execute("""
            SELECT 
                u.id,
                u.nombre,
                u.apellido,
                u.carnet,
                u.email,
                u.estado,
                COALESCE(i.fecha_inscripcion::date, u.fecha_registro::date) as fecha_inscripcion,
                COALESCE(c.nombre, 'Sin Carrera Asignada') as carrera,
                LOWER(COALESCE(c.area, 'humanistica')) as area,
                COALESCE(i.nivel, u.nivel_asignado, 'Sin Nivel') as nivel,
                COALESCE(i.paralelo, 'A') as paralelo,
                COALESCE(i.turno, 'Noche') as turno
            FROM usuarios u
            JOIN inscripciones i ON i.usuario_id = u.id
            JOIN carreras c ON c.id = i.carrera_id
            WHERE u.rol = 'estudiante' AND COALESCE(i.estado, 'activo') = 'activo'
            ORDER BY area, carrera, nivel, paralelo, u.apellido
        """)
        rows = rows_to_dicts(cur, cur.fetchall())

        # Organizar en estructura agrupada — incluye paralelo en la clave si hay más de uno
        from collections import defaultdict
        # Primero contar cuántos paralelos hay por (área, carrera, nivel, turno)
        paralelo_counts = defaultdict(set)
        for r in rows:
            area_raw = (r["area"] or "humanistica").lower()
            area = "tecnica" if "cnica" in area_raw else "humanistica"
            carrera = r["carrera"] or "Sin Carrera"
            nivel = r["nivel"] or "Sin Nivel"
            turno = r["turno"] or "Noche"
            paralelo_counts[(area, carrera, nivel, turno)].add(r["paralelo"] or "A")

        grupos = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

        for r in rows:
            area_raw = (r["area"] or "humanistica").lower()
            area = "tecnica" if "cnica" in area_raw else "humanistica"
            carrera = r["carrera"] or "Sin Carrera Asignada"
            nivel = r["nivel"] or "Sin Nivel"
            paralelo = r["paralelo"] or "A"
            turno = r["turno"] or "Noche"
            # Si hay más de un paralelo en este curso, añadir el paralelo a la clave
            base_nivel = f"{nivel} ({turno})"
            clave_nivel = f"{base_nivel} - Paralelo {paralelo}" if len(paralelo_counts[(area, carrera, nivel, turno)]) > 1 else base_nivel
            grupos[area][carrera][clave_nivel].append(r)

        # Docentes (incluye jefe_carrera para mostrar su rol correcto)
        cur.execute("""
            SELECT id, nombre, apellido, carnet, email, estado, rol,
                   COALESCE(nivel_asignado, 'Sin Especialidad') as especialidad,
                   COALESCE(curso_asignado, '') as nivel_asignado,
                   COALESCE(es_jefe, FALSE) as es_jefe,
                   fecha_registro::date as fecha_ingreso
            FROM usuarios 
            WHERE rol IN ('docente','profesor','jefe_carrera')
            ORDER BY especialidad, apellido
        """)
        docentes = rows_to_dicts(cur, cur.fetchall())

        # Conteo por carrera (resumen)
        cur.execute("""
            SELECT COALESCE(c.nombre,'Sin Carrera') as carrera, COALESCE(c.area,'humanistica') as area,
                   COUNT(DISTINCT u.id) as total
            FROM usuarios u
            LEFT JOIN (
                SELECT DISTINCT ON (usuario_id) usuario_id, carrera_id
                FROM inscripciones ORDER BY usuario_id, id DESC
            ) i ON i.usuario_id = u.id
            LEFT JOIN carreras c ON i.carrera_id = c.id
            WHERE u.rol='estudiante'
            GROUP BY carrera, area ORDER BY area, carrera
        """)
        resumen_carreras = rows_to_dicts(cur, cur.fetchall())

        # Catálogo completo de carreras con su área (independiente de inscripciones)
        cur.execute("SELECT nombre, LOWER(area) as area FROM carreras WHERE estado = 'activo' ORDER BY area, nombre")
        catalogo_areas = {r["nombre"]: r["area"] for r in rows_to_dicts(cur, cur.fetchall())}

        return {
            "estudiantes": rows,
            "grupos": {
                area: {
                    carrera: {
                        nivel: {
                            "alumnos": alumnos,
                            "total": len(alumnos)
                        }
                        for nivel, alumnos in niveles.items()
                    }
                    for carrera, niveles in carreras.items()
                }
                for area, carreras in grupos.items()
            },
            "docentes": docentes,
            "resumen_carreras": resumen_carreras,
            "catalogo_areas": catalogo_areas
        }
    finally: cur.close(); conn.close()


from pydantic import BaseModel
from typing import Optional

class EliminarInscripcionesRequest(BaseModel):
    tipo: str  # 'individual', 'carrera', 'nivel', 'area', 'todos'
    usuario_id: Optional[int] = None
    carrera: Optional[str] = None
    nivel: Optional[str] = None
    area: Optional[str] = None
    turno: Optional[str] = None
    rol: Optional[str] = "estudiante"  # "estudiante" | "docente" | "todos"

@router.delete("/eliminar-inscripciones")
def eliminar_inscripciones(data: EliminarInscripcionesRequest, current_user: dict = Depends(get_current_user)):
    """Elimina inscripciones de estudiantes/docentes por tipo (individual, carrera, nivel, Ã¡rea, todos)."""
    if current_user["rol"] not in ["director", "administrador"]:
        raise HTTPException(403, "Solo el Director o Administrador puede realizar esta acciÃ³n")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        eliminados = 0

        roles_objetivo = []
        if data.rol == "todos":
            roles_objetivo = ['estudiante', 'docente', 'profesor', 'jefe_carrera']
        elif data.rol == "docente":
            roles_objetivo = ['docente', 'profesor', 'jefe_carrera']
        else:
            roles_objetivo = ['estudiante']

        target_ids = []
        if data.tipo == "individual":
            if not data.usuario_id:
                raise HTTPException(400, "Se requiere usuario_id para eliminaciÃ³n individual")
            target_ids = [data.usuario_id]

        elif data.tipo == "carrera":
            if not data.carrera:
                raise HTTPException(400, "Se requiere el nombre de la carrera/especialidad")
            if data.rol == "docente":
                cur.execute("SELECT id FROM usuarios WHERE nivel_asignado = %s AND rol IN %s", (data.carrera, tuple(roles_objetivo)))
            else:
                cur.execute("""
                    SELECT DISTINCT u.id FROM usuarios u JOIN inscripciones i ON i.usuario_id = u.id JOIN carreras c ON c.id = i.carrera_id
                    WHERE c.nombre = %s AND u.rol IN %s
                """, (data.carrera, tuple(roles_objetivo)))
            target_ids = [row[0] for row in cur.fetchall()]

        elif data.tipo == "nivel":
            if not data.nivel:
                raise HTTPException(400, "Se requiere el nivel")
            if data.turno:
                cur.execute("""
                    SELECT DISTINCT u.id FROM usuarios u JOIN inscripciones i ON i.usuario_id = u.id
                    WHERE i.nivel = %s AND i.turno = %s AND u.rol IN %s
                """, (data.nivel, data.turno, tuple(roles_objetivo)))
            else:
                cur.execute("""
                    SELECT DISTINCT u.id FROM usuarios u JOIN inscripciones i ON i.usuario_id = u.id
                    WHERE i.nivel = %s AND u.rol IN %s
                """, (data.nivel, tuple(roles_objetivo)))
            target_ids = [row[0] for row in cur.fetchall()]

        elif data.tipo == "area":
            if not data.area:
                raise HTTPException(400, "Se requiere el Ã¡rea")
            db_area = "TÃ©cnica" if data.area.lower() == "tecnica" else "HumanÃ­stica"
            cur.execute("""
                SELECT DISTINCT u.id FROM usuarios u JOIN inscripciones i ON i.usuario_id = u.id JOIN carreras c ON c.id = i.carrera_id
                WHERE LOWER(c.area) = LOWER(%s) AND u.rol IN %s
            """, (db_area, tuple(roles_objetivo)))
            target_ids = [row[0] for row in cur.fetchall()]

        elif data.tipo == "todos":
            cur.execute("SELECT id FROM usuarios WHERE rol IN %s", (tuple(roles_objetivo),))
            target_ids = [row[0] for row in cur.fetchall()]

        else:
            raise HTTPException(400, f"Tipo de eliminaciÃ³n no vÃ¡lido: {data.tipo}")

        eliminados = 0
        if target_ids:
            # Eliminar dependencias manualmente en caso de que la BD no tenga ON DELETE CASCADE
            t_ids = tuple(target_ids)
            cur.execute("DELETE FROM progreso WHERE usuario_id IN %s", (t_ids,))
            cur.execute("DELETE FROM inscripciones WHERE usuario_id IN %s", (t_ids,))
            cur.execute("DELETE FROM certificados WHERE usuario_id IN %s", (t_ids,))
            
            # Si hay docentes entre los eliminados, desvincularlos de los cursos (set null en vez de borrar el curso)
            cur.execute("UPDATE modulos SET docente_id = NULL WHERE docente_id IN %s", (t_ids,))
            cur.execute("UPDATE usuarios SET curso_asignado = NULL WHERE id IN %s", (t_ids,))
            
            # Finalmente, eliminar los usuarios
            cur.execute("DELETE FROM usuarios WHERE id IN %s", (t_ids,))
            eliminados = cur.rowcount

        conn.commit()
        return {"eliminados": eliminados, "mensaje": f"Se eliminaron {eliminados} registros correctamente."}
    except HTTPException as he:
        raise he
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Error al eliminar: {str(e)}")
    finally:
        cur.close(); conn.close()


@router.delete("/purgar-carreras-invalidas")
def purgar_carreras_invalidas(current_user: dict = Depends(get_current_user)):
    """Elimina carreras cuyo nombre es igual al nombre de un Ã¡rea (basura de datos)."""
    if current_user["rol"] not in ["admin", "administrador", "director"]:
        raise HTTPException(403, "Solo el Director puede purgar carreras")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        nombres_invalidos = ['tecnica', 'humanistica', 'tÃ©cnica', 'humanÃ­stica', 'general', 'sin carrera asignada']
        cur.execute("""
            DELETE FROM carreras
            WHERE LOWER(TRIM(nombre)) = ANY(%s)
            RETURNING id, nombre
        """, (nombres_invalidos,))
        eliminadas = cur.fetchall()
        conn.commit()
        return {"eliminadas": [{"id": r[0], "nombre": r[1]} for r in eliminadas], "total": len(eliminadas)}
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Error al purgar: {str(e)}")
    finally:
        cur.close(); conn.close()

