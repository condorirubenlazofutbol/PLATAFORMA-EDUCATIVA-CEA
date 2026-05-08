# Script de Limpieza Crítica - CEA Prof. Herman Ortiz Camargo
from database import get_db_connection
from seed_cea import seed_cea_data
import sys

def purge_and_seed():
    print("🚀 Iniciando purga total de módulos no institucionales...")
    conn = get_db_connection()
    if not conn:
        print("❌ Error: No se pudo conectar a la base de datos.")
        return

    try:
        cur = conn.cursor()
        
        # 1. Limpiar dependencias de mayor a menor
        print("🧹 Borrando inscripciones y temas...")
        cur.execute("DELETE FROM inscripciones")
        cur.execute("DELETE FROM temas")
        
        print("🧹 Borrando módulos y carreras...")
        cur.execute("DELETE FROM modulos")
        cur.execute("DELETE FROM carreras")
        
        print("🧹 Limpiando subsistemas residuales...")
        cur.execute("DELETE FROM subsistemas WHERE id != 1")
        
        # 2. Resetear secuencias para limpieza estética de IDs
        try:
            cur.execute("ALTER SEQUENCE carreras_id_seq RESTART WITH 1")
            cur.execute("ALTER SEQUENCE modulos_id_seq RESTART WITH 1")
            cur.execute("ALTER SEQUENCE inscripciones_id_seq RESTART WITH 1")
        except:
            pass

        conn.commit()
        print("✅ Base de datos purgada. Iniciando re-siembra institucional...")
        
        # 3. Sembrar datos oficiales del CEA
        creados = seed_cea_data()
        
        print(f"✨ ¡ÉXITO! Se han generado {creados} módulos oficiales.")
        print("📉 Los módulos de 'Ingeniería' y 'Nivel Superior' han sido eliminados permanentemente.")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ ERROR CRÍTICO: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    purge_and_seed()
