"""
evaluaciones.py — Sistema de evaluaciones online CEA
Docentes crean exámenes con preguntas múltiples.
Estudiantes responden y reciben calificación automática.
"""
from fastapi import APIRouter, Depends, HTTPException
from database import get_db_connection
from routes.auth import get_current_user
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

def rows_to_dicts(cursor, rows):
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, r)) for r in rows]

# --- MODELOS ---
class OpcionBase(BaseModel):
    texto: str
    es_correcta: bool

class PreguntaBase(BaseModel):
    texto: str
    puntos: int = 1
    opciones: List[OpcionBase]

class EvaluacionCreate(BaseModel):
    modulo_id: int
    titulo: str
    descripcion: Optional[str] = ""
    tiempo_minutos: int = 60
    activa: bool = False
    preguntas: List[PreguntaBase]

class RespuestaAlumno(BaseModel):
    pregunta_id: int
    opcion_id: int


# --- DOCENTE: CREAR/GESTIONAR EVALUACIONES ---

@router.post("/")
def crear_evaluacion(data: EvaluacionCreate, current_user: dict = Depends(get_current_user)):
    if current_user["rol"] not in ["docente","profesor","director","administrador"]:
        raise HTTPException(403, "Solo docentes pueden crear evaluaciones")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Insertar evaluación
        cur.execute("""
            INSERT INTO evaluaciones (modulo_id,docente_id,titulo,descripcion,tiempo_minutos,activa)
            VALUES (%s,%s,%s,%s,%s,%s) RETURNING id
        """, (data.modulo_id, current_user["id"], data.titulo, data.descripcion, data.tiempo_minutos, data.activa))
        eval_id = cur.fetchone()[0]

        # Insertar preguntas y opciones
        for i, p in enumerate(data.preguntas):
            cur.execute("""
                INSERT INTO preguntas (evaluacion_id,texto,puntos,orden)
                VALUES (%s,%s,%s,%s) RETURNING id
            """, (eval_id, p.texto, p.puntos, i+1))
            preg_id = cur.fetchone()[0]
            
            for op in p.opciones:
                cur.execute("""
                    INSERT INTO opciones_pregunta (pregunta_id,texto,es_correcta)
                    VALUES (%s,%s,%s)
                """, (preg_id, op.texto, op.es_correcta))

        conn.commit()
        return {"id": eval_id, "mensaje": "Evaluación creada correctamente"}
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally: cur.close(); conn.close()


