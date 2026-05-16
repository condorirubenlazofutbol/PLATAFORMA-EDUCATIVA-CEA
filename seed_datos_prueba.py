"""
==============================================================================
  SCRIPT DE DATOS DE PRUEBA - PLATAFORMA CEA PAILÓN
==============================================================================
  Genera estudiantes y docentes de prueba usando la API del sistema.
  
  ESTRUCTURA:
  ─ ÁREA TÉCNICA
    ├── Sistemas Informáticos  → Básico (45 alum = 2 par.), Auxiliar, Medio I, Medio II (25 c/u)
    └── Contabilidad           → Básico (25 alum = 1 par.), Auxiliar, Medio I, Medio II
  ─ ÁREA HUMANÍSTICA
    ├── Aplicados (Primer Año)           → 45 alumnos (2 paralelos)
    ├── Complementarios (Segundo Año)    → 25 alumnos (1 paralelo)
    └── Especializados (Tercer Año)      → 25 alumnos (1 paralelo)
  
  USO:
    python seed_datos_prueba.py
  
  REQUISITOS:
    pip install requests openpyxl
==============================================================================
"""

import requests
import random
import os
import time

# ── Configuración ──────────────────────────────────────────────────────────────
API_BASE = "https://educonnect-backend-ql79.onrender.com"   # ← URL de tu backend
ADMIN_EMAIL    = "admin@ceapailon.com"                       # ← Credenciales director/admin
ADMIN_PASSWORD = "admin123"                                  # ← Contraseña

TURNO = "Noche"
SUBSISTEMA_ID = 1

# ── Bancos de Nombres ──────────────────────────────────────────────────────────
NOMBRES_M = [
    "Juan Carlos", "Pedro Luis", "Miguel Angel", "Carlos Eduardo", "Luis Fernando",
    "Jorge Alberto", "Diego Alejandro", "Rodrigo Andres", "Felipe Sebastian", "Nicolas Mateo",
    "Andres Felipe", "David Santiago", "Jose Manuel", "Alejandro Ivan", "Mario Antonio",
    "Roberto Carlos", "Hector Daniel", "Gustavo Adolfo", "Ricardo Gabriel", "Mauricio Esteban",
    "Christian Paul", "Edwin Omar", "Boris Ivan", "Freddy Marcelo", "Raul Enrique",
    "Hernan Dario", "Cristian Ariel", "Fabian Rolando", "Walter Efrain", "Victor Hugo"
]
NOMBRES_F = [
    "Maria Jose", "Ana Lucia", "Sandra Patricia", "Carmen Rosa", "Laura Beatriz",
    "Sofia Alejandra", "Valeria Fernanda", "Daniela Paola", "Gabriela Isabel", "Monica Elena",
    "Natalia Andrea", "Veronica Susana", "Patricia Lorena", "Claudia Marcela", "Silvia Rocio",
    "Paola Alexandra", "Jessica Tatiana", "Karina Estefania", "Lourdes Mirian", "Carla Noemi",
    "Diana Carolina", "Fernanda Beatriz", "Roxana Elizabeth", "Graciela Irene", "Yenny Lorena",
    "Lidia Angelica", "Ruth Noemi", "Celia Maribel", "Alicia Margoth", "Delia Beatriz"
]
APELLIDOS = [
    "Gutierrez", "Mamani", "Quispe", "Flores", "Garcia", "Martinez", "Rodriguez", "Lopez",
    "Sanchez", "Perez", "Torres", "Vargas", "Rojas", "Castro", "Ruiz", "Morales",
    "Jimenez", "Herrera", "Medina", "Aguilar", "Reyes", "Chavez", "Mendoza", "Varga",
    "Salazar", "Romero", "Alvarez", "Suarez", "Molina", "Ortega", "Delgado", "Ramos",
    "Cruz", "Lara", "Espinoza", "Carrillo", "Diaz", "Soto", "Montes", "Ibarra",
    "Palacios", "Cabrera", "Villanueva", "Campos", "Ceron", "Arce", "Blanco", "Ochoa",
    "Cordova", "Villalba"
]

