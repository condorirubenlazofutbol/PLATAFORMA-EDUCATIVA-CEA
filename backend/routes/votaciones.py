from fastapi import APIRouter, Depends, HTTPException
from database import get_db_connection
from routes.auth import get_current_user
from models import EleccionCreate, VotoCreate
from datetime import datetime

router = APIRouter()

def rows_to_dicts(cursor, rows):
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, r)) for r in rows]

@router.post("/elecciones")
def crear_eleccion(eleccion: EleccionCreate, current_user: dict = Depends(get_current_user)):
    if current_user["rol"] not in ["director", "secretaria"]:
        raise HTTPException(status_code=403, detail="No tienes permisos")
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO elecciones (subsistema_id, titulo, descripcion, fecha_inicio, fecha_fin) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (current_user.get("subsistema_id"), eleccion.titulo, eleccion.descripcion, eleccion.fecha_inicio, eleccion.fecha_fin)
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        return {"id": new_id, "mensaje": "Elección creada"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close(); conn.close()

@router.get("/elecciones/activas")
def obtener_elecciones_activas(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        subsistema_id = current_user.get("subsistema_id")
        # Mostrar activas y dentro del rango de fechas
        cur.execute("""
            SELECT id, titulo, descripcion, fecha_inicio, fecha_fin, estado 
            FROM elecciones 
            WHERE subsistema_id = %s AND estado = 'activa' AND NOW() BETWEEN fecha_inicio AND fecha_fin
        """, (subsistema_id,))
        return {"elecciones": rows_to_dicts(cur, cur.fetchall())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close(); conn.close()

@router.post("/votar")
def emitir_voto(voto: VotoCreate, current_user: dict = Depends(get_current_user)):
    if current_user["rol"] != "estudiante":
        raise HTTPException(status_code=403, detail="Solo los estudiantes pueden votar")
        
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Verificar que no haya votado ya
        cur.execute("SELECT id FROM votos WHERE eleccion_id = %s AND estudiante_id = %s", (voto.eleccion_id, current_user["id"]))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Ya has emitido tu voto en esta elección")
            
        cur.execute(
            "INSERT INTO votos (eleccion_id, estudiante_id, candidato_id) VALUES (%s, %s, %s)",
            (voto.eleccion_id, current_user["id"], voto.candidato_id)
        )
        conn.commit()
        return {"mensaje": "Voto registrado exitosamente"}
    except HTTPException as he:
        conn.rollback()
        raise he
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close(); conn.close()
