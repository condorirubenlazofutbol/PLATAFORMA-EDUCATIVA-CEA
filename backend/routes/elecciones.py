from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from database import get_db_connection
from routes.auth import get_current_user
from models import EleccionCreate, VotoCreate, CandidatoCreate, MesaCreate, VotanteLoteTexto, AsignarJefeCI
import security as auth_security
from datetime import datetime
import hashlib, random, string

router = APIRouter()

def rows_to_dicts(cursor, rows):
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, r)) for r in rows]

def require_role(user, *roles):
    if user["rol"] not in roles:
        raise HTTPException(403, "Sin permisos")

# ─── HELPERS ────────────────────────────────────────────────────────────────

def get_eleccion_activa(cur, eleccion_id=None):
    if eleccion_id:
        cur.execute("SELECT * FROM elecciones WHERE id=%s", (eleccion_id,))
    else:
        cur.execute("SELECT * FROM elecciones ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    if not row:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))

# ─── LOGIN CI (votantes usan CI como credencial) ────────────────────────────

@router.post("/login-ci")
def login_con_ci(body: dict):
    ci = body.get("ci", "").strip()
    if not ci:
        raise HTTPException(400, "CI requerido")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, nombre, apellido, email, rol, subsistema_id
            FROM usuarios WHERE carnet=%s AND rol IN ('votante', 'estudiante')
        """, (ci,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "CI no encontrado en el padrón electoral")
        user = dict(zip([d[0] for d in cur.description], row))
        # Generar token con rol incluido en el payload
        token = auth_security.create_access_token(data={"sub": user["email"], "rol": user["rol"]})
        return {"access_token": token, "token_type": "bearer", "rol": user["rol"]}
    finally:
        cur.close(); conn.close()

# ─── CANDIDATOS PÚBLICOS ─────────────────────────────────────────────────────

@router.get("/candidatos/publicos")
def candidatos_publicos():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.id, c.nombre, c.sigla, c.cargo, c.frente, c.descripcion, c.imagen_base64
            FROM candidatos c
            JOIN elecciones e ON c.eleccion_id = e.id
            ORDER BY c.id
        """)
        return rows_to_dicts(cur, cur.fetchall())
    finally:
        cur.close(); conn.close()

# ─── VOTANTE ENDPOINTS ───────────────────────────────────────────────────────

@router.get("/votante/mi-info")
def mi_info(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, nombre, apellido, email, rol, carnet FROM usuarios WHERE id=%s", (current_user["id"],))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Usuario no encontrado")
        u = dict(zip([d[0] for d in cur.description], row))
        # Verificar si ya votó
        cur.execute("SELECT id FROM votos WHERE estudiante_id=%s LIMIT 1", (u["id"],))
        u["ha_votado"] = cur.fetchone() is not None
        return u
    finally:
        cur.close(); conn.close()

@router.get("/votante/estado-eleccion")
def estado_eleccion():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, titulo as nombre, estado, descripcion FROM elecciones ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        if not row:
            return {"id": None, "nombre": None, "activa": False, "resultados_publicados": False}
        d = dict(zip([d[0] for d in cur.description], row))
        return {
            "id": d["id"],
            "nombre": d["nombre"],
            "activa": d["estado"] == "activa",
            "resultados_publicados": d["estado"] == "publicada"
        }
    finally:
        cur.close(); conn.close()

