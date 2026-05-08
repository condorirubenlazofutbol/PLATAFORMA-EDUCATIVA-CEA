"""
planes.py — Generador de Planes Didácticos con IA para el CEA
Usa los datos de la malla curricular como contexto para generar:
  - Plan Semestral/Modular
  - Plan de Aula-Taller (por sesión)
  - Plan de Tema (desarrollo profundo)
"""
import os
from fastapi import APIRouter, Depends, HTTPException
from database import get_db_connection
from routes.auth import get_current_user
from pydantic import BaseModel
from typing import Optional
import httpx

router = APIRouter()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


def rows_to_dicts(cursor, rows):
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, r)) for r in rows]


# ─── MODELOS ──────────────────────────────────────────────────────────────────

class PlanRequest(BaseModel):
    tipo: str                          # 'semestral' | 'aula_taller' | 'tema'
    carrera_id: int
    modulo_id: Optional[int] = None
    tema_id: Optional[int] = None
    nivel: Optional[str] = None
    horas_sesion: Optional[int] = 4   # Para plan aula-taller
    observaciones: Optional[str] = "" # Notas adicionales del docente


# ─── GENERADOR INTERNO ────────────────────────────────────────────────────────

def get_contexto_modulo(cur, modulo_id: int) -> dict:
    cur.execute("""
        SELECT m.id, m.nombre, m.nivel, m.periodo, m.descripcion, m.area,
               c.nombre as carrera
        FROM modulos m
        LEFT JOIN carreras c ON m.carrera_id = c.id
        WHERE m.id = %s
    """, (modulo_id,))
    row = cur.fetchone()
    if not row:
        return {}
    mod = dict(zip([d[0] for d in cur.description], row))

    cur.execute("SELECT numero, titulo, subtitulos FROM temas WHERE modulo_id=%s ORDER BY numero", (modulo_id,))
    mod["temas"] = rows_to_dicts(cur, cur.fetchall())
    return mod


