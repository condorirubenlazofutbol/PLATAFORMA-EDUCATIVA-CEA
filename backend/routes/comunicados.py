from fastapi import APIRouter, Depends, HTTPException
from database import get_db_connection
from routes.auth import get_current_user
from models import AvisoCreate

router = APIRouter()

def rows_to_dicts(cursor, rows):
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, r)) for r in rows]

@router.post("/avisos", status_code=201)
def create_aviso(aviso: AvisoCreate, current_user: dict = Depends(get_current_user)):
    if current_user["rol"] not in ["director", "secretaria", "admin", "administrador"]:
        raise HTTPException(status_code=403, detail="No tienes permiso para publicar avisos")
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO avisos_institucionales (subsistema_id, autor_id, titulo, contenido, target_area, target_nivel, target_paralelo) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (current_user.get("subsistema_id"), current_user["id"], aviso.titulo, aviso.contenido, aviso.target_area, aviso.target_nivel, aviso.target_paralelo)
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        return {"id": new_id, "mensaje": "Aviso publicado exitosamente"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close(); conn.close()

@router.get("/avisos")
def get_avisos(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        subsistema_id = current_user.get("subsistema_id")
        
        if current_user["rol"] == "estudiante":
            cur.execute("""
                SELECT a.id, a.titulo, a.contenido, a.target_area, a.target_nivel, a.target_paralelo, a.fecha_creacion, u.nombre || ' ' || u.apellido as autor 
                FROM avisos_institucionales a 
                JOIN usuarios u ON a.autor_id = u.id 
                WHERE (a.subsistema_id = %s OR a.subsistema_id IS NULL)
                AND (
                    (a.target_area IS NULL AND a.target_nivel IS NULL AND a.target_paralelo IS NULL)
                    OR EXISTS (
                        SELECT 1 FROM inscripciones i 
                        JOIN carreras c ON i.carrera_id = c.id
                        WHERE i.usuario_id = %s AND i.estado = 'activo'
                        AND (a.target_area IS NULL OR a.target_area = '' OR c.area = a.target_area)
                        AND (a.target_nivel IS NULL OR a.target_nivel = '' OR i.nivel = a.target_nivel)
                        AND (a.target_paralelo IS NULL OR a.target_paralelo = '' OR i.paralelo = a.target_paralelo)
                    )
                )
                ORDER BY a.fecha_creacion DESC
            """, (subsistema_id, current_user["id"]))
        else:
            if subsistema_id:
                cur.execute("""
                    SELECT a.id, a.titulo, a.contenido, a.target_area, a.target_nivel, a.target_paralelo, a.fecha_creacion, u.nombre || ' ' || u.apellido as autor 
                    FROM avisos_institucionales a 
                    JOIN usuarios u ON a.autor_id = u.id 
                    WHERE a.subsistema_id = %s 
                    ORDER BY a.fecha_creacion DESC
                """, (subsistema_id,))
            else:
                cur.execute("""
                    SELECT a.id, a.titulo, a.contenido, a.target_area, a.target_nivel, a.target_paralelo, a.fecha_creacion, u.nombre || ' ' || u.apellido as autor 
                    FROM avisos_institucionales a 
                    JOIN usuarios u ON a.autor_id = u.id 
                    WHERE a.subsistema_id IS NULL
                    ORDER BY a.fecha_creacion DESC
                """)
        
        return {"avisos": rows_to_dicts(cur, cur.fetchall())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close(); conn.close()

@router.delete("/avisos/{aviso_id}")
def delete_aviso(aviso_id: int, current_user: dict = Depends(get_current_user)):
    if current_user["rol"] not in ["director", "secretaria", "admin", "administrador"]:
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar avisos")
        
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Usamos IS NOT DISTINCT FROM para manejar correctamente los valores NULL en subsistema_id
        cur.execute("DELETE FROM avisos_institucionales WHERE id = %s AND subsistema_id IS NOT DISTINCT FROM %s", (aviso_id, current_user.get("subsistema_id")))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Aviso no encontrado o no pertenece a tu subsistema")
        conn.commit()
        return {"mensaje": "Aviso eliminado"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close(); conn.close()