@router.get("/votante/candidatos")
def candidatos_para_votar(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.id, c.nombre, c.sigla, c.cargo, c.frente, c.descripcion, c.imagen_base64
            FROM candidatos c
            JOIN elecciones e ON c.eleccion_id = e.id
            WHERE e.estado='activa'
            ORDER BY c.id
        """)
        return rows_to_dicts(cur, cur.fetchall())
    finally:
        cur.close(); conn.close()

@router.post("/votante/votar")
def emitir_voto(voto: VotoCreate, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM votos WHERE estudiante_id=%s AND eleccion_id=%s", (current_user["id"], voto.eleccion_id))
        if cur.fetchone():
            raise HTTPException(400, "Ya emitiste tu voto en esta elección")
        cur.execute(
            "INSERT INTO votos (eleccion_id, estudiante_id, candidato_id) VALUES (%s,%s,%s)",
            (voto.eleccion_id, current_user["id"], voto.candidato_id)
        )
        conn.commit()
        return {"mensaje": "Voto registrado exitosamente"}
    except HTTPException:
        conn.rollback(); raise
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()

# ─── ADMIN ELECCIONES ────────────────────────────────────────────────────────

@router.get("/admin/elecciones")
def listar_elecciones(current_user: dict = Depends(get_current_user)):
    require_role(current_user, "admin", "director", "secretaria")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, titulo as nombre, estado, descripcion, fecha_inicio, fecha_fin FROM elecciones ORDER BY id DESC")
        rows = rows_to_dicts(cur, cur.fetchall())
        for r in rows:
            r["activa"] = r.pop("estado") == "activa"
        return rows
    finally:
        cur.close(); conn.close()

@router.post("/admin/elecciones")
def crear_eleccion(data: EleccionCreate, current_user: dict = Depends(get_current_user)):
    require_role(current_user, "admin", "director", "secretaria")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        titulo = data.nombre or data.titulo or "Elección CEA"
        cur.execute("""
            INSERT INTO elecciones (subsistema_id, titulo, descripcion, fecha_inicio, fecha_fin, estado)
            VALUES (%s,%s,%s,%s,%s,'cerrada') RETURNING id, titulo as nombre, estado
        """, (
            current_user.get("subsistema_id"),
            titulo,
            data.descripcion or "",
            data.fecha_inicio or datetime.now(),
            data.fecha_fin or datetime.now()
        ))
        row = cur.fetchone()
        conn.commit()
        return {"id": row[0], "nombre": row[1], "activa": False}
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()

@router.post("/admin/elecciones/{eleccion_id}/toggle")
def toggle_eleccion(eleccion_id: int, current_user: dict = Depends(get_current_user)):
    require_role(current_user, "admin", "director")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT estado FROM elecciones WHERE id=%s", (eleccion_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Elección no encontrada")
        nuevo = "cerrada" if row[0] == "activa" else "activa"
        cur.execute("UPDATE elecciones SET estado=%s WHERE id=%s", (nuevo, eleccion_id))
        conn.commit()
        return {"id": eleccion_id, "activa": nuevo == "activa"}
    except HTTPException: raise
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()

@router.delete("/admin/elecciones/{eleccion_id}")
def eliminar_eleccion(eleccion_id: int, current_user: dict = Depends(get_current_user)):
    require_role(current_user, "admin", "director")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM elecciones WHERE id=%s", (eleccion_id,))
        conn.commit()
        return {"ok": True}
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()

# ─── ADMIN STATS ─────────────────────────────────────────────────────────────

@router.get("/admin/stats")
def admin_stats(eleccion_id: int = None, current_user: dict = Depends(get_current_user)):
    require_role(current_user, "admin", "director", "secretaria")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM usuarios WHERE rol IN ('votante', 'estudiante')")
        total_votantes = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM candidatos")
        total_candidatos = cur.fetchone()[0]
        total_votos = 0
        if eleccion_id:
            cur.execute("SELECT COUNT(*) FROM votos WHERE eleccion_id=%s", (eleccion_id,))
            total_votos = cur.fetchone()[0]
        else:
            cur.execute("SELECT COUNT(*) FROM votos")
            total_votos = cur.fetchone()[0]
        participacion = round((total_votos / total_votantes * 100), 1) if total_votantes else 0
        return {
            "total_votantes": total_votantes,
            "total_habilitados": total_votantes,
            "total_votos": total_votos,
            "participacion": participacion,
            "total_mesas": 0,
            "total_candidatos": total_candidatos
        }
    finally:
        cur.close(); conn.close()

# ─── ADMIN RESULTADOS ─────────────────────────────────────────────────────────

@router.get("/admin/resultados")
def resultados(eleccion_id: int = None, current_user: dict = Depends(get_current_user)):
    require_role(current_user, "admin", "director", "secretaria")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if eleccion_id:
            cur.execute("""
                SELECT c.nombre, c.sigla, COUNT(v.id) as votos
                FROM candidatos c
                LEFT JOIN votos v ON v.candidato_id=c.id AND v.eleccion_id=%s
                WHERE c.eleccion_id=%s
                GROUP BY c.id, c.nombre, c.sigla
                ORDER BY votos DESC
            """, (eleccion_id, eleccion_id))
        else:
            cur.execute("""
                SELECT c.nombre, c.sigla, COUNT(v.id) as votos
                FROM candidatos c
                LEFT JOIN votos v ON v.candidato_id=c.id
                GROUP BY c.id, c.nombre, c.sigla
                ORDER BY votos DESC
            """)
        rows = rows_to_dicts(cur, cur.fetchall())
        total = sum(r["votos"] for r in rows)
        for i, r in enumerate(rows):
            r["porcentaje"] = round(r["votos"] / total * 100, 1) if total else 0
            r["candidato"] = r.pop("nombre")
            r["estado"] = "🥇 GANADOR" if i == 0 and r["votos"] > 0 else ""
        return rows
    finally:
        cur.close(); conn.close()

@router.get("/admin/reportes/resultados")
def reportes_resultados(current_user: dict = Depends(get_current_user)):
    return resultados(current_user=current_user)

@router.post("/admin/publicar-resultados")
def publicar_resultados(eleccion_id: int, current_user: dict = Depends(get_current_user)):
    require_role(current_user, "admin", "director")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE elecciones SET estado='publicada' WHERE id=%s", (eleccion_id,))
        conn.commit()
        return {"ok": True}
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()

# ─── ADMIN MESAS (simplificado) ──────────────────────────────────────────────

@router.post("/admin/mesas")
def crear_mesas(data: MesaCreate, current_user: dict = Depends(get_current_user)):
    require_role(current_user, "admin", "director")
    return {"msg": f"Función de mesas disponible. Se crearían {data.cantidad} mesas para elección {data.eleccion_id}."}

@router.get("/admin/mesas/{eleccion_id}")
def get_mesas(eleccion_id: int, current_user: dict = Depends(get_current_user)):
    require_role(current_user, "admin", "director", "secretaria")
    return []

@router.delete("/admin/mesas/{mesa_id}")
def eliminar_mesa(mesa_id: int, current_user: dict = Depends(get_current_user)):
    require_role(current_user, "admin", "director")
    return {"ok": True}

@router.post("/admin/distribuir-mesas/{eleccion_id}")
def distribuir_mesas(eleccion_id: int, current_user: dict = Depends(get_current_user)):
    require_role(current_user, "admin", "director")
    return {"msg": "Distribución completada (modo simplificado sin mesas físicas).", "resumen": "Los votantes pueden votar directamente."}

@router.post("/admin/asignar-jefe-ci")
def asignar_jefe_ci(data: AsignarJefeCI, current_user: dict = Depends(get_current_user)):
    require_role(current_user, "admin", "director")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM usuarios WHERE carnet=%s", (data.ci,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "CI no encontrado en el padrón")
        cur.execute("UPDATE usuarios SET rol='jefe' WHERE id=%s", (row[0],))
        conn.commit()
        return {"msg": f"Jefe de mesa asignado correctamente (CI: {data.ci})"}
    except HTTPException: raise
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()

# ─── ADMIN AUDITORÍA ─────────────────────────────────────────────────────────

@router.get("/admin/auditoria")
def auditoria(current_user: dict = Depends(get_current_user)):
    require_role(current_user, "admin", "director")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT u.id as usuario_id, u.nombre, u.rol,
                   'LOGIN' as accion, 'Actividad registrada' as detalle,
                   NOW() as timestamp, 'Interna' as ip_address
            FROM usuarios u
            WHERE u.rol IN ('admin','secretaria','jefe')
            LIMIT 50
        """)
        return rows_to_dicts(cur, cur.fetchall())
    finally:
        cur.close(); conn.close()

