# Final stable version for EduConnect Ruben
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from routes import auth, modulos, evaluaciones
from database import init_db

load_dotenv()

app = FastAPI(title="Educonnect-Ruben API", description="LMS Backend – EduConnect Ruben v5.0")

@app.on_event("startup")
def startup_event():
    print("Servidor EduConnect Ruben iniciado correctamente.")

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
        "version":  "5.0.0 PRO",
        "database": db_status == "connected",
        "author":   "Antigravity AI"
    }

@app.get("/cargar-datos")
def instalar_datos_iniciales():
    """Inicializa tablas, crea usuarios por defecto y carga la malla curricular."""
    try:
        import importlib
        import seed_modulos
        import database
        importlib.reload(database)
        importlib.reload(seed_modulos)

        database.init_db()
        reparados = seed_modulos.seed_data()

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
            "version":          "5.0.0 PRO",
            "modulos_creados":  reparados,
            "total_en_bd":      total_mods,
            "usuarios":         [{"email": u[0], "rol": u[1]} for u in users]
        }
    except Exception as e:
        return {"status": "error", "detalle": str(e)}
