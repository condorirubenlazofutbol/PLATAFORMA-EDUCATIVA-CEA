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
                   COALESCE(i.paralelo, 'A') as paralelo
            FROM usuarios u
            JOIN inscripciones i ON i.usuario_id = u.id
            JOIN carreras c ON c.id = i.carrera_id
            WHERE u.rol = 'estudiante' AND i.estado = 'activo'
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
                COALESCE(i.paralelo, 'A') as paralelo
            FROM usuarios u
            JOIN inscripciones i ON i.usuario_id = u.id
            JOIN carreras c ON c.id = i.carrera_id
            WHERE u.rol = 'estudiante' AND i.estado = 'activo'
            ORDER BY area, carrera, nivel, paralelo, u.apellido
        """)
        rows = rows_to_dicts(cur, cur.fetchall())

        # Organizar en estructura agrupada â€” incluye paralelo en la clave si hay mÃ¡s de uno
        from collections import defaultdict
        # Primero contar cuÃ¡ntos paralelos hay por (Ã¡rea, carrera, nivel)
        paralelo_counts = defaultdict(set)
        for r in rows:
            area = (r["area"] or "humanistica").lower()
            carrera = r["carrera"] or "Sin Carrera"
            nivel = r["nivel"] or "Sin Nivel"
            paralelo_counts[(area, carrera, nivel)].add(r["paralelo"] or "A")

        grupos = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

        for r in rows:
            area = (r["area"] or "humanistica").lower()
            carrera = r["carrera"] or "Sin Carrera Asignada"
            nivel = r["nivel"] or "Sin Nivel"
            paralelo = r["paralelo"] or "A"
            # Si hay mÃ¡s de un paralelo en este curso, aÃ±adir el paralelo a la clave
            clave_nivel = f"{nivel} - Paralelo {paralelo}" if len(paralelo_counts[(area, carrera, nivel)]) > 1 else nivel
            grupos[area][carrera][clave_nivel].append(r)

        # Docentes (incluye jefe_carrera para mostrar su rol correcto)
        cur.execute("""
            SELECT id, nombre, apellido, carnet, email, estado, rol,
                   COALESCE(nivel_asignado, 'Sin Especialidad') as especialidad,
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
            roles_objetivo = ['estudiante', 'docente', 'profesor']
        elif data.rol == "docente":
            roles_objetivo = ['docente', 'profesor']
        else:
            roles_objetivo = ['estudiante']

        if data.tipo == "individual":
            if not data.usuario_id:
                raise HTTPException(400, "Se requiere usuario_id para eliminaciÃ³n individual")
            cur.execute("DELETE FROM usuarios WHERE id = %s RETURNING id", (data.usuario_id,))
            eliminados = cur.rowcount

        elif data.tipo == "carrera":
            if not data.carrera:
                raise HTTPException(400, "Se requiere el nombre de la carrera/especialidad")
            
            if data.rol == "docente":
                # Para docentes, la especialidad se guarda en nivel_asignado
                cur.execute("""
                    DELETE FROM usuarios 
                    WHERE nivel_asignado = %s AND rol = ANY(%s) 
                    RETURNING id
                """, (data.carrera, roles_objetivo))
            else:
                cur.execute("""
                    DELETE FROM usuarios WHERE id IN (
                        SELECT DISTINCT i.usuario_id FROM inscripciones i
                        JOIN carreras c ON i.carrera_id = c.id
                        WHERE c.nombre = %s
                    ) AND rol = ANY(%s) RETURNING id
                """, (data.carrera, roles_objetivo))
            eliminados = cur.rowcount

        elif data.tipo == "nivel":
            if not data.nivel:
                raise HTTPException(400, "Se requiere el nivel")
            cur.execute("""
                DELETE FROM usuarios WHERE id IN (
                    SELECT DISTINCT i.usuario_id FROM inscripciones i
                    WHERE i.nivel = %s
                ) AND rol = ANY(%s) RETURNING id
            """, (data.nivel, roles_objetivo))
            eliminados = cur.rowcount

        elif data.tipo == "area":
            if not data.area:
                raise HTTPException(400, "Se requiere el Ã¡rea")
            db_area = "TÃ©cnica" if data.area.lower() == "tecnica" else "HumanÃ­stica"
            cur.execute("""
                DELETE FROM usuarios WHERE id IN (
                    SELECT DISTINCT i.usuario_id FROM inscripciones i
                    JOIN carreras c ON i.carrera_id = c.id
                    WHERE LOWER(c.area) = LOWER(%s)
                ) AND rol = ANY(%s) RETURNING id
            """, (db_area, roles_objetivo))
            eliminados = cur.rowcount

        elif data.tipo == "todos":
            cur.execute("DELETE FROM usuarios WHERE rol = ANY(%s) RETURNING id", (roles_objetivo,))
            eliminados = cur.rowcount

        else:
            raise HTTPException(400, f"Tipo de eliminaciÃ³n no vÃ¡lido: {data.tipo}")

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