def build_prompt(tipo: str, carrera: str, nivel: str, modulo: dict,
                 tema: dict = None, horas: int = 4, observaciones: str = "") -> str:
    """Construye el prompt institucional CEA según el tipo de plan."""

    temas_txt = ""
    if modulo.get("temas"):
        for t in modulo["temas"]:
            subs = t.get("subtitulos", [])
            if isinstance(subs, str):
                import json
                try: subs = json.loads(subs)
                except: subs = []
            sub_txt = "\n".join([f"      - {s}" for s in subs]) if subs else ""
            temas_txt += f"\n    Tema {t['numero']}: {t['titulo']}"
            if sub_txt:
                temas_txt += f"\n{sub_txt}"

    ctx_modulo = f"""
Carrera: {carrera}
Nivel: {nivel}
Módulo: {modulo.get('nombre', '')}
Área: {modulo.get('area', 'Técnica')}
Período: {modulo.get('periodo', '')}
Descripción del módulo: {modulo.get('descripcion', '')}
Temas del módulo:{temas_txt}
    """.strip()

    if tipo == "semestral":
        return f"""Eres un experto pedagogo del CEA (Centro de Educación Alternativa) Prof. Herman Ortiz Camargo de Pailón, Bolivia.
El CEA trabaja con el Modelo Educativo Sociocomunitario Productivo (MESCP) del Estado Plurinacional de Bolivia.
La evaluación es sobre 100 puntos: Ser(10), Saber(30-40), Hacer(30-40), Decidir(10), Autoevaluación(10).

Genera un PLAN SEMESTRAL MODULAR completo y profesional con la siguiente información curricular:

{ctx_modulo}

El plan debe incluir:
1. Datos institucionales (CEA Prof. Herman Ortiz Camargo, Pailón, Santa Cruz, Bolivia)
2. Objetivo holístico del módulo (en 4 dimensiones: Ser, Saber, Hacer, Decidir)
3. Justificación pedagógica del módulo
4. Contenidos mínimos organizados por tema (con referencias bibliográficas)
5. Estrategias metodológicas y actividades prácticas de laboratorio/taller
6. Recursos y materiales necesarios
7. Criterios e instrumentos de evaluación (tabla con dimensiones y porcentajes)
8. Cronograma de desarrollo (distribución de horas por tema)
9. Producto esperado al finalizar el módulo
{f"Observaciones adicionales del facilitador: {observaciones}" if observaciones else ""}

Formato: Documento formal en español. Usa encabezados claros. Nivel Pro institucional."""

    elif tipo == "aula_taller":
        tema_info = f"Tema {tema['numero']}: {tema['titulo']}" if tema else "Tema a definir"
        return f"""Eres un experto pedagogo del CEA (Centro de Educación Alternativa) Prof. Herman Ortiz Camargo de Pailón, Bolivia.
Trabajas con el Modelo Educativo Sociocomunitario Productivo (MESCP).

Genera un PLAN DE AULA-TALLER detallado y profesional para una sesión de {horas} horas:

Contexto curricular:
{ctx_modulo}

Tema de la sesión: {tema_info}
{f"Observaciones: {observaciones}" if observaciones else ""}

El plan de aula-taller debe incluir:
1. Datos de identificación (institución, carrera, facilitador, fecha, tema, horas)
2. Objetivo de la sesión (holístico con las 4 dimensiones)
3. Momento ACTIVACIÓN DEL SABER PREVIO (15-20 min): Preguntas, dinámicas, materiales
4. Momento CONSTRUCCIÓN DE NUEVOS SABERES (tiempo principal): Contenidos + actividades paso a paso
5. Momento VALORACIÓN Y CONSOLIDACIÓN (20-30 min): Práctica guiada, ejercicios, debate
6. Momento PRODUCTO/TAREA (10-15 min): Producto concreto de la sesión
7. Recursos necesarios (herramientas, equipos, materiales, software)
8. Criterios de evaluación formativa de la sesión
9. Reflexión metacognitiva (preguntas al estudiante)

Formato: Documento formal, estructurado con secciones claras. Nivel profesional institucional CEA Bolivia."""

    else:  # tema
        tema_info = f"Tema {tema['numero']}: {tema['titulo']}" if tema else "Tema a definir"
        subs = []
        if tema:
            subs_raw = tema.get("subtitulos", [])
            if isinstance(subs_raw, str):
                import json
                try: subs = json.loads(subs_raw)
                except: subs = []
            else:
                subs = subs_raw or []

        sub_txt = "\n".join([f"  - {s}" for s in subs]) if subs else "(Sin subtítulos definidos)"

        return f"""Eres un experto pedagogo del CEA (Centro de Educación Alternativa) Prof. Herman Ortiz Camargo de Pailón, Bolivia.
Trabajas con el Modelo Educativo Sociocomunitario Productivo (MESCP).

Genera el DESARROLLO COMPLETO DE UN TEMA con todos los contenidos académicos necesarios:

Contexto:
{ctx_modulo}

Tema a desarrollar: {tema_info}
Subtítulos del tema:
{sub_txt}

{f"Notas del facilitador: {observaciones}" if observaciones else ""}

El desarrollo del tema debe incluir:
1. Introducción motivadora y contextualización del tema
2. Desarrollo teórico completo de CADA subtítulo (con ejemplos prácticos, analogías y casos reales)
3. Actividades prácticas de laboratorio/taller por subtítulo
4. Materiales de apoyo recomendados (libros, videos, tutoriales, herramientas)
5. Ejercicios de práctica con soluciones guiadas
6. Evaluación del tema: preguntas de comprensión + práctica calificable
7. Glosario de términos clave
8. Conexión con los demás temas del módulo y con el PSP (Proyecto Socioproductivo)

Formato: Documento académico completo, extenso y detallado. Incluye ejemplos con código/ejercicios si aplica. Nivel pro."""


async def llamar_gemini(prompt: str) -> str:
    """Llama a la API de Gemini para generar el plan."""
    if not GEMINI_API_KEY:
        # Modo demo si no hay API key
        return f"""[MODO DEMO - Configura GEMINI_API_KEY para obtener el plan completo]

PLAN GENERADO PARA: {prompt[:200]}...

Para activar la generación con IA:
1. Obtén tu API Key en https://ai.google.dev/
2. Configura la variable de entorno GEMINI_API_KEY en Render/Railway
3. Recarga el backend con /cargar-datos

Este es un plan de ejemplo con la estructura correcta que generará la IA."""

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 8192,
        }
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            json=payload,
            headers=headers
        )
        if not resp.is_success:
            raise HTTPException(502, f"Error IA: {resp.text[:300]}")
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


# ─── ENDPOINTS ────────────────────────────────────────────────────────────────