# ── Nombres de Docentes ────────────────────────────────────────────────────────
DOCENTES = [
    # Técnica - Sistemas Informáticos
    {"nombre": "Luis", "apellido": "Villarroel", "especialidad": "Sistemas Informáticos"},
    {"nombre": "Roberto", "apellido": "Camacho",  "especialidad": "Sistemas Informáticos"},
    {"nombre": "Patricia", "apellido": "Medina",  "especialidad": "Sistemas Informáticos"},
    {"nombre": "Carlos", "apellido": "Torrez",    "especialidad": "Sistemas Informáticos"},
    # Técnica - Contabilidad
    {"nombre": "Sandra", "apellido": "Rivero",    "especialidad": "Contabilidad"},
    {"nombre": "Mario",  "apellido": "Suarez",    "especialidad": "Contabilidad"},
    {"nombre": "Elena",  "apellido": "Montero",   "especialidad": "Contabilidad"},
    {"nombre": "Jorge",  "apellido": "Salinas",   "especialidad": "Contabilidad"},
    # Humanística - Matemática
    {"nombre": "Jesus",  "apellido": "Mesias",    "especialidad": "Matemática"},
    # Humanística - Lenguaje
    {"nombre": "Ana",    "apellido": "Quiroga",   "especialidad": "Lenguaje"},
    # Humanística - Ciencias Naturales
    {"nombre": "Victor", "apellido": "Pedraza",   "especialidad": "Ciencias Naturales"},
    # Humanística - Ciencias Sociales
    {"nombre": "Rosa",   "apellido": "Mendez",    "especialidad": "Ciencias Sociales"},
]

# ── Estructura de Cursos ───────────────────────────────────────────────────────
# nivel_asignado para estudiantes técnicos: "Carrera - Nivel"
# nivel_asignado para humanística: solo "Nivel"

CURSOS_TECNICA = {
    "Sistemas Informáticos": [
        {"nivel_api": "Sistemas Informáticos - Nivel Básico",    "cantidad": 45, "label": "BASICO"},
        {"nivel_api": "Sistemas Informáticos - Nivel Auxiliar",  "cantidad": 25, "label": "AUXILIAR"},
        {"nivel_api": "Sistemas Informáticos - Nivel Medio I",   "cantidad": 25, "label": "MEDIO I"},
        {"nivel_api": "Sistemas Informáticos - Nivel Medio II",  "cantidad": 25, "label": "MEDIO II"},
    ],
    "Contabilidad": [
        {"nivel_api": "Contabilidad - Nivel Básico",    "cantidad": 25, "label": "BASICO"},
        {"nivel_api": "Contabilidad - Nivel Auxiliar",  "cantidad": 25, "label": "AUXILIAR"},
        {"nivel_api": "Contabilidad - Nivel Medio I",   "cantidad": 25, "label": "MEDIO I"},
        {"nivel_api": "Contabilidad - Nivel Medio II",  "cantidad": 25, "label": "MEDIO II"},
    ],
}

CURSOS_HUMANISTICA = [
    {"nivel_api": "Aplicados (Primer Año)",        "cantidad": 45, "label": "APLICADOS"},
    {"nivel_api": "Complementarios (Segundo Año)", "cantidad": 25, "label": "COMPLEMENTARIOS"},
    {"nivel_api": "Especializados (Tercer Año)",   "cantidad": 25, "label": "ESPECIALIZADOS"},
]

# ── Helpers ────────────────────────────────────────────────────────────────────
_usado_carnets = set()
_usado_idx = 0

def generar_persona(idx):
    nombres_pool = NOMBRES_M + NOMBRES_F
    nombre   = nombres_pool[idx % len(nombres_pool)]
    apellido = APELLIDOS[idx % len(APELLIDOS)] + " " + APELLIDOS[(idx + 7) % len(APELLIDOS)]
    while True:
        carnet = str(random.randint(10_000_000, 99_999_999))
        if carnet not in _usado_carnets:
            _usado_carnets.add(carnet)
            return nombre, apellido, carnet