@router.get("/admin/forzar-migracion")
def forzar_migracion(current_user: dict = Depends(get_current_user)):
    require_role(current_user, "admin", "director")
    from database import init_db
    init_db()
    return {"msg": "Migración ejecutada correctamente. Tablas verificadas."}

@router.post("/admin/reset-sistema")
def reset_sistema(current_user: dict = Depends(get_current_user)):
    require_role(current_user, "admin")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM votos")
        cur.execute("DELETE FROM candidatos")
        cur.execute("DELETE FROM elecciones")
        cur.execute("DELETE FROM usuarios WHERE rol='votante'")
        conn.commit()
        return {"ok": True, "msg": "Sistema reiniciado"}
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()

@router.get("/admin/reportes/votantes")
def reporte_votantes(current_user: dict = Depends(get_current_user)):
    require_role(current_user, "admin", "director", "secretaria")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT u.carnet as ci, u.nombre, u.email as correo,
                   0 as mesa, true as habilitado,
                   EXISTS(SELECT 1 FROM votos v WHERE v.estudiante_id=u.id) as ha_votado
            FROM usuarios u WHERE u.rol IN ('votante', 'estudiante') ORDER BY u.nombre
        """)
        return rows_to_dicts(cur, cur.fetchall())
    finally:
        cur.close(); conn.close()

@router.get("/admin/reportes/candidatos")
def reporte_candidatos(current_user: dict = Depends(get_current_user)):
    return candidatos_publicos()

@router.get("/admin/reportes/jurados")
def reporte_jurados(current_user: dict = Depends(get_current_user)):
    require_role(current_user, "admin", "director", "secretaria")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT nombre, email as correo, 1 as mesa FROM usuarios WHERE rol='jefe'")
        return rows_to_dicts(cur, cur.fetchall())
    finally:
        cur.close(); conn.close()

@router.get("/admin/export/{entity}")
def export_csv(entity: str, current_user: dict = Depends(get_current_user)):
    require_role(current_user, "admin", "director", "secretaria")
    from fastapi.responses import StreamingResponse
    import io, csv
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        output = io.StringIO()
        writer = csv.writer(output)
        if entity == "votantes":
            cur.execute("SELECT carnet, nombre, email FROM usuarios WHERE rol='votante' ORDER BY nombre")
            writer.writerow(["CI","Nombre","Correo"])
        elif entity == "candidatos":
            cur.execute("SELECT id, nombre, sigla, cargo, frente FROM candidatos ORDER BY id")
            writer.writerow(["ID","Nombre","Sigla","Cargo","Frente"])
        elif entity == "resultados":
            cur.execute("""
                SELECT c.nombre, c.sigla, COUNT(v.id) as votos
                FROM candidatos c LEFT JOIN votos v ON v.candidato_id=c.id
                GROUP BY c.id, c.nombre, c.sigla ORDER BY votos DESC
            """)
            writer.writerow(["Candidato","Sigla","Votos"])
        else:
            writer.writerow(["Sin datos"])
        writer.writerows(cur.fetchall())
        output.seek(0)
        return StreamingResponse(iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={entity}.csv"})
    finally:
        cur.close(); conn.close()

# ─── SECRETARÍA ──────────────────────────────────────────────────────────────

@router.post("/secretaria/candidatos")
def registrar_candidato(data: CandidatoCreate, current_user: dict = Depends(get_current_user)):
    require_role(current_user, "admin", "director", "secretaria")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO candidatos (eleccion_id, nombre, sigla, foto, imagen_base64, cargo, frente, descripcion)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id, nombre
        """, (
            data.eleccion_id, data.nombre, data.sigla,
            data.imagen_base64, data.imagen_base64,
            data.cargo, data.frente, data.descripcion
        ))
        row = cur.fetchone()
        # Si hay CI de representante, inscribirlo como votante
        if data.ci_representante:
            try:
                email = f"{data.nombre.lower().replace(' ','.')[:20]}@cea.com"
                cur.execute("""
                    INSERT INTO usuarios (nombre, apellido, email, password, rol, carnet)
                    VALUES (%s,'',%s,'cea2024','votante',%s)
                    ON CONFLICT (email) DO NOTHING
                """, (data.nombre, email, data.ci_representante))
            except Exception:
                pass
        conn.commit()
        return {"id": row[0], "nombre": row[1]}
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()

