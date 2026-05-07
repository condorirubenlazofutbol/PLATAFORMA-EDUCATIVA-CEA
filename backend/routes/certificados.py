import uuid
from fastapi import APIRouter, Depends, HTTPException
from database import get_db_connection
from routes.auth import get_current_user

router = APIRouter()

def rows_to_dicts(cursor, rows):
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, r)) for r in rows]

@router.post("/certificados/emitir/{modulo_id}")
def emitir_certificado(modulo_id: int, current_user: dict = Depends(get_current_user)):
    if current_user["rol"] not in ["estudiante"]:
        raise HTTPException(status_code=403, detail="Solo los estudiantes pueden emitir sus propios certificados")
        
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # Verificar si ya existe
        cur.execute("SELECT id FROM certificados WHERE estudiante_id = %s AND modulo_id = %s", (current_user["id"], modulo_id))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="El certificado ya fue emitido para este módulo")
            
        # Generar código QR único (simulado con UUID)
        codigo_qr = str(uuid.uuid4())
        
        cur.execute(
            "INSERT INTO certificados (estudiante_id, modulo_id, codigo_qr) VALUES (%s, %s, %s) RETURNING id, fecha_emision",
            (current_user["id"], modulo_id, codigo_qr)
        )
        row = cur.fetchone()
        conn.commit()
        
        return {
            "mensaje": "Certificado emitido con éxito",
            "certificado_id": row[0],
            "codigo_qr": codigo_qr,
            "fecha_emision": row[1]
        }
    except HTTPException as he:
        conn.rollback()
        raise he
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close(); conn.close()

@router.get("/certificados/mis-certificados")
def mis_certificados(current_user: dict = Depends(get_current_user)):
    if current_user["rol"] != "estudiante":
        raise HTTPException(status_code=403, detail="Acceso denegado")
        
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.id, c.codigo_qr, c.fecha_emision, m.nombre as modulo, m.nivel 
            FROM certificados c
            JOIN modulos m ON c.modulo_id = m.id
            WHERE c.estudiante_id = %s
            ORDER BY c.fecha_emision DESC
        """, (current_user["id"],))
        
        return {"certificados": rows_to_dicts(cur, cur.fetchall())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close(); conn.close()
