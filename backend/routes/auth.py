from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Optional
from database import get_db_connection
import security as auth, psycopg2, io, openpyxl

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

class RegistroEstudiante(BaseModel):
    nombre: str
    apellido: str
    carnet: str
    nivel_asignado: Optional[str] = None

class RegistroProfesorBody(BaseModel):
    nombre: str
    apellido: str
    email: str
    password: str
    nivel_asignado: str

class TokenData(BaseModel):
    username: str | None = None

def rows_to_dicts(cursor, rows):
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, r)) for r in rows]

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection error")
        cur = conn.cursor()
        cur.execute("SELECT id, nombre, email, password, rol, nivel_asignado FROM usuarios WHERE email=%s", (form_data.username,))
        row = cur.fetchone()
        cur.close(); conn.close()
        
        if not row:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
            
        is_valid = False
        try:
            is_valid = auth.verify_password(form_data.password, row[3])
        except Exception as ve:
            raise HTTPException(status_code=500, detail=f"Error verificando password: {str(ve)}")

        if not is_valid:
            raise HTTPException(status_code=401, detail="Contraseña incorrecta")

        token = auth.create_access_token(data={"sub": row[2]})
        return {"access_token": token, "token_type": "bearer",
                "rol": row[4], "nombre": row[1], "nivel_asignado": row[5]}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login crash: {str(e)}")


@router.get("/me")
def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = auth.decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido")
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database error")
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, apellido, email, rol, nivel_asignado FROM usuarios WHERE email=%s", (payload.get("sub"),))
    row = cur.fetchone()
    cur.close(); conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"id": row[0], "nombre": row[1], "apellido": row[2], "email": row[3], "rol": row[4], "nivel_asignado": row[5]}

@router.post("/register-profesor", dependencies=[Depends(get_current_user)])
def register_profesor(nombre: str, apellido: str, carnet: str, nivel_asignado: str):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")
    try:
        cur = conn.cursor()
        # Generar email: nombre.apellido@educonnect.com (sin espacios)
        email = f"{nombre.strip().split(' ')[0].lower()}.{apellido.strip().split(' ')[0].lower()}@educonnect.com"
        
        # Hash del carnet como password inicial
        hashed = auth.get_password_hash(carnet)
        
        cur.execute(
            "INSERT INTO usuarios (nombre, apellido, email, password, rol, nivel_asignado, carnet) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (nombre, apellido, email, hashed, "profesor", nivel_asignado, carnet)
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close(); conn.close()
        return {"id": new_id, "mensaje": f"Profesor {nombre} creado para nivel {nivel_asignado}"}
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.post("/register-estudiante", dependencies=[Depends(get_current_user)])
def register_estudiante(data: RegistroEstudiante):
    """El admin inscribe un nuevo estudiante. Email y Password se generan automáticamente."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")
    try:
        cur = conn.cursor()
        # Generar email y password inicial
        email = f"{data.nombre.strip().split(' ')[0].lower()}.{data.apellido.strip().split(' ')[0].lower()}@educonnect.com"
        hashed = auth.get_password_hash(data.carnet)

        cur.execute(
            "INSERT INTO usuarios (nombre, apellido, email, password, rol, nivel_asignado, carnet) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (data.nombre, data.apellido, email, hashed, "estudiante", data.nivel_asignado, data.carnet)
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        return {"id": new_id, "email": data.email, "mensaje": f"Estudiante {data.nombre} inscrito correctamente"}
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.get("/estudiantes", dependencies=[Depends(get_current_user)])
def get_estudiantes():
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, nombre, apellido, email, nivel_asignado FROM usuarios WHERE rol='estudiante' ORDER BY nivel_asignado, nombre")
        return {"estudiantes": rows_to_dicts(cur, cur.fetchall())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.get("/profesores")
def get_profesores():
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, nombre, apellido, email, nivel_asignado FROM usuarios WHERE rol='profesor' ORDER BY nivel_asignado")
        return {"profesores": rows_to_dicts(cur, cur.fetchall())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.delete("/usuarios/{usuario_id}", dependencies=[Depends(get_current_user)])
def delete_usuario(usuario_id: int):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")
    try:
        cur = conn.cursor()
        # Primero verificamos si el usuario existe
        cur.execute("SELECT email FROM usuarios WHERE id = %s", (usuario_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
            
        cur.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))
        conn.commit()
        return {"mensaje": "Usuario eliminado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

class PasswordResetBody(BaseModel):
    new_password: str

@router.put("/usuarios/{usuario_id}/password", dependencies=[Depends(get_current_user)])
def reset_password(usuario_id: int, data: PasswordResetBody):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")
    try:
        cur = conn.cursor()
        hashed = auth.get_password_hash(data.new_password)
        cur.execute("UPDATE usuarios SET password = %s WHERE id = %s", (hashed, usuario_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        conn.commit()
        return {"mensaje": "Contraseña restablecida correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.put("/update-password")
def update_my_password(data: PasswordResetBody, current_user: dict = Depends(get_current_user)):
    """Permite al usuario logueado cambiar su propia contraseña."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        hashed = auth.get_password_hash(data.new_password)
        cur.execute("UPDATE usuarios SET password = %s WHERE id = %s", (hashed, current_user["id"]))
        conn.commit()
        return {"mensaje": "Tu contraseña ha sido actualizada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.post("/bulk-register", dependencies=[Depends(get_current_user)])
async def bulk_register(nivel: str, rol: str = "estudiante", file: UploadFile = File(...)):
    """Carga masiva de usuarios (estudiante o profesor) desde Excel (.xlsx)."""
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="El archivo debe ser .xlsx")
    
    contents = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(contents))
    sheet = wb.active
    
    registrados = 0
    errores = []
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    for row in sheet.iter_rows(min_row=2, values_only=True):
        nombre, apellido, carnet = row
        if not nombre or not carnet: continue
        
        try:
            email = f"{str(nombre).strip().split(' ')[0].lower()}.{str(apellido).strip().split(' ')[0].lower()}@educonnect.com"
            hashed = auth.get_password_hash(str(carnet))
            
            cur.execute(
                "INSERT INTO usuarios (nombre, apellido, email, password, rol, nivel_asignado, carnet) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (str(nombre), str(apellido), email, hashed, rol, nivel, str(carnet))
            )
            registrados += 1
        except Exception as e:
            errores.append(f"Error en fila {nombre}: {str(e)}")
            continue

    conn.commit()
    cur.close(); conn.close()
    
    return {
        "status": "done",
        "registrados": registrados,
        "errores": errores
    }