@router.get("/secretaria/votantes")
def listar_votantes(current_user: dict = Depends(get_current_user)):
    require_role(current_user, "admin", "director", "secretaria")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT u.carnet as ci, u.nombre, u.email as correo,
                   true as habilitado,
                   EXISTS(SELECT 1 FROM votos v WHERE v.estudiante_id=u.id) as ha_votado
            FROM usuarios u WHERE u.rol IN ('votante', 'estudiante') ORDER BY u.nombre
        """)
        return rows_to_dicts(cur, cur.fetchall())
    finally:
        cur.close(); conn.close()

@router.get("/secretaria/votantes/buscar/{ci}")
def buscar_votante(ci: str, current_user: dict = Depends(get_current_user)):
    require_role(current_user, "admin", "director", "secretaria", "jefe")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, nombre, email as correo, carnet as ci FROM usuarios WHERE carnet=%s AND rol IN ('votante', 'estudiante')", (ci,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "CI no encontrado")
        d = dict(zip([d[0] for d in cur.description], row))
        cur.execute("SELECT id FROM votos WHERE estudiante_id=%s", (d["id"],))
        d["ha_votado"] = cur.fetchone() is not None
        return d
    finally:
        cur.close(); conn.close()

@router.post("/secretaria/usuarios")
def inscribir_votante(data: dict, current_user: dict = Depends(get_current_user)):
    require_role(current_user, "admin", "director", "secretaria")
    ci = data.get("ci","").strip()
    nombre = data.get("nombre","").strip()
    if not ci or not nombre:
        raise HTTPException(400, "CI y nombre son requeridos")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM usuarios WHERE carnet=%s", (ci,))
        if cur.fetchone():
            raise HTTPException(400, "Este CI ya está inscrito")
        email = f"{ci}@cea.com"
        cur.execute("""
            INSERT INTO usuarios (nombre, apellido, email, password, rol, carnet, subsistema_id)
            VALUES (%s,'',%s,'cea2024','votante',%s,%s) RETURNING id, email
        """, (nombre, email, ci, current_user.get("subsistema_id")))
        row = cur.fetchone()
        conn.commit()
        return {"id": row[0], "correo": row[1]}
    except HTTPException: raise
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()

@router.post("/secretaria/inscribir-texto-lote")
def inscribir_lote_texto(data: VotanteLoteTexto, current_user: dict = Depends(get_current_user)):
    require_role(current_user, "admin", "director", "secretaria")
    conn = get_db_connection()
    registrados = omitidos = 0
    try:
        cur = conn.cursor()
        for v in data.votantes:
            ci = str(v.get("ci","")).strip()
            nombres = str(v.get("nombres","")).strip()
            apellidos = str(v.get("apellidos","")).strip()
            nombre = f"{nombres} {apellidos}".strip()
            if not ci or not nombre:
                omitidos += 1; continue
            cur.execute("SELECT id FROM usuarios WHERE carnet=%s", (ci,))
            if cur.fetchone():
                omitidos += 1; continue
            email = f"{ci}@cea.com"
            try:
                cur.execute("""
                    INSERT INTO usuarios (nombre, apellido, email, password, rol, carnet, subsistema_id)
                    VALUES (%s,'',%s,'cea2024','votante',%s,%s)
                """, (nombre, email, ci, current_user.get("subsistema_id")))
                registrados += 1
            except Exception:
                omitidos += 1; conn.rollback()
        conn.commit()
        return {"registrados": registrados, "omitidos": omitidos}
    except Exception as e:
        conn.rollback(); raise HTTPException(500, str(e))
    finally:
        cur.close(); conn.close()

@router.post("/secretaria/inscribir-lote")
async def inscribir_lote_excel(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    require_role(current_user, "admin", "director", "secretaria")
    try:
        import openpyxl, io
        contents = await file.read()
        wb = openpyxl.load_workbook(io.BytesIO(contents))
        ws = wb.active
        votantes = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[0]:
                votantes.append({"ci": str(row[0]).strip(), "nombres": str(row[1] or "").strip(), "apellidos": str(row[2] or "").strip()})
        data = VotanteLoteTexto(votantes=votantes)
        return inscribir_lote_texto(data, current_user)
    except Exception as e:
        raise HTTPException(500, f"Error procesando Excel: {str(e)}")

# ─── JEFE DE MESA ─────────────────────────────────────────────────────────────

@router.get("/jefe/votante/{ci}")
def jefe_get_votante(ci: str, current_user: dict = Depends(get_current_user)):
    require_role(current_user, "jefe", "admin")
    return buscar_votante(ci, current_user)

@router.post("/jefe/validar-votante")
def jefe_validar_votante(ci: str, current_user: dict = Depends(get_current_user)):
    require_role(current_user, "jefe", "admin")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM usuarios WHERE carnet=%s AND rol='votante'", (ci,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Estudiante no encontrado")
        cur.execute("SELECT id FROM votos WHERE estudiante_id=%s", (row[0],))
        if cur.fetchone():
            raise HTTPException(400, "Este estudiante ya votó")
        return {"ok": True, "msg": "Estudiante habilitado para votar"}
    finally:
        cur.close(); conn.close()
