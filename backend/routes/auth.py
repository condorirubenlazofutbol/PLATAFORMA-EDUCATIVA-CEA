from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Optional
from database import get_db_connection
import security as auth, psycopg2, io, openpyxl

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

class RegistroUsuario(BaseModel):
    nombre: str
    apellido: str
    carnet: str
    rol: str
    subsistema_id: int
    nivel_asignado: Optional[str] = None

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
        cur.execute("SELECT id, nombre, email, password, rol, nivel_asignado, estado, subsistema_id FROM usuarios WHERE email=%s", (form_data.username,))
        row = cur.fetchone()
        cur.close(); conn.close()
        
        if not row:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
            
        estado = row[6]
        if estado == 'pausado':
            raise HTTPException(status_code=403, detail="Tu cuenta está suspendida por falta de pago o por el administrador.")
            
        is_valid = False
        try:
            is_valid = auth.verify_password(form_data.password, row[3])
        except Exception as ve:
            raise HTTPException(status_code=500, detail=f"Error verificando password: {str(ve)}")

        if not is_valid:
            raise HTTPException(status_code=401, detail="Contraseña incorrecta")

        token = auth.create_access_token(data={"sub": row[2]})
        return {"access_token": token, "token_type": "bearer",
                "rol": row[4], "nombre": row[1], "nivel_asignado": row[5], "subsistema_id": row[7]}
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
    cur.execute("SELECT id, nombre, apellido, email, rol, nivel_asignado, subsistema_id FROM usuarios WHERE email=%s", (payload.get("sub"),))
    row = cur.fetchone()
    cur.close(); conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"id": row[0], "nombre": row[1], "apellido": row[2], "email": row[3], "rol": row[4], "nivel_asignado": row[5], "subsistema_id": row[6]}

@router.post("/register-usuario", dependencies=[Depends(get_current_user)])
def register_usuario(data: RegistroUsuario):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")
    try:
        cur = conn.cursor()
        clean_n = data.nombre.strip().split(' ')[0].lower()
        clean_a = data.apellido.strip().split(' ')[0].lower()
        email = f"{clean_n}.{clean_a}@educonnect.com"
        hashed = auth.get_password_hash(str(data.carnet).strip())
        try:
            cur.execute(
                "INSERT INTO usuarios (subsistema_id, nombre, apellido, email, password, rol, nivel_asignado, carnet) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (data.subsistema_id, data.nombre.strip(), data.apellido.strip(), email, hashed, data.rol, data.nivel_asignado, str(data.carnet).strip())
            )
        except Exception:
            conn.rollback()
            # fallback sin carnet
            cur.execute(
                "INSERT INTO usuarios (subsistema_id, nombre, apellido, email, password, rol, nivel_asignado) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (data.subsistema_id, data.nombre.strip(), data.apellido.strip(), email, hashed, data.rol, data.nivel_asignado)
            )
        new_id = cur.fetchone()[0]
        conn.commit()
        return {"id": new_id, "email": email, "mensaje": f"Usuario {data.nombre} ({data.rol}) creado"}
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=400, detail="El email ya está registrado. Verifica el carnet.")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close(); conn.close()

@router.get("/estudiantes", dependencies=[Depends(get_current_user)])
def get_estudiantes():
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, nombre, apellido, email, nivel_asignado, carnet, estado FROM usuarios WHERE rol='estudiante' ORDER BY nivel_asignado, nombre")
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
        cur.execute("SELECT id, nombre, apellido, email, nivel_asignado, carnet, estado FROM usuarios WHERE rol='profesor' ORDER BY nivel_asignado")
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

class EstadoUpdateBody(BaseModel):
    estado: str

@router.put("/usuarios/{usuario_id}/estado", dependencies=[Depends(get_current_user)])
def update_estado(usuario_id: int, data: EstadoUpdateBody):
    if data.estado not in ['activo', 'pausado']:
        raise HTTPException(status_code=400, detail="Estado inválido")
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")
    try:
        cur = conn.cursor()
        cur.execute("UPDATE usuarios SET estado = %s WHERE id = %s", (data.estado, usuario_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        conn.commit()
        return {"mensaje": f"Estado actualizado a {data.estado}"}
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
async def bulk_register(nivel: str, rol: str = "estudiante", file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
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
    
    subsistema_id = current_user.get("subsistema_id")
    
    for row in sheet.iter_rows(min_row=2, values_only=True):
        nombre, apellido, carnet = row
        if not nombre or not carnet: continue
        
        try:
            # Limpieza profunda para email
            clean_n = str(nombre).strip().split(' ')[0].lower()
            clean_a = str(apellido).strip().split(' ')[0].lower()
            email = f"{clean_n}.{clean_a}@educonnect.com"
            
            # Asegurar carnet como string y hash
            s_carnet = str(carnet).strip()
            hashed = auth.get_password_hash(s_carnet)
            
            cur.execute(
                "INSERT INTO usuarios (subsistema_id, nombre, apellido, email, password, rol, nivel_asignado, carnet) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (subsistema_id, str(nombre).strip(), str(apellido).strip(), email, hashed, rol, nivel, s_carnet)
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
