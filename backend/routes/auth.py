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
    carrera_id: Optional[int] = None

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

def generate_cea_email(nombre: str, apellido: str):
    clean_n = nombre.strip().replace(" ", "").lower()
    clean_a = apellido.strip().replace(" ", "").lower()
    # Limitar longitud para evitar correos gigantes
    return f"{clean_n}{clean_a}"[:30] + "@ceapilon.com"

@router.post("/register-usuario", dependencies=[Depends(get_current_user)])
def register_usuario(data: RegistroUsuario):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")
    try:
        cur = conn.cursor()
        email = generate_cea_email(data.nombre, data.apellido)
        hashed = auth.get_password_hash(str(data.carnet).strip())
        
        # Verificar si ya existe el carnet
        cur.execute("SELECT id FROM usuarios WHERE carnet=%s", (str(data.carnet).strip(),))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="El carnet ya está registrado.")

        cur.execute(
            "INSERT INTO usuarios (subsistema_id, nombre, apellido, email, password, rol, nivel_asignado, carnet) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (data.subsistema_id or 1, data.nombre.strip(), data.apellido.strip(), email, hashed, data.rol, data.nivel_asignado, str(data.carnet).strip())
        )
        new_id = cur.fetchone()[0]
        
        # --- Lógica de Inscripción Inteligente Pro ---
        if data.rol == "estudiante" and data.nivel_asignado:
            nivel_str = data.nivel_asignado
            
            # Área Técnica (formato: "Carrera - Nivel")
            if " - " in nivel_str:
                parts = nivel_str.split(" - ")
                carrera_nombre = parts[0].strip()
                nivel_nombre = parts[1].strip()
                
                cur.execute("SELECT id FROM carreras WHERE nombre = %s AND area = 'Técnica'", (carrera_nombre,))
                c_row = cur.fetchone()
                if c_row:
                    c_id = c_row[0]
                    cur.execute("INSERT INTO inscripciones (usuario_id, carrera_id, nivel) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", (new_id, c_id, nivel_nombre))
                    
                    # Matricular automáticamente en sus 5 módulos
                    cur.execute("SELECT id FROM modulos WHERE carrera_id = %s AND nivel = %s", (c_id, nivel_nombre))
                    modulos = cur.fetchall()
                    for mod in modulos:
                        cur.execute("INSERT INTO progreso (usuario_id, modulo_id, estado) VALUES (%s, %s, 'cursando') ON CONFLICT DO NOTHING", (new_id, mod[0]))
            
            # Área Humanística (formato: "Nivel")
            else:
                nivel_nombre = nivel_str.strip()
                cur.execute("SELECT id FROM carreras WHERE area = 'Humanística'")
                carreras_hum = cur.fetchall()
                for c_row in carreras_hum:
                    c_id = c_row[0]
                    cur.execute("INSERT INTO inscripciones (usuario_id, carrera_id, nivel) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", (new_id, c_id, nivel_nombre))
                    
                    # Matricular automáticamente en sus 2 módulos por materia
                    cur.execute("SELECT id FROM modulos WHERE carrera_id = %s AND nivel = %s", (c_id, nivel_nombre))
                    modulos = cur.fetchall()
                    for mod in modulos:
                        cur.execute("INSERT INTO progreso (usuario_id, modulo_id, estado) VALUES (%s, %s, 'cursando') ON CONFLICT DO NOTHING", (new_id, mod[0]))

        if data.carrera_id:
            cur.execute(
                "INSERT INTO inscripciones (usuario_id, carrera_id, nivel) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                (new_id, data.carrera_id, data.nivel_asignado)
            )
            
        conn.commit()
        return {"id": new_id, "email": email, "mensaje": f"Usuario {data.nombre} ({data.rol}) creado exitosamente"}
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=400, detail="El email generado ya existe. Contacte a soporte.")
    except HTTPException: raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close(); conn.close()

@router.post("/importar-estudiantes-excel")
async def importar_estudiantes_excel(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    if current_user["rol"] not in ["admin", "director", "secretaria"]:
        raise HTTPException(403, "No autorizado")
    
    try:
        contents = await file.read()
        wb = openpyxl.load_workbook(io.BytesIO(contents))
        ws = wb.active
        
        registrados = 0
        errores = []
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Esperamos columnas: Carnet, Nombres, Apellidos, Area (humanistica/tecnica), Nivel
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row[0]: continue
            
            carnet = str(row[0]).strip()
            nombres = str(row[1] or "").strip()
            apellidos = str(row[2] or "").strip()
            area = str(row[3] or "humanistica").lower().strip()
            nivel = str(row[4] or "Primer Semestre").strip()
            
            email = generate_cea_email(nombres, apellidos)
            password = auth.get_password_hash(carnet)
            
            try:
                cur.execute(
                    "INSERT INTO usuarios (subsistema_id, nombre, apellido, email, password, rol, nivel_asignado, carnet) VALUES (1,%s,%s,%s,%s,'estudiante',%s,%s)",
                    (nombres, apellidos, email, password, nivel, carnet)
                )
                registrados += 1
            except Exception as e:
                conn.rollback()
                errores.append(f"Error en CI {carnet}: {str(e)}")
                continue
            
        conn.commit()
        cur.close(); conn.close()
        
        return {"registrados": registrados, "errores": errores}
    except Exception as e:
        raise HTTPException(500, f"Error procesando Excel: {str(e)}")


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