@router.post("/generar")
async def generar_plan(req: PlanRequest, current_user: dict = Depends(get_current_user)):
    """Genera un plan didáctico usando IA con contexto de la malla curricular."""
    if current_user["rol"] not in ["docente", "jefe_carrera", "director", "administrador"]:
        raise HTTPException(403, "Solo facilitadores y jefes de carrera pueden generar planes")

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Obtener datos de la carrera
        cur.execute("SELECT nombre, area FROM carreras WHERE id=%s", (req.carrera_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Carrera no encontrada")
        carrera_nombre, carrera_area = row

        # Obtener módulo si se especificó
        modulo = {}
        if req.modulo_id:
            modulo = get_contexto_modulo(cur, req.modulo_id)

        # Obtener tema si se especificó
        tema = None
        if req.tema_id:
            cur.execute("SELECT id, numero, titulo, subtitulos FROM temas WHERE id=%s", (req.tema_id,))
            t_row = cur.fetchone()
            if t_row:
                tema = dict(zip([d[0] for d in cur.description], t_row))

        nivel = req.nivel or modulo.get("nivel", "")

        # Construir prompt y llamar IA
        prompt = build_prompt(
            tipo=req.tipo,
            carrera=carrera_nombre,
            nivel=nivel,
            modulo=modulo,
            tema=tema,
            horas=req.horas_sesion or 4,
            observaciones=req.observaciones or ""
        )

        contenido = await llamar_gemini(prompt)

        # Guardar en historial
        titulo = f"Plan {req.tipo.title()} - {modulo.get('nombre', carrera_nombre)}"
        if tema:
            titulo += f" (Tema {tema['numero']})"

        cur.execute("""
            INSERT INTO planes_didacticos
            (docente_id, carrera_id, modulo_id, tema_id, tipo, titulo, contenido_ia)
            VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """, (
            current_user["id"], req.carrera_id, req.modulo_id,
            req.tema_id, req.tipo, titulo, contenido
        ))
        plan_id = cur.fetchone()[0]
        conn.commit()

        return {"id": plan_id, "titulo": titulo, "contenido": contenido, "tipo": req.tipo}

    except HTTPException:
        conn.rollback(); raise
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


@router.get("/historial")
def historial_planes(current_user: dict = Depends(get_current_user)):
    """Retorna el historial de planes del docente actual."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        query_filter = ""
        params = []
        if current_user["rol"] not in ["director", "administrador"]:
            query_filter = "WHERE pd.docente_id=%s"
            params = [current_user["id"]]

        cur.execute(f"""
            SELECT pd.id, pd.tipo, pd.titulo, pd.fecha_generacion,
                   c.nombre as carrera, m.nombre as modulo,
                   u.nombre as docente
            FROM planes_didacticos pd
            LEFT JOIN carreras c ON pd.carrera_id = c.id
            LEFT JOIN modulos m ON pd.modulo_id = m.id
            LEFT JOIN usuarios u ON pd.docente_id = u.id
            {query_filter}
            ORDER BY pd.fecha_generacion DESC LIMIT 100
        """, params)
        return {"planes": rows_to_dicts(cur, cur.fetchall())}
    finally:
        cur.close(); conn.close()


@router.get("/{plan_id}")
def obtener_plan(plan_id: int, current_user: dict = Depends(get_current_user)):
    """Retorna un plan específico por ID."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT pd.id, pd.tipo, pd.titulo, pd.contenido_ia, pd.fecha_generacion,
                   c.nombre as carrera, m.nombre as modulo, pd.docente_id
            FROM planes_didacticos pd
            LEFT JOIN carreras c ON pd.carrera_id = c.id
            LEFT JOIN modulos m ON pd.modulo_id = m.id
            WHERE pd.id = %s
        """, (plan_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Plan no encontrado")
        plan = dict(zip([d[0] for d in cur.description], row))

        # Solo el dueño o directivos pueden ver el plan
        if (plan["docente_id"] != current_user["id"] and
                current_user["rol"] not in ["director", "administrador", "jefe_carrera"]):
            raise HTTPException(403, "Sin permisos")

        return plan
    finally:
        cur.close(); conn.close()


@router.delete("/{plan_id}")
def eliminar_plan(plan_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT docente_id FROM planes_didacticos WHERE id=%s", (plan_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Plan no encontrado")
        if row[0] != current_user["id"] and current_user["rol"] not in ["director", "administrador"]:
            raise HTTPException(403, "Sin permisos")
        cur.execute("DELETE FROM planes_didacticos WHERE id=%s", (plan_id,))
        conn.commit()
        return {"mensaje": "Plan eliminado"}
    except HTTPException:
        conn.rollback(); raise
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()
