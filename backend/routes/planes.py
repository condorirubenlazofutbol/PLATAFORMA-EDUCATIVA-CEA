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
    tipo: str                               # 'semestral'|'modular'|'aula_taller'|'tema'|'modulo_completo'
    carrera_id: int
    modulo_id: Optional[int] = None
    tema_id: Optional[int] = None
    nivel: Optional[str] = None
    horas_sesion: Optional[int] = 25
    observaciones: Optional[str] = ""
    generar_completo: Optional[bool] = False   # True → genera los 4 temas del módulo
    subtitulo_num: Optional[int] = None        # 1-4 para tema específico


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
                 tema: dict = None, subtitulo_num: int = None,
                 generar_completo: bool = False,
                 horas: int = 25, observaciones: str = "") -> str:
    """Construye el prompt institucional CEA según el tipo de plan usando los prompts maestros del CEA."""

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
Temas del módulo:{temas_txt}
    """.strip()

    # ─── PROMPT MAESTRO MÓDULOS (Contenido educativo completo por tema/módulo) ─
    if tipo in ["tema", "modulo_completo"]:
        tema_info = ""
        if tema and not generar_completo:
            tema_info = f"Tema {tema['numero']}: {tema['titulo']}"
            if subtitulo_num and isinstance(tema.get('subtitulos'), list):
                subs = tema['subtitulos']
                if subtitulo_num <= len(subs):
                    tema_info += f" → Subtítulo {subtitulo_num}: {subs[subtitulo_num-1]}"

        return f"""Actúa como experto en diseño curricular técnico-tecnológico en Bolivia, especializado en la carrera de {carrera}, bajo el Modelo Educativo Sociocomunitario Productivo (MESCP). Tu objetivo es generar guías de aprendizaje de alta calidad profesional para el CEA "Prof. Herman Ortiz Camargo", Distrito de Pailón.

CONTEXTO CURRICULAR REAL:
{ctx_modulo}

{'INSTRUCCIÓN: Genera el MÓDULO COMPLETO desarrollando los 4 temas con todo su contenido.' if generar_completo else f'INSTRUCCIÓN: Desarrolla el siguiente tema: {tema_info}'}

ESTRUCTURA OBLIGATORIA DEL DOCUMENTO (usa Markdown profesional):

# CARÁTULA
**CARRERA:** {carrera}
**NIVEL:** {nivel}
**MÓDULO:** {modulo.get('nombre', '')}
{'**TEMA:** ' + (tema_info if tema_info else 'MÓDULO COMPLETO')}

---

# I. PRESENTACIÓN
(Redacción inicial extensa de al menos 3 párrafos explicando la importancia del módulo en el contexto socioproductivo boliviano.)

**PRÁCTICA:** (Redacción amplia y técnica sobre las experiencias iniciales y el contacto con la realidad tecnológica del módulo. Mínimo 5-8 líneas.)

**TEORÍA:** (Redacción amplia sobre la profundización científica y los conceptos avanzados. Mínimo 5-8 líneas.)

**VALORACIÓN:** (Redacción amplia sobre el análisis ético, social y la utilidad técnica para la comunidad boliviana. Mínimo 5-8 líneas.)

**PRODUCCIÓN:** (Redacción amplia sobre los productos finales o soluciones que el estudiante creará. Mínimo 5-8 líneas.)

---

# II. INTRODUCCIÓN
(Incluye: 1. Importancia técnica del módulo/tema; 2. Objetivos de aprendizaje; 3. Resumen de cada uno de los 4 temas de la malla; 4. Relevancia en el mercado laboral boliviano.)

---

# III. ÍNDICE DE CONTENIDOS
(Lista jerárquica con temas y subtemas completos según la malla real. Solo texto plano.)

---

{"".join([f"""
# TEMA {t['numero']}: {t['titulo']}

## 1. PRÁCTICA
(Pregunta diagnóstica y caso real técnico en **NEGRITA**. Formato: pregunta en negrita + Rpta………………………………………………………………………)

## 2. TEORÍA
(MÍNIMO 2000 PALABRAS. Desarrollo técnico exhaustivo con subtemas 2.1, 2.1.1, a). INCLUIR: ejemplos resueltos paso a paso, tablas comparativas, bloques de código cuando aplique, indicadores de gráficos en azul [Insertar diagrama aquí], contextualización Bolivia, conclusión general, glosario de términos clave, guía de laboratorio sugerida.)

## 3. VALORACIÓN
(Reflexión profunda sobre la importancia técnica del tema, impacto ético y beneficio para la sociedad boliviana.)

## 4. PRODUCCIÓN
(Exactamente 15 preguntas evaluativas: 5 Desarrollo, 5 Selección Múltiple, 5 Verdadero/Falso INTERCALADAS. Formato: número en negrita, enunciado en negrita, respuesta en texto normal. Para desarrollo: Rpta…………………………. Para múltiple: incisos a, b, c, d en líneas separadas. Para V/F: incisos a, b en líneas separadas.)

""" for t in (modulo.get("temas", []) if generar_completo else [tema] if tema else [])])}

