"""
malla.py — Gestión Curricular Institucional CEA
Permite a directores/jefes crear módulos con 4 temas para todas las carreras,
y a docentes gestionar solo sus niveles asignados. Soporta importación por Excel.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from database import get_db_connection
from routes.auth import get_current_user
from pydantic import BaseModel
from typing import Optional, List
import io
import json

router = APIRouter()


# ── Modelo para importación JSON desde el cliente ──────────────────
class TemaImport(BaseModel):
    numero: int
    titulo: str
    subtemas: Optional[str] = ""   # "A · B · C · D" separado por ·

class ModuloImport(BaseModel):
    nombre: str
    nivel: str
    area: Optional[str] = ""
    carrera_nombre: Optional[str] = ""
    numero: Optional[str] = ""
    temas: Optional[List[TemaImport]] = []



def rows_to_dicts(cursor, rows):
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, r)) for r in rows]


def require_malla_role(user, carrera_id=None):
    """
    Control de acceso jerárquico CEA:
    - Admin/Director: Acceso total.
    - Jefe de Carrera: Acceso si es el jefe asignado a la carrera técnica.
    - Profesor/Docente: Acceso total si la carrera es 'Humanística'.
    """
    rol = user["rol"].lower()
    if rol in ["admin", "administrador", "director"]:
        return True
    
    if not carrera_id:
        # Para listados globales, permitimos a personal docente
        if rol in ["jefe_carrera", "profesor", "docente"]:
            return True
        raise HTTPException(403, "Acceso restringido a personal administrativo")

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT area, jefe_id FROM carreras WHERE id=%s", (carrera_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Carrera no encontrada")
        
        area = str(row[0]).lower()
        jefe_id = row[1]
        
        # Área Técnica: Solo Jefe de Carrera (el asignado) o Admin
        if "técnica" in area:
            if rol == "jefe_carrera" and jefe_id == user["id"]:
                return True
            raise HTTPException(403, "Solo el Jefe de esta Carrera Técnica puede modificar su malla.")
            
        # Área Humanística: Cualquier profesor puede subir su malla
        if "humanística" in area:
            if rol in ["profesor", "docente", "jefe_carrera"]:
                return True
            raise HTTPException(403, "Solo personal docente puede gestionar mallas humanísticas.")
                
    finally:
        conn.close()
        
    raise HTTPException(403, "Sin permisos suficientes para esta operación curricular.")


# ─── MODELOS ─────────────────────────────────────────────────────────────────

class TemaCreate(BaseModel):
    numero: int  # 1, 2, 3, 4
    titulo: str
    subtitulos: Optional[List[str]] = []


class ModuloCreate(BaseModel):
    carrera_id: int
    nombre: str
    nivel: str              # "Técnico Básico", "Auxiliar", etc.
    subnivel: Optional[str] = None
    periodo: Optional[str] = None
    descripcion: Optional[str] = None
    area: Optional[str] = None   # 'Técnica' | 'Humanística'
    orden: Optional[int] = 0
    temas: List[TemaCreate] = []  # Exactamente 4


class ModuloUpdate(BaseModel):
    nombre: Optional[str] = None
    nivel: Optional[str] = None
    subnivel: Optional[str] = None
    periodo: Optional[str] = None
    descripcion: Optional[str] = None
    orden: Optional[int] = None
    temas: Optional[List[TemaCreate]] = None


# ─── ENDPOINTS PÚBLICOS ───────────────────────────────────────────────────────

@router.get("/carreras")
def get_carreras(current_user: dict = Depends(get_current_user)):
    """Lista carreras filtradas por rol."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        if current_user["rol"] == "estudiante":
            # Estudiante: Solo su carrera
            cur.execute("""
                SELECT c.id, c.nombre, c.area, c.descripcion, COUNT(m.id) as total_modulos
                FROM carreras c
                JOIN inscripciones i ON i.carrera_id = c.id
                LEFT JOIN modulos m ON m.carrera_id = c.id
                WHERE i.usuario_id = %s
                GROUP BY c.id, c.nombre, c.area, c.descripcion
            """, (current_user["id"],))
        elif current_user["rol"] in ["docente", "profesor"] and current_user.get("nivel_asignado"):
             # Docente: Podríamos filtrar, pero usualmente necesitan ver la carrera para gestionar
             cur.execute("""
                SELECT c.id, c.nombre, c.area, c.descripcion, COUNT(m.id) as total_modulos
                FROM carreras c
                LEFT JOIN modulos m ON m.carrera_id = c.id
                GROUP BY c.id, c.nombre, c.area, c.descripcion
                ORDER BY c.area, c.nombre
            """)
        else:
            cur.execute("""
                SELECT c.id, c.nombre, c.area, c.descripcion, COUNT(m.id) as total_modulos
                FROM carreras c
                LEFT JOIN modulos m ON m.carrera_id = c.id
                GROUP BY c.id, c.nombre, c.area, c.descripcion
                ORDER BY c.area, c.nombre
            """)
            
        return {"carreras": rows_to_dicts(cur, cur.fetchall())}
    finally:
        cur.close(); conn.close()