def login():
    print(f"🔐 Autenticando como {ADMIN_EMAIL}...")
    r = requests.post(f"{API_BASE}/auth/login",
                      data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if r.status_code != 200:
        print(f"❌ Login fallido: {r.text}")
        exit(1)
    token = r.json()["access_token"]
    print(f"✅ Autenticado OK")
    return token

def registrar_usuario(token, nombre, apellido, carnet, rol, nivel_asignado):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "nombre": nombre,
        "apellido": apellido,
        "carnet": carnet,
        "rol": rol,
        "subsistema_id": SUBSISTEMA_ID,
        "nivel_asignado": nivel_asignado,
        "turno": TURNO
    }
    r = requests.post(f"{API_BASE}/auth/register-usuario", json=payload, headers=headers)
    return r.status_code, r.json()

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    token = login()
    print()

    total_ok  = 0
    total_err = 0
    idx = 0

    # ── 1. DOCENTES ────────────────────────────────────────────────────────────
    print("═" * 60)
    print("  👨‍🏫 REGISTRANDO DOCENTES")
    print("═" * 60)
    for doc in DOCENTES:
        carnet = str(random.randint(5_000_000, 9_999_999))
        _usado_carnets.add(carnet)
        status, resp = registrar_usuario(
            token,
            doc["nombre"], doc["apellido"], carnet,
            rol="docente",
            nivel_asignado=doc["especialidad"]
        )
        if status == 200:
            print(f"  ✅ Docente: {doc['apellido']} {doc['nombre']} → {doc['especialidad']}")
            total_ok += 1
        else:
            detail = resp.get("detail", resp)
            print(f"  ⚠️  Docente: {doc['apellido']} {doc['nombre']} → {detail}")
            total_err += 1
        time.sleep(0.3)

    print()

    # ── 2. ESTUDIANTES - TÉCNICA ───────────────────────────────────────────────
    print("═" * 60)
    print("  🎓 REGISTRANDO ESTUDIANTES — ÁREA TÉCNICA")
    print("═" * 60)
    for carrera, niveles in CURSOS_TECNICA.items():
        print(f"\n  📁 {carrera}")
        for curso in niveles:
            nivel_api = curso["nivel_api"]
            cantidad  = curso["cantidad"]
            label     = curso["label"]
            ok = 0; err = 0
            for _ in range(cantidad):
                nombre, apellido, carnet = generar_persona(idx); idx += 1
                status, resp = registrar_usuario(token, nombre, apellido, carnet, "estudiante", nivel_api)
                if status == 200:
                    ok += 1; total_ok += 1
                else:
                    err += 1; total_err += 1
                time.sleep(0.1)
            paralelos = "2 paralelos" if cantidad >= 30 else "1 paralelo"
            print(f"    ✅ {label}: {ok} estudiantes registrados ({paralelos})" +
                  (f" — ⚠️ {err} errores" if err else ""))

    print()

    # ── 3. ESTUDIANTES - HUMANÍSTICA ──────────────────────────────────────────
    print("═" * 60)
    print("  📚 REGISTRANDO ESTUDIANTES — ÁREA HUMANÍSTICA")
    print("═" * 60)
    print(f"\n  📁 Humanística (todos los cursos)")
    for curso in CURSOS_HUMANISTICA:
        nivel_api = curso["nivel_api"]
        cantidad  = curso["cantidad"]
        label     = curso["label"]
        ok = 0; err = 0
        for _ in range(cantidad):
            nombre, apellido, carnet = generar_persona(idx); idx += 1
            status, resp = registrar_usuario(token, nombre, apellido, carnet, "estudiante", nivel_api)
            if status == 200:
                ok += 1; total_ok += 1
            else:
                err += 1; total_err += 1
            time.sleep(0.1)
        paralelos = "2 paralelos" if cantidad >= 30 else "1 paralelo"
        print(f"    ✅ {label}: {ok} estudiantes registrados ({paralelos})" +
              (f" — ⚠️ {err} errores" if err else ""))

    # ── Resumen ────────────────────────────────────────────────────────────────
    print()
    print("═" * 60)
    print(f"  📊 RESUMEN FINAL")
    print("═" * 60)
    print(f"  ✅ Registros exitosos : {total_ok}")
    print(f"  ⚠️  Errores           : {total_err}")
    print(f"  📌 Total procesados   : {total_ok + total_err}")
    print()
    print("  🏁 ¡Listo! Ahora entra al Director y recarga el Directorio.")
    print("     Los paralelos se generan automáticamente según cantidad.")

if __name__ == "__main__":
    main()