---

# IV. BIBLIOGRAFÍA COMPLETA
(10-15 fuentes actualizadas en formato APA. Autores en **NEGRITA**, resto en texto normal. Lista numerada 1., 2., 3...)

{f'Observaciones adicionales: {observaciones}' if observaciones else ''}

GENERA EL DOCUMENTO COMPLETO Y DETALLADO AHORA. DESARROLLA CADA SECCIÓN SIN RESUMIR NI OMITIR CONTENIDO."""

    # ─── PROMPT MAESTRO PLANIFICACIÓN EDUCATIVA CEA 2026 ─────────────────────
    base_cea = f"""Actúa como un experto en Diseño Curricular Técnico-Tecnológico (EPJA) de Bolivia. Tu función es generar documentos de planificación para la especialidad de {carrera} en el CEA "Prof. Herman Ortiz Camargo", Distrito de Pailón.
CARACTERÍSTICAS TÉCNICAS:
- Idioma: Profesional, técnico y alineado a la normativa de Educación Técnica Tecnológica Productiva (ETTP) y el MESCP.
- Coherencia: Los contenidos deben reflejar la realidad tecnológica y el mercado laboral boliviano.
- Identidad: Nombrar siempre al CEA "Prof. Herman Ortiz Camargo", Dirección Distrital Pailón.

CONTEXTO CURRICULAR REAL:
{ctx_modulo}

{f'Observaciones del facilitador: {observaciones}' if observaciones else ''}"""

    if tipo == "semestral":
        return f"""{base_cea}

INSTRUCCIÓN: Genera el PLAN SEMESTRAL MODULAR completo con la siguiente estructura obligatoria en formato Markdown con tablas:

# PLAN SEMESTRAL MODULAR
## CEA "Prof. Herman Ortiz Camargo" — Pailón, Santa Cruz, Bolivia

### DATOS REFERENCIALES
| Campo | Dato |
|---|---|
| Dirección Distrital | Pailón |
| CEA | "Prof. Herman Ortiz Camargo" |
| Especialidad | {carrera} |
| Nivel | {nivel} |
| Gestión | 2026 |
| Facilitador/a | _________________________________ |
| Firma y Sello | _________________________________ |

### OBJETIVO GENERAL DEL POA
(Redacta el objetivo oficial sobre el fortalecimiento de la educación técnica para mejorar las condiciones de vida de la comunidad de Pailón, orientado al desarrollo socioproductivo local.)

### TABLA DE CONTENIDOS SEMESTRAL
| N° | Unidad Temática / Módulo | Contenidos Mínimos | Metodología (P-T-V-P) | Recursos | Tiempo (Periodos) | Evaluación (SER/SABER/HACER/DECIDIR) |
|---|---|---|---|---|---|---|
(Desarrolla una fila completa por cada tema de la malla. Mínimo 4 filas correspondientes a los 4 temas. Sé específico y técnico en cada celda.)

### DISTRIBUCIÓN SEMANAL DE CONTENIDOS
(Tabla con 18 semanas mínimo, indicando qué tema/contenido se trabaja cada semana, con horas asignadas.)

| Semana | Fechas | Tema/Contenido | Actividad Principal | Horas |
|---|---|---|---|---|

### CRONOGRAMA DE EVALUACIONES
(Tabla con fechas tentativas de evaluaciones parciales y final.)

### FIRMA Y APROBACIÓN
(Espacio para firmas del Facilitador/a, Jefe de Carrera y Director/a del CEA.)

GENERA EL PLAN COMPLETO Y DETALLADO AHORA."""

    elif tipo == "modular":
        return f"""{base_cea}

INSTRUCCIÓN: Genera el PLAN MODULAR DETALLADO completo con la siguiente estructura obligatoria en formato Markdown con tablas:

# PLAN MODULAR DETALLADO
## {modulo.get('nombre', 'Módulo')}
## CEA "Prof. Herman Ortiz Camargo" — {nivel} — Gestión 2026