@router.get("/modulo/{modulo_id}")
def listar_evaluaciones(modulo_id: int, current_user: dict = Depends(get_current_user)):
    """Lista las evaluaciones de un módulo. Estudiantes solo ven activas."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if current_user["rol"] == "estudiante":
            cur.execute("""
                SELECT e.id, e.titulo, e.descripcion, e.tiempo_minutos, e.activa,
                       (SELECT sum(p.puntos) FROM preguntas p WHERE p.evaluacion_id=e.id) as puntaje_total,
                       (SELECT COUNT(*) FROM respuestas_alumno r WHERE r.evaluacion_id=e.id AND r.estudiante_id=%s) > 0 as completada
                FROM evaluaciones e WHERE e.modulo_id=%s AND e.activa=TRUE
            """, (current_user["id"], modulo_id))
        else:
            cur.execute("""
                SELECT e.id, e.titulo, e.descripcion, e.tiempo_minutos, e.activa,
                       (SELECT sum(p.puntos) FROM preguntas p WHERE p.evaluacion_id=e.id) as puntaje_total,
                       (SELECT COUNT(DISTINCT r.estudiante_id) FROM respuestas_alumno r WHERE r.evaluacion_id=e.id) as respondieron
                FROM evaluaciones e WHERE e.modulo_id=%s
            """, (modulo_id,))
        return {"evaluaciones": rows_to_dicts(cur, cur.fetchall())}
    finally: cur.close(); conn.close()


@router.delete("/{eval_id}")
def eliminar_evaluacion(eval_id: int, current_user: dict = Depends(get_current_user)):
    if current_user["rol"] not in ["docente","profesor","director","administrador"]:
        raise HTTPException(403, "Sin permisos")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM evaluaciones WHERE id=%s AND (docente_id=%s OR %s IN ('director','administrador'))", 
                    (eval_id, current_user["id"], current_user["rol"]))
        conn.commit()
        return {"mensaje": "Evaluación eliminada"}
    finally: cur.close(); conn.close()


# --- ESTUDIANTE: RESPONDER EVALUACIÓN ---

@router.get("/{eval_id}/iniciar")
def iniciar_evaluacion(eval_id: int, current_user: dict = Depends(get_current_user)):
    """Retorna la evaluación con sus preguntas (sin las respuestas correctas)."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Validar si ya la hizo
        if current_user["rol"] == "estudiante":
            cur.execute("SELECT id FROM respuestas_alumno WHERE evaluacion_id=%s AND estudiante_id=%s LIMIT 1", (eval_id, current_user["id"]))
            if cur.fetchone(): raise HTTPException(400, "Ya completaste esta evaluación")

        cur.execute("SELECT id, titulo, descripcion, tiempo_minutos FROM evaluaciones WHERE id=%s", (eval_id,))
        ev = cur.fetchone()
        if not ev: raise HTTPException(404, "No encontrada")
        evaluacion = {"id": ev[0], "titulo": ev[1], "descripcion": ev[2], "tiempo": ev[3]}

        cur.execute("SELECT id, texto, puntos FROM preguntas WHERE evaluacion_id=%s ORDER BY orden", (eval_id,))
        preguntas = rows_to_dicts(cur, cur.fetchall())

        for p in preguntas:
            cur.execute("SELECT id, texto FROM opciones_pregunta WHERE pregunta_id=%s", (p["id"],))
            p["opciones"] = rows_to_dicts(cur, cur.fetchall())

        evaluacion["preguntas"] = preguntas
        return evaluacion
    finally: cur.close(); conn.close()


@router.post("/{eval_id}/responder")
def responder_evaluacion(eval_id: int, respuestas: List[RespuestaAlumno], current_user: dict = Depends(get_current_user)):
    """Guarda y califica automáticamente la evaluación."""
    if current_user["rol"] != "estudiante": raise HTTPException(400, "Solo estudiantes")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Verificar si ya respondió
        cur.execute("SELECT id FROM respuestas_alumno WHERE evaluacion_id=%s AND estudiante_id=%s LIMIT 1", (eval_id, current_user["id"]))
        if cur.fetchone(): raise HTTPException(400, "Evaluación ya completada")

        puntaje_obtenido = 0
        puntaje_total = 0

        # Procesar respuestas
        for r in respuestas:
            # Obtener datos de la pregunta y opción
            cur.execute("SELECT puntos FROM preguntas WHERE id=%s", (r.pregunta_id,))
            puntos_preg = cur.fetchone()[0]
            puntaje_total += puntos_preg

            cur.execute("SELECT es_correcta FROM opciones_pregunta WHERE id=%s", (r.opcion_id,))
            es_correcta = cur.fetchone()[0]

            puntos_ganados = puntos_preg if es_correcta else 0
            puntaje_obtenido += puntos_ganados

            # Guardar
            cur.execute("""
                INSERT INTO respuestas_alumno (evaluacion_id,estudiante_id,pregunta_id,opcion_id,es_correcta,puntos_obtenidos)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (eval_id, current_user["id"], r.pregunta_id, r.opcion_id, es_correcta, puntos_ganados))

        nota_100 = round((puntaje_obtenido / max(puntaje_total, 1)) * 100, 2)
        conn.commit()

        # Opcional: Integrar nota al módulo en `progreso` (Sería nota SABER por ej.)
        
        return {
            "mensaje": "Evaluación finalizada",
            "puntaje_obtenido": puntaje_obtenido,
            "puntaje_total": puntaje_total,
            "nota_100": nota_100
        }
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally: cur.close(); conn.close()
