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

app = FastAPI(title="Educonnect-Ruben API", description="LMS Backend for educational platform")

@app.on_event("startup")
def startup_event():
    """Arranque ultra-rápido para evitar timeouts en Render."""
    print("Servidor EduConnect iniciado correctamente.")


# CORS Configuration

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permitir todos los orígenes para facilitar integraciones
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(modulos.router, prefix="/modulos", tags=["Modulos"])
app.include_router(evaluaciones.router, prefix="/evaluaciones", tags=["Evaluaciones"])

@app.get("/")
def read_root():
    db_status = "error"
    db_detail = "No se detectó DATABASE_URL ni INTERNAL_DATABASE_URL"
    
    try:
        from database import get_db_connection
        conn = get_db_connection()
        if conn:
            db_status = "connected"
            db_detail = "Conexión exitosa"
            conn.close()
    except Exception as e:
        db_detail = str(e)

    return {
        "client": "Educonnect-Ruben",
        "status": "online",
        "version": "5.0.0 PRO MAX Stable",
        "database": db_status == "connected",
        "author": "Antigravity AI"
    }



@app.get("/cargar-datos")
def instalar_datos_iniciales():
    """Endpoint manual para forzar la recarga de datos maestros."""
    try:
        import importlib
        import seed
        import seed_modulos
        import database
        importlib.reload(seed)
        importlib.reload(seed_modulos)
        importlib.reload(database)
        
        database.init_db()
        reparados = seed_modulos.seed_data()
        
        # Verificación final
        from database import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT email, rol, password FROM usuarios")
        users = cur.fetchall()
        cur.close(); conn.close()
        
        return {
            "status": "success",
            "version_actual": "4.2.0 DIAGNOSTIC",
            "modulos_reparados": reparados,
            "usuarios": [{"email": u[0], "rol": u[1], "prefix": u[2][:10]} for u in users]
        }

    except Exception as e:
        return {"status": "error", "detalle": str(e)}


    except Exception as e:
        return {"status": "error", "detalle": str(e)}