@router.delete("/carreras/{carrera_id}")
def delete_carrera(carrera_id: int, current_user: dict = Depends(get_current_user)):
    """Elimina una carrera específica (solo Director/Admin)."""
    if current_user["rol"] not in ["admin", "administrador", "director"]:
        raise HTTPException(403, "Solo el Director puede eliminar carreras")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT nombre FROM carreras WHERE id = %s", (carrera_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Carrera no encontrada")
        nombre = row[0]
        # Eliminar inscripciones y módulos relacionados primero (CASCADE debería manejarlo)
        cur.execute("DELETE FROM carreras WHERE id = %s", (carrera_id,))
        conn.commit()
        return {"mensaje": f"Carrera '{nombre}' eliminada correctamente"}
    except HTTPException: raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Error al eliminar carrera: {str(e)}")
    finally:
        cur.close(); conn.close()


@router.get("/{carrera_id}/estructura")
def get_estructura(carrera_id: int):
    """Estructura completa de una carrera: niveles → módulos → temas."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Info de la carrera
        cur.execute("SELECT id, nombre, area, descripcion FROM carreras WHERE id=%s", (carrera_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Carrera no encontrada")
        carrera = dict(zip([d[0] for d in cur.description], row))

        # Módulos con sus temas
        cur.execute("""
            SELECT m.id, m.nombre, m.nivel, m.subnivel, m.periodo,
                   m.descripcion, m.area, m.orden
            FROM modulos m
            WHERE m.carrera_id = %s
            ORDER BY m.nivel, m.orden, m.id
        """, (carrera_id,))
        modulos_raw = rows_to_dicts(cur, cur.fetchall())

        # Temas para cada módulo
        for mod in modulos_raw:
            cur.execute("""
                SELECT id, numero, titulo, subtitulos
                FROM temas
                WHERE modulo_id = %s
                ORDER BY numero
            """, (mod["id"],))
            mod["temas"] = rows_to_dicts(cur, cur.fetchall())

        # Agrupar por nivel
        niveles = {}
        for mod in modulos_raw:
            nivel_key = mod.get("nivel", "Sin nivel")
            if nivel_key not in niveles:
                niveles[nivel_key] = {"nivel": nivel_key, "modulos": []}
            niveles[nivel_key]["modulos"].append(mod)

        carrera["niveles"] = list(niveles.values())
        return carrera
    finally:
        cur.close(); conn.close()


@router.get("/estructura-completa")
def get_estructura_completa():
    """Vista institucional completa: todas las carreras con módulos y temas."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM carreras ORDER BY area, nombre")
        carrera_ids = [r[0] for r in cur.fetchall()]
        return [get_estructura(cid) for cid in carrera_ids]
    finally:
        cur.close(); conn.close()


# ─── CRUD MÓDULOS ─────────────────────────────────────────────────────────────

