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
        rol_retornado = row[4]
        # Normalizar roles: unificar variantes para que el frontend funcione correctamente
        if rol_retornado == 'profesor':
            rol_retornado = 'docente'
        elif rol_retornado == 'jefe':
            rol_retornado = 'jefe_carrera'
        
        return {"access_token": token, "token_type": "bearer",
                "rol": rol_retornado, "nombre": row[1], "nivel_asignado": row[5], "subsistema_id": row[7]}
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
    # Usar solo primer nombre y primer apellido (paterno)
    clean_n = nombre.strip().split(" ")[0].lower()
    clean_a = apellido.strip().split(" ")[0].lower()
    return f"{clean_n}{clean_a}" + "@ceapailon.com"

def obtener_paralelo_disponible(cur, carrera_id, nivel, area):
    limite = 30 if str(area).lower() == 'técnica' else 40
    cur.execute('''
        SELECT paralelo, COUNT(*) 
        FROM inscripciones 
        WHERE carrera_id = %s AND nivel = %s
        GROUP BY paralelo
        ORDER BY paralelo ASC
    ''', (carrera_id, nivel))
    paralelos = cur.fetchall()
    
    if not paralelos: return 'A'
    for paralelo, count in paralelos:
        if count < limite: return paralelo
    ultimo_paralelo = paralelos[-1][0]
    return chr(ord(ultimo_paralelo) + 1) if len(ultimo_paralelo) == 1 and ultimo_paralelo.isalpha() else 'A'

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
                
                cur.execute("SELECT id, area FROM carreras WHERE nombre = %s AND area = 'Técnica'", (carrera_nombre,))
                c_row = cur.fetchone()
                if c_row:
                    c_id = c_row[0]
                    area = c_row[1]
                    paralelo = obtener_paralelo_disponible(cur, c_id, nivel_nombre, area)
                    cur.execute("INSERT INTO inscripciones (usuario_id, carrera_id, nivel, paralelo) VALUES (%s, %s, %s, %s) ON CONFLICT (usuario_id, carrera_id) DO UPDATE SET paralelo = EXCLUDED.paralelo", (new_id, c_id, nivel_nombre, paralelo))
                    
                    # Matricular automáticamente en sus 5 módulos
                    cur.execute("SELECT id FROM modulos WHERE carrera_id = %s AND nivel = %s", (c_id, nivel_nombre))
                    modulos = cur.fetchall()
                    for mod in modulos:
                        cur.execute("INSERT INTO progreso (usuario_id, modulo_id, estado) VALUES (%s, %s, 'cursando') ON CONFLICT DO NOTHING", (new_id, mod[0]))
            
            # Área Humanística (formato: "Nivel")
            else:
                nivel_nombre = nivel_str.strip()
                cur.execute("SELECT id, area FROM carreras WHERE area = 'Humanística'")
                carreras_hum = cur.fetchall()
                for c_row in carreras_hum:
                    c_id = c_row[0]
                    area = c_row[1]
                    paralelo = obtener_paralelo_disponible(cur, c_id, nivel_nombre, area)
                    cur.execute("INSERT INTO inscripciones (usuario_id, carrera_id, nivel, paralelo) VALUES (%s, %s, %s, %s) ON CONFLICT (usuario_id, carrera_id) DO UPDATE SET paralelo = EXCLUDED.paralelo", (new_id, c_id, nivel_nombre, paralelo))
                    
                    # Matricular automáticamente en sus 2 módulos por materia
                    cur.execute("SELECT id FROM modulos WHERE carrera_id = %s AND nivel = %s", (c_id, nivel_nombre))
                    modulos = cur.fetchall()
                    for mod in modulos:
                        cur.execute("INSERT INTO progreso (usuario_id, modulo_id, estado) VALUES (%s, %s, 'cursando') ON CONFLICT DO NOTHING", (new_id, mod[0]))

        if data.carrera_id:
            cur.execute("SELECT area FROM carreras WHERE id = %s", (data.carrera_id,))
            c_area_row = cur.fetchone()
            area = c_area_row[0] if c_area_row else 'Humanística'
            paralelo = obtener_paralelo_disponible(cur, data.carrera_id, data.nivel_asignado, area)
            cur.execute(
                "INSERT INTO inscripciones (usuario_id, carrera_id, nivel, paralelo) VALUES (%s, %s, %s, %s) ON CONFLICT (usuario_id, carrera_id) DO UPDATE SET paralelo = EXCLUDED.paralelo",
                (new_id, data.carrera_id, data.nivel_asignado, paralelo)
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

@router.get("/plantilla-estudiantes")
def descargar_plantilla_estudiantes():
    from fastapi.responses import StreamingResponse
    import io
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Estudiantes"
    
    headers = ["Carnet", "Nombres", "Apellidos", "Área (Técnica/Humanística)", "Nivel (Ej: 1er Semestre)"]
    ws.append(headers)
    
    # Algunos datos de ejemplo
    ws.append(["12345678", "Juan Perez", "Gomez", "Técnica", "Sistemas Informáticos"])
    ws.append(["87654321", "Maria", "Lopez", "Humanística", "Ciencias Naturales"])

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    
    return StreamingResponse(
        stream, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Plantilla_Estudiantes_CEA.xlsx"}
    )

@router.get("/plantilla-docentes")
def descargar_plantilla_docentes():
    from fastapi.responses import StreamingResponse
    import io
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Docentes"
    
    headers = ["Nombres", "Apellidos", "Carnet", "Especialidad / Carrera Asignada"]
    ws.append(headers)
    
    # Datos de ejemplo
    ws.append(["Carlos", "Mamani", "8877665", "Sistemas Informáticos"])
    ws.append(["Ana", "Suarez", "5544332", "Belleza Integral"])

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    
    return StreamingResponse(
        stream, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Plantilla_Docentes_CEA.xlsx"}
    )

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
        
        # Columnas: Nombre | Apellido | Carnet | Área | Nivel (mismo orden que plantilla docentes)
        for row in ws.iter_rows(min_row=2, values_only=True):
            # Ignorar filas completamente vacías
            if not row or not row[0]: continue
            
            nombres   = str(row[0]).strip() if len(row) > 0 and row[0] else ""
            apellidos = str(row[1]).strip() if len(row) > 1 and row[1] else ""
            carnet    = str(row[2]).strip() if len(row) > 2 and row[2] else ""
            area      = str(row[3]).lower().strip() if len(row) > 3 and row[3] else "humanistica"
            nivel     = str(row[4]).strip() if len(row) > 4 and row[4] else "Primer Semestre"
            
            # Validar que al menos tenga nombre y carnet
            if not nombres or not carnet:
                errores.append(f"Fila ignorada: nombre o carnet vacío")
                continue
            
            email = generate_cea_email(nombres, apellidos)
            password = auth.get_password_hash(carnet)
            
            try:
                # Buscar carrera por nombre (Especialidad / Area)
                cur.execute("SELECT id, area FROM carreras WHERE nombre ILIKE %s LIMIT 1", (f"%{area}%",))
                c_row = cur.fetchone()
                if not c_row:
                    # Crear carrera si no existe
                    db_area = 'Humanística' if 'human' in area.lower() else 'Técnica'
                    cur.execute("INSERT INTO carreras (nombre, area, subsistema_id) VALUES (%s, %s, 1) RETURNING id, area", (area, db_area))
                    c_row = cur.fetchone()
                
                carrera_id = c_row[0]
                db_area = c_row[1]
                
                # Insertar usuario — ON CONFLICT actualiza en vez de fallar si ya existe
                cur.execute(
                    """INSERT INTO usuarios (subsistema_id, nombre, apellido, email, password, rol, nivel_asignado, carnet)
                       VALUES (1,%s,%s,%s,%s,'estudiante',%s,%s)
                       ON CONFLICT (email) DO UPDATE SET
                           nombre = EXCLUDED.nombre,
                           apellido = EXCLUDED.apellido,
                           nivel_asignado = EXCLUDED.nivel_asignado,
                           carnet = EXCLUDED.carnet
                       RETURNING id""",
                    (nombres, apellidos, email, password, nivel, carnet)
                )
                new_id = cur.fetchone()[0]
                
                # Calcular paralelo
                paralelo = obtener_paralelo_disponible(cur, carrera_id, nivel, db_area)
                
                # Insertar en inscripciones
                cur.execute(
                    "INSERT INTO inscripciones (usuario_id, carrera_id, nivel, paralelo) VALUES (%s, %s, %s, %s) ON CONFLICT (usuario_id, carrera_id) DO UPDATE SET paralelo = EXCLUDED.paralelo",
                    (new_id, carrera_id, nivel, paralelo)
                )
                
                conn.commit() # Commit PER ROW to prevent losing previous rows on error
                registrados += 1
            except Exception as e:
                conn.rollback() # Solo deshace esta iteración porque las anteriores ya se hicieron commit
                errores.append(f"Error en CI {carnet}: {str(e)}")
                continue
            
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

@router.get("/usuarios")
def get_usuarios(current_user: dict = Depends(get_current_user)):
    """Lista todos los usuarios para la Secretaría/Director/Admin."""
    if current_user["rol"] not in ["admin", "administrador", "director", "secretaria"]:
        raise HTTPException(status_code=403, detail="No autorizado")
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT u.id, u.nombre, u.apellido, u.email, u.rol, u.nivel_asignado, 
                   u.carnet, u.estado, u.fecha_registro
            FROM usuarios u
            ORDER BY u.rol, u.nombre
        """)
        return rows_to_dicts(cur, cur.fetchall())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.get("/inscripciones")
def get_inscripciones(current_user: dict = Depends(get_current_user)):
    """Lista todas las inscripciones con datos del estudiante, carrera y paralelo."""
    if current_user["rol"] not in ["admin", "administrador", "director", "secretaria", "jefe_carrera"]:
        raise HTTPException(status_code=403, detail="No autorizado")
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                i.id, i.usuario_id, i.carrera_id, i.nivel, i.paralelo, i.estado, i.fecha_inscripcion,
                u.nombre, u.apellido, u.carnet, u.email,
                c.nombre AS carrera_nombre, c.area AS carrera_area
            FROM inscripciones i
            JOIN usuarios u ON u.id = i.usuario_id
            JOIN carreras c ON c.id = i.carrera_id
            ORDER BY c.area, c.nombre, i.nivel, i.paralelo, u.apellido
        """)
        return {"inscripciones": rows_to_dicts(cur, cur.fetchall())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.put("/inscripciones/{inscripcion_id}/estado")
def cambiar_estado_inscripcion(inscripcion_id: int, current_user: dict = Depends(get_current_user)):
    """Cambia el estado de una inscripción (activo/pausado/retirado)."""
    if current_user["rol"] not in ["admin", "administrador", "director", "secretaria"]:
        raise HTTPException(status_code=403, detail="No autorizado")
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")
    try:
        from pydantic import BaseModel as BM
        # State toggle: activo -> pausado -> retirado -> activo
        cur = conn.cursor()
        cur.execute("SELECT estado FROM inscripciones WHERE id=%s", (inscripcion_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Inscripción no encontrada")
        next_state = {"activo": "pausado", "pausado": "retirado", "retirado": "activo"}.get(row[0], "activo")
        cur.execute("UPDATE inscripciones SET estado=%s WHERE id=%s", (next_state, inscripcion_id))
        conn.commit()
        return {"nuevo_estado": next_state}
    finally:
        conn.close()

@router.get("/personal")
def get_personal(current_user: dict = Depends(get_current_user)):
    if current_user["rol"] not in ["admin", "director", "secretaria"]:
        raise HTTPException(status_code=403, detail="No autorizado")
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Error DB")
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, nombre, apellido, email, rol, nivel_asignado, carnet, estado FROM usuarios WHERE rol IN ('profesor', 'jefe_carrera', 'secretaria', 'director') ORDER BY rol, nombre")
        return {"personal": rows_to_dicts(cur, cur.fetchall())}
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

class EspecialidadUpdateBody(BaseModel):
    especialidad: str

@router.put("/usuarios/{usuario_id}/especialidad", dependencies=[Depends(get_current_user)])
def update_especialidad(usuario_id: int, data: EspecialidadUpdateBody):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")
    try:
        cur = conn.cursor()
        cur.execute("UPDATE usuarios SET nivel_asignado = %s WHERE id = %s AND rol IN ('docente', 'profesor')", (data.especialidad, usuario_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Docente no encontrado")
        conn.commit()
        return {"mensaje": f"Especialidad/Nivel actualizado correctamente a: {data.especialidad}"}
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
        nombre = row[0]
        carnet = row[2] if len(row) > 2 else None
        if not nombre or not carnet: continue
        
        apellido = row[1] if len(row) > 1 else ""
        # Si el excel tiene una 4ta columna, usarla como nivel/especialidad, sino usar el default
        actual_nivel = str(row[3]).strip() if len(row) > 3 and row[3] else nivel
        
        try:
            # Limpieza profunda para email
            clean_n = str(nombre).strip().split(' ')[0].lower()
            clean_a = str(apellido).strip().split(' ')[0].lower()
            email = f"{clean_n}{clean_a}@ceapailon.com"
            
            # Asegurar carnet como string y hash
            s_carnet = str(carnet).strip()
            hashed = auth.get_password_hash(s_carnet)
            
            cur.execute(
                "INSERT INTO usuarios (subsistema_id, nombre, apellido, email, password, rol, nivel_asignado, carnet) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (subsistema_id, str(nombre).strip(), str(apellido).strip(), email, hashed, rol, actual_nivel, s_carnet)
            )
            conn.commit() # Commit per row
            registrados += 1
        except Exception as e:
            conn.rollback() # Rollback solo esta fila
            errores.append(f"Error en fila {nombre}: {str(e)}")
            continue

    cur.close(); conn.close()
    
    return {
        "status": "done",
        "registrados": registrados,
        "errores": errores
    }

class PromoverDirectorRequest(BaseModel):
    usuario_id: int
    nuevo_rol: str # 'director' o 'secretaria'

@router.post("/promover-alta-direccion", dependencies=[Depends(get_current_user)])
def promover_alta_direccion(data: PromoverDirectorRequest, current_user: dict = Depends(get_current_user)):
    if current_user["rol"] != "admin":
        raise HTTPException(status_code=403, detail="Solo el Súper Admin puede realizar esta acción")
    if data.nuevo_rol not in ["director", "secretaria"]:
        raise HTTPException(status_code=400, detail="Rol inválido")
        
    conn = get_db_connection()
    if not conn: raise HTTPException(status_code=500, detail="Error DB")
    try:
        cur = conn.cursor()
        
        # 1. Identificar si ya hay alguien con este rol y degradarlo a profesor
        cur.execute("UPDATE usuarios SET rol = 'profesor' WHERE rol = %s", (data.nuevo_rol,))
        
        # 2. Ascender al nuevo usuario
        cur.execute("UPDATE usuarios SET rol = %s WHERE id = %s", (data.nuevo_rol, data.usuario_id))
        
        conn.commit()
        return {"mensaje": f"Usuario ascendido a {data.nuevo_rol} exitosamente. El anterior fue degradado a profesor."}
    finally:
        conn.close()

class PromoverJefeRequest(BaseModel):
    usuario_id: int
    carrera_id: Opt[int] = None
    especialidad_nombre: Opt[str] = None  # Nombre de la especialidad si no hay carrera_id

@router.post("/promover-jefe-carrera", dependencies=[Depends(get_current_user)])
def promover_jefe_carrera(data: PromoverJefeRequest, current_user: dict = Depends(get_current_user)):
    if current_user["rol"] not in ["admin", "director"]:
        raise HTTPException(status_code=403, detail="Solo la Dirección puede nombrar Jefes de Carrera")
        
    conn = get_db_connection()
    if not conn: raise HTTPException(status_code=500, detail="Error DB")
    try:
        cur = conn.cursor()

        # Resolver carrera_id: si viene especialidad_nombre, buscar o crear la carrera
        carrera_id = data.carrera_id
        if not carrera_id and data.especialidad_nombre:
            nombre_esp = data.especialidad_nombre.strip()
            cur.execute("SELECT id FROM carreras WHERE nombre ILIKE %s LIMIT 1", (nombre_esp,))
            c_row = cur.fetchone()
            if c_row:
                carrera_id = c_row[0]
            else:
                # Crear la carrera automáticamente sin subsistema_id estricto
                cur.execute(
                    "INSERT INTO carreras (nombre, area, subsistema_id) VALUES (%s, 'General', NULL) RETURNING id",
                    (nombre_esp,)
                )
                carrera_id = cur.fetchone()[0]
                conn.commit()

        if not carrera_id:
            raise HTTPException(status_code=400, detail="Debe especificar una carrera o especialidad")
        
        # 1. Encontrar quién era el jefe de esta carrera antes
        cur.execute("SELECT jefe_id FROM carreras WHERE id = %s", (carrera_id,))
        c_row = cur.fetchone()
        if not c_row:
            raise HTTPException(status_code=404, detail="Carrera no encontrada")
            
        antiguo_jefe_id = c_row[0]
        if antiguo_jefe_id:
            # Degradamos al antiguo jefe a profesor solo si era jefe_carrera
            cur.execute("UPDATE usuarios SET rol = 'profesor' WHERE id = %s AND rol = 'jefe_carrera'", (antiguo_jefe_id,))
            
        # 2. Promovemos al nuevo usuario a jefe_carrera
        cur.execute("UPDATE usuarios SET rol = 'jefe_carrera' WHERE id = %s", (data.usuario_id,))
        
        # 3. Asignamos en la tabla carreras
        cur.execute("UPDATE carreras SET jefe_id = %s WHERE id = %s", (data.usuario_id, carrera_id))
        
        conn.commit()
        return {"mensaje": "Profesor ascendido a Jefe de Carrera exitosamente."}
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error en promover_jefe_carrera: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
    finally:
        if conn: conn.close()
