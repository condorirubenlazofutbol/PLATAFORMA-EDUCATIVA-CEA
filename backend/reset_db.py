import os
import sys
from database import get_db_connection
from seed_cea import seed_cea_data

def clean_and_seed():
    print("Iniciando limpieza profunda de la base de datos...")
    conn = get_db_connection()
    if not conn:
        print("Error de conexión a la BD.")
        return

    try:
        cur = conn.cursor()
        
        # 1. Limpieza agresiva de dependencias
        print("🧹 Borrando inscripciones y temas...")
        cur.execute("DELETE FROM inscripciones")
        cur.execute("DELETE FROM temas")
        
        print("🧹 Borrando módulos y carreras...")
        cur.execute("DELETE FROM modulos")
        cur.execute("DELETE FROM carreras")
        
        print("🧹 Limpiando subsistemas residuales...")
        cur.execute("DELETE FROM subsistemas WHERE id != 1")
        
        # 2. Resetear secuencias
        try:
            cur.execute("ALTER SEQUENCE carreras_id_seq RESTART WITH 1")
            cur.execute("ALTER SEQUENCE modulos_id_seq RESTART WITH 1")
        except: pass

        conn.commit()
        print("✅ Base de datos purgada. Iniciando re-siembra institucional...")
        
        # 3. Sembrar datos oficiales del CEA
        seed_cea_data()
        
        print("¡Operación completada con éxito! La plataforma ahora es 100% CEA Nivel Pro.")
    except Exception as e:
        conn.rollback()
        print(f"Error durante la limpieza: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    clean_and_seed()