@router.post("/modulo")
def crear_modulo(data: ModuloCreate, current_user: dict = Depends(get_current_user)):
    """Crea un módulo con sus 4 temas."""
    require_malla_role(current_user, data.carrera_id)
    if len(data.temas) > 4:
        raise HTTPException(400, "Máximo 4 temas por módulo")

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO modulos (carrera_id, nombre, nivel, subnivel, periodo, descripcion, area, orden)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """, (
            data.carrera_id, data.nombre, data.nivel, data.subnivel,
            data.periodo, data.descripcion, data.area, data.orden or 0
        ))
        modulo_id = cur.fetchone()[0]

        # Insertar temas
        for i, tema in enumerate(data.temas):
            cur.execute("""
                INSERT INTO temas (modulo_id, numero, titulo, subtitulos)
                VALUES (%s,%s,%s,%s)
                ON CONFLICT (modulo_id, numero) DO UPDATE
                SET titulo=EXCLUDED.titulo, subtitulos=EXCLUDED.subtitulos
            """, (modulo_id, tema.numero or (i+1), tema.titulo,
                  __import__('json').dumps(tema.subtitulos or [])))

        conn.commit()
        return {"id": modulo_id, "mensaje": "Módulo creado correctamente"}
    except HTTPException:
        conn.rollback(); raise
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


@router.put("/modulo/{modulo_id}")
def editar_modulo(modulo_id: int, data: ModuloUpdate, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT carrera_id FROM modulos WHERE id=%s", (modulo_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Módulo no encontrado")
        require_malla_role(current_user, row[0])

        # Actualizar campos que lleguen
        updates = []
        vals = []
        for field in ["nombre", "nivel", "subnivel", "periodo", "descripcion", "orden"]:
            val = getattr(data, field)
            if val is not None:
                updates.append(f"{field}=%s")
                vals.append(val)

        if updates:
            vals.append(modulo_id)
            cur.execute(f"UPDATE modulos SET {', '.join(updates)} WHERE id=%s", vals)

        # Actualizar temas si vienen
        if data.temas is not None:
            import json
            for i, tema in enumerate(data.temas):
                cur.execute("""
                    INSERT INTO temas (modulo_id, numero, titulo, subtitulos)
                    VALUES (%s,%s,%s,%s)
                    ON CONFLICT (modulo_id, numero) DO UPDATE
                    SET titulo=EXCLUDED.titulo, subtitulos=EXCLUDED.subtitulos
                """, (modulo_id, tema.numero or (i+1), tema.titulo,
                      json.dumps(tema.subtitulos or [])))

        conn.commit()
        return {"mensaje": "Módulo actualizado"}
    except HTTPException:
        conn.rollback(); raise
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


@router.delete("/modulo/{modulo_id}")
def eliminar_modulo(modulo_id: int, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT carrera_id FROM modulos WHERE id=%s", (modulo_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Módulo no encontrado")
        require_malla_role(current_user, row[0])
        cur.execute("DELETE FROM modulos WHERE id=%s", (modulo_id,))
        conn.commit()
        return {"mensaje": "Módulo eliminado"}
    except HTTPException:
        conn.rollback(); raise
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()


# ─── IMPORTAR DESDE EXCEL ────────────────────────────────────────────────────

@router.post("/{carrera_id}/importar-excel")
async def importar_malla_excel(
    carrera_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Importa la malla curricular desde Excel.
    Formato de columnas:
    Nivel | Semestre | Nombre Módulo | Área | Tema1 | Sub1 | Tema2 | Sub2 | Tema3 | Sub3 | Tema4 | Sub4
    Los subtítulos pueden ir separados por / dentro de la celda.
    """
    require_malla_role(current_user, carrera_id)
    try:
        import openpyxl, json
        contents = await file.read()
        wb = openpyxl.load_workbook(io.BytesIO(contents))
        ws = wb.active

        conn = get_db_connection()
        cur = conn.cursor()

        # Verificar que la carrera existe
        cur.execute("SELECT nombre FROM carreras WHERE id=%s", (carrera_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Carrera no encontrada")

        creados = 0
        actualizados = 0
        errores = []

        for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row[0]:
                continue
            try:
                nivel       = str(row[0] or "").strip()
                semestre    = str(row[1] or "").strip()
                nombre_mod  = str(row[2] or "").strip()
                area        = str(row[3] or "Técnica").strip()
                periodo     = semestre or nivel

                if not nombre_mod:
                    continue

                # Temas y subtítulos (columnas 4-11: T1,Sub1,T2,Sub2,T3,Sub3,T4,Sub4)
                temas_data = []
                for i in range(4):
                    col_t = 4 + (i * 2)
                    col_s = col_t + 1
                    t_titulo = str(row[col_t] or "").strip() if len(row) > col_t else ""
                    t_subs_raw = str(row[col_s] or "").strip() if len(row) > col_s else ""
                    if t_titulo:
                        subs = [s.strip() for s in t_subs_raw.split("/") if s.strip()] if t_subs_raw else []
                        temas_data.append({"numero": i+1, "titulo": t_titulo, "subtitulos": subs})

                # Insertar módulo
                cur.execute("""
                    INSERT INTO modulos (carrera_id, nombre, nivel, subnivel, periodo, area, orden)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT DO NOTHING
                    RETURNING id
                """, (carrera_id, nombre_mod, nivel, semestre, periodo, area, creados))
                result = cur.fetchone()

                if result:
                    modulo_id = result[0]
                    creados += 1
                else:
                    # Ya existe, buscar ID
                    cur.execute("SELECT id FROM modulos WHERE carrera_id=%s AND nombre=%s AND nivel=%s",
                                (carrera_id, nombre_mod, nivel))
                    existing = cur.fetchone()
                    if not existing:
                        continue
                    modulo_id = existing[0]
                    actualizados += 1

                # Insertar/actualizar temas
                for t in temas_data:
                    cur.execute("""
                        INSERT INTO temas (modulo_id, numero, titulo, subtitulos)
                        VALUES (%s,%s,%s,%s)
                        ON CONFLICT (modulo_id, numero) DO UPDATE
                        SET titulo=EXCLUDED.titulo, subtitulos=EXCLUDED.subtitulos
                    """, (modulo_id, t["numero"], t["titulo"], json.dumps(t["subtitulos"])))

            except Exception as e:
                errores.append(f"Fila {row_num}: {str(e)}")
                conn.rollback()
                continue

        # Log de importación
        cur.execute("""
            INSERT INTO malla_imports (usuario_id, carrera_id, archivo_nombre, modulos_importados)
            VALUES (%s,%s,%s,%s)
        """, (current_user["id"], carrera_id, file.filename, creados))

        conn.commit()
        return {
            "creados": creados,
            "actualizados": actualizados,
            "errores": errores,
            "mensaje": f"Importación completada: {creados} módulos nuevos, {actualizados} actualizados"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error procesando Excel: {str(e)}")
    finally:
        try:
            cur.close(); conn.close()
        except:
            pass


@router.get("/historial-importaciones")
def historial_importaciones(current_user: dict = Depends(get_current_user)):
    require_malla_role(current_user)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT mi.id, c.nombre as carrera, mi.archivo_nombre,
                   mi.modulos_importados, mi.fecha, u.nombre as importado_por
            FROM malla_imports mi
            JOIN carreras c ON mi.carrera_id = c.id
            JOIN usuarios u ON mi.usuario_id = u.id
            ORDER BY mi.fecha DESC LIMIT 50
        """)
        return {"importaciones": rows_to_dicts(cur, cur.fetchall())}
    finally:
        cur.close(); conn.close()


# ─── IMPORTAR MALLA DESDE JSON (cliente parsea el Excel) ────────────────────

@router.post("/importar")
def importar_malla_json(data: ModuloImport, current_user: dict = Depends(get_current_user)):
    """
    Recibe un módulo completo (nombre, nivel, área, carrera, temas con subtemas)
    procesado en el cliente desde el Excel de Malla Curricular CEA.
    Busca o crea la carrera automáticamente.
    """
    if current_user["rol"] not in ["jefe_carrera", "director", "administrador", "admin"]:
        raise HTTPException(403, "Solo Jefe de Carrera o Director pueden importar la malla.")

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # 1. Resolver carrera (buscar por nombre, o crear si no existe)
        area = (data.area or "Técnica").strip()
        carrera_nombre = (data.carrera_nombre or data.nombre).strip()

        cur.execute(
            "SELECT id FROM carreras WHERE LOWER(nombre) = LOWER(%s) LIMIT 1",
            (carrera_nombre,)
        )
        row = cur.fetchone()
        if row:
            carrera_id = row[0]
        else:
            # Crear la carrera automáticamente
            cur.execute(
                "SELECT id FROM subsistemas LIMIT 1"
            )
            sub = cur.fetchone()
            subsistema_id = sub[0] if sub else 1
            cur.execute(
                "INSERT INTO carreras (subsistema_id, nombre, area) VALUES (%s, %s, %s) RETURNING id",
                (subsistema_id, carrera_nombre, area)
            )
            carrera_id = cur.fetchone()[0]

        nivel = data.nivel.strip()

        # 2. Insertar el módulo (upsert por nombre+nivel+carrera_id)
        cur.execute("""
            SELECT id FROM modulos
            WHERE carrera_id = %s AND LOWER(nombre) = LOWER(%s) AND nivel = %s
            LIMIT 1
        """, (carrera_id, data.nombre, nivel))
        mod_row = cur.fetchone()

        if mod_row:
            modulo_id = mod_row[0]
        else:
            cur.execute("""
                INSERT INTO modulos (carrera_id, nombre, nivel, area, orden)
                VALUES (%s, %s, %s, %s, 0) RETURNING id
            """, (carrera_id, data.nombre, nivel, area))
            modulo_id = cur.fetchone()[0]

        # 3. Insertar los temas con sus subtemas
        for tema in (data.temas or []):
            # Convertir "A · B · C · D" a lista JSON
            subs_raw = (tema.subtemas or "").strip()
            subs_list = [s.strip() for s in subs_raw.split("·") if s.strip()] if subs_raw else []

            cur.execute("""
                INSERT INTO temas (modulo_id, numero, titulo, subtitulos)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (modulo_id, numero) DO UPDATE
                SET titulo = EXCLUDED.titulo, subtitulos = EXCLUDED.subtitulos
            """, (modulo_id, tema.numero, tema.titulo, json.dumps(subs_list, ensure_ascii=False)))

        conn.commit()
        return {
            "mensaje": f"Módulo '{data.nombre}' importado correctamente.",
            "modulo_id": modulo_id,
            "carrera_id": carrera_id
        }

    except HTTPException:
        conn.rollback(); raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Error al importar módulo: {str(e)}")
    finally:
        cur.close(); conn.close()

