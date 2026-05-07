import os
from fastapi import APIRouter, Depends, HTTPException
from database import get_db_connection
from routes.auth import get_current_user
from models import PlanificacionCreate
# import openai  # Descomentar cuando tengas la API key

router = APIRouter()

# Configurar tu API Key de OpenAI o Gemini en el archivo .env
# openai.api_key = os.getenv("OPENAI_API_KEY")

@router.post("/generar-planificacion")
def generar_planificacion(data: PlanificacionCreate, current_user: dict = Depends(get_current_user)):
    if current_user["rol"] not in ["docente", "profesor"]:
        raise HTTPException(status_code=403, detail="Solo los docentes pueden generar planificaciones")
        
    # --- SIMULACIÓN DE LLAMADA A IA ---
    # En producción, reemplazar este bloque con la llamada real:
    # response = openai.ChatCompletion.create(
    #     model="gpt-4",
    #     messages=[
    #         {"role": "system", "content": "Eres un experto en pedagogía. Genera un plan de clase detallado para el tema proporcionado."},
    #         {"role": "user", "content": f"Tema: {data.tema}"}
    #     ]
    # )
    # contenido_generado = response['choices'][0]['message']['content']
    
    contenido_generado = f"""
    # Planificación Pedagógica Generada por IA
    **Tema:** {data.tema}
    
    ## 1. Objetivos de Aprendizaje
    - Comprender los conceptos fundamentales de {data.tema}.
    - Aplicar el conocimiento en casos prácticos.
    
    ## 2. Metodología
    - Clase magistral interactiva (20 min)
    - Trabajo grupal / Taller (30 min)
    - Evaluación formativa (10 min)
    
    ## 3. Recursos Necesarios
    - Presentación en diapositivas.
    - Casos de estudio en PDF.
    - Pizarra y marcadores.
    
    ## 4. Criterios de Evaluación
    - Participación activa.
    - Resolución correcta del caso de estudio.
    """
    # ----------------------------------
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO planificaciones (docente_id, modulo_id, contenido_ia) VALUES (%s, %s, %s) RETURNING id",
            (current_user["id"], data.modulo_id, contenido_generado)
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        return {
            "id": new_id, 
            "mensaje": "Planificación generada y guardada con éxito",
            "contenido": contenido_generado
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close(); conn.close()
