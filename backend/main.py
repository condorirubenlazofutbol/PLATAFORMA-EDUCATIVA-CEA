# Final stable version for EduConnect Ruben
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from routes import auth, modulos, evaluaciones, comunicados, ai_tools, certificados, votaciones, notas, elecciones
from database import init_db

load_dotenv()

app = FastAPI(title="Educonnect-Ruben API", description="LMS Backend – EduConnect Ruben v21.0 PRO")

@app.on_event("startup")
def startup_event():
    print("Servidor EduConnect Ruben iniciado correctamente.")
    try:
        from database import init_db
        init_db()
        print("Migración y seeding automático completado.")
    except Exception as e:
        print(f"Migración startup warning: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,         prefix="/auth",         tags=["Authentication"])
app.include_router(modulos.router,      prefix="/modulos",      tags=["Modulos"])
app.include_router(evaluaciones.router, prefix="/evaluaciones", tags=["Evaluaciones"])
app.include_router(comunicados.router,  prefix="/comunicados",  tags=["Comunicados"])
app.include_router(ai_tools.router,     prefix="/ai",           tags=["AI Tools"])
app.include_router(certificados.router, prefix="/certificados", tags=["Certificados"])
app.include_router(votaciones.router,   prefix="/votaciones",   tags=["Votaciones"])
app.include_router(notas.router,        prefix="/notas",        tags=["Notas"])
app.include_router(elecciones.router,   tags=["Elecciones"])  # Sin prefijo: /admin/*, /votante/*, /secretaria/*, /candidatos/*

@app.get("/")
def read_root():
    db_status = "error"
    try:
        from database import get_db_connection
        conn = get_db_connection()
        if conn:
            db_status = "connected"
            conn.close()
    except Exception as e:
        db_status = str(e)
    return {
        "client":   "Educonnect-Ruben",
        "status":   "online",
        "version":  "21.0.0 PRO",
        "database": db_status == "connected",
        "author":   "Antigravity AI"
    }

@app.get("/cargar-datos")
def instalar_datos_iniciales():
    """Inicializa tablas, crea usuarios por defecto y carga la malla curricular."""
    try:
        import importlib
        import seed
        import seed_cea
        import database
        importlib.reload(database)
        importlib.reload(seed)
        importlib.reload(seed_cea)

        database.init_db()
        seed.seed_users()
        reparados = seed_cea.seed_cea_data()

        from database import get_db_connection
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("SELECT email, rol FROM usuarios ORDER BY id")
        users = cur.fetchall()
        cur.execute("SELECT COUNT(*) FROM modulos")
        total_mods = cur.fetchone()[0]
        cur.close(); conn.close()

        return {
            "status":           "success",
            "version":          "21.0.0 PRO",
            "modulos_creados":  reparados,
            "total_en_bd":      total_mods,
            "usuarios":         [{"email": u[0], "rol": u[1]} for u in users]
        }
    except Exception as e:
        return {"status": "error", "detalle": str(e)}
