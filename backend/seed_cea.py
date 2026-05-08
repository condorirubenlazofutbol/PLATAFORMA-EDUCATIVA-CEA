import os
from database import get_db_connection

CARRERAS_TECNICAS = [
    "Sistemas Informáticos",
    "Veterinaria",
    "Educación Parvularia",
    "Fisioterapia",
    "Contabilidad General",
    "Corte y Confección",
    "Belleza Integral",
    "Gastronomía"
]
NIVELES_TECNICOS = ["Nivel Básico", "Nivel Auxiliar", "Nivel Medio I", "Nivel Medio II"]

MATERIAS_HUMANISTICAS = [
    "Matemática",
    "Lenguaje",
    "Ciencias Naturales",
    "Ciencias Sociales"
]
NIVELES_HUMANISTICOS = ["Aplicados (Primer Año)", "Complementarios (Segundo Año)", "Especializados (Tercer Año)"]

def seed_cea_data():
    """Genera las carreras, materias y sus módulos en la base de datos según la estructura oficial."""
    conn = get_db_connection()
    if not conn:
        print("Error: No database connection")
        return 0
    
    try:
        cur = conn.cursor()
        
        # Ensure subsistema 1 exists
        try:
            cur.execute("INSERT INTO subsistemas (id, nombre, descripcion) VALUES (1, 'CEA Central', 'Subsistema principal') ON CONFLICT (id) DO NOTHING")
        except:
            conn.rollback()
            cur.execute("INSERT INTO subsistemas (id, nombre, descripcion) SELECT 1, 'CEA Central', 'Subsistema principal' WHERE NOT EXISTS (SELECT 1 FROM subsistemas WHERE id = 1)")
        
        modulos_creados = 0
        
        # 1. Seed Técnicas
        for nombre_carrera in CARRERAS_TECNICAS:
            cur.execute("SELECT id FROM carreras WHERE nombre = %s AND area = 'Técnica'", (nombre_carrera,))
            row = cur.fetchone()
            if not row:
                cur.execute("INSERT INTO carreras (subsistema_id, nombre, area) VALUES (1, %s, 'Técnica') RETURNING id", (nombre_carrera,))
                c_id = cur.fetchone()[0]
            else:
                c_id = row[0]
                
            # Create modules
            for nivel in NIVELES_TECNICOS:
                for i in range(1, 6):
                    mod_name = f"Módulo {i}"
                    cur.execute("SELECT id FROM modulos WHERE carrera_id = %s AND nivel = %s AND nombre = %s", (c_id, nivel, mod_name))
                    if not cur.fetchone():
                        cur.execute("INSERT INTO modulos (nombre, nivel, carrera_id, orden) VALUES (%s, %s, %s, %s)", (mod_name, nivel, c_id, i))
                        modulos_creados += 1
                        
        # 2. Seed Humanísticas
        for materia in MATERIAS_HUMANISTICAS:
            cur.execute("SELECT id FROM carreras WHERE nombre = %s AND area = 'Humanística'", (materia,))
            row = cur.fetchone()
            if not row:
                cur.execute("INSERT INTO carreras (subsistema_id, nombre, area) VALUES (1, %s, 'Humanística') RETURNING id", (materia,))
                c_id = cur.fetchone()[0]
            else:
                c_id = row[0]
                
            for nivel in NIVELES_HUMANISTICOS:
                for i in range(1, 3):
                    mod_name = f"Módulo {i}"
                    cur.execute("SELECT id FROM modulos WHERE carrera_id = %s AND nivel = %s AND nombre = %s", (c_id, nivel, mod_name))
                    if not cur.fetchone():
                        cur.execute("INSERT INTO modulos (nombre, nivel, carrera_id, orden) VALUES (%s, %s, %s, %s)", (mod_name, nivel, c_id, i))
                        modulos_creados += 1

        conn.commit()
        print(f"CEA Seed completado. {modulos_creados} módulos nuevos generados.")
        return modulos_creados
    except Exception as e:
        conn.rollback()
        print(f"Error en CEA seed: {e}")
        return 0
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    seed_cea_data()