### DATOS REFERENCIALES
| Campo | Dato |
|---|---|
| Dirección Distrital | Pailón |
| CEA | "Prof. Herman Ortiz Camargo" |
| Especialidad | {carrera} |
| Nivel | {nivel} |
| Módulo | {modulo.get('nombre', '')} |
| Duración | {horas} periodos |
| Gestión | 2026 |

### OBJETIVO HOLÍSTICO DEL MÓDULO
(Redacta el objetivo holístico completo con verbos que promuevan valores sociocomunitarios Y habilidades técnicas específicas. Debe incluir las 4 dimensiones del MESCP.)

**SER:** (Objetivo actitudinal y valórico)
**SABER:** (Objetivo conceptual y cognitivo técnico)
**HACER:** (Objetivo procedimental y práctico)
**DECIDIR:** (Objetivo de toma de decisiones productivas)

### CUADRO DE UNIDADES TEMÁTICAS
| Tema | Título | Contenidos Mínimos | Metodología Andragógica | Recursos | Periodos | Criterios de Evaluación |
|---|---|---|---|---|---|---|
(Una fila por cada tema de la malla. Desarrolla metodología específica P-T-V-P por tema.)

### ESTRATEGIAS METODOLÓGICAS GENERALES
(Lista detallada de estrategias andragógicas aplicadas al módulo.)

### CRITERIOS E INSTRUMENTOS DE EVALUACIÓN
| Dimensión | Criterio | Instrumento | Ponderación |
|---|---|---|---|
| SER | | | 10% |
| SABER | | | 30% |
| HACER | | | 40% |
| DECIDIR | | | 20% |

### PRODUCTO DEL MÓDULO
(Describe el entregable técnico o producto tangible que el estudiante presentará al finalizar el módulo.)

GENERA EL PLAN COMPLETO Y DETALLADO AHORA."""

    else:  # aula_taller
        tema_info = f"Tema {tema['numero']}: {tema['titulo']}" if tema else "Tema específico"
        return f"""{base_cea}

Tema Específico de la Sesión: {tema_info}
Duración de la Sesión: {horas} periodos.

INSTRUCCIÓN: Genera el PLAN DE AULA TALLER completo con la siguiente estructura obligatoria en formato Markdown con tablas:

# PLAN DE AULA TALLER
## {tema_info}
## CEA "Prof. Herman Ortiz Camargo" — {nivel} — Gestión 2026

### DATOS REFERENCIALES
| Campo | Dato |
|---|---|
| CEA | "Prof. Herman Ortiz Camargo" — Pailón |
| Especialidad | {carrera} |
| Nivel | {nivel} |
| Módulo | {modulo.get('nombre', '')} |
| Tema | {tema_info} |
| Duración | {horas} periodos |
| Fecha | _________________________ |
| Facilitador/a | _________________________ |

### OBJETIVO HOLÍSTICO DEL TEMA
(Redacta el objetivo holístico enfocado en la comprensión profunda y aplicación del tema específico.)

**SER:** ...
**SABER:** ...
**HACER:** ...
**DECIDIR:** ...

### TABLA DE DESARROLLO DE LA SESIÓN
| Momento | Objetivo Holístico | Contenido Temático Específico | Actividades del Facilitador | Actividades del Estudiante | Recursos | Tiempo |
|---|---|---|---|---|---|---|
| **PRÁCTICA** | | | | | | |
| **TEORÍA** | | | | | | |
| **VALORACIÓN** | | | | | | |
| **PRODUCCIÓN** | | | | | | |

### DESARROLLO METODOLÓGICO DETALLADO

**PRÁCTICA** (Descripción detallada de actividades iniciales, diagnóstico, experiencia directa con el tema.)

**TEORÍA** (Exposición teórica, conceptos clave, ejemplos técnicos, explicación paso a paso.)

**VALORACIÓN** (Reflexión crítica, debate, análisis del impacto en la comunidad boliviana.)

**PRODUCCIÓN** (Actividad de cierre, entregable concreto, ejercicio evaluativo.)

### PRODUCTO DE LA SESIÓN
(Define exactamente qué entregable técnico tendrá el estudiante al finalizar la sesión.)

### EVALUACIÓN DE LA SESIÓN
| Indicador | Instrumento | Puntaje |
|---|---|---|

GENERA EL PLAN COMPLETO Y DETALLADO AHORA."""


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
            subtitulo_num=req.subtitulo_num,
            generar_completo=req.generar_completo or False,
            horas=req.horas_sesion or 25,
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
