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
        
        # Eliminar las carreras de nivel superior o ingeniería que no pertenezcan al CEA
        carreras_oficiales = [
            'Sistemas Informáticos', 'Veterinaria', 'Educación Parvularia', 
            'Fisioterapia', 'Contabilidad General', 'Corte y Confección', 
            'Belleza Integral', 'Gastronomía', 'Matemática', 'Lenguaje', 
            'Ciencias Naturales', 'Ciencias Sociales'
        ]
        
        format_strings = ','.join(['%s'] * len(carreras_oficiales))
        cur.execute(f"SELECT id FROM carreras WHERE nombre NOT IN ({format_strings})", tuple(carreras_oficiales))
        carreras_a_borrar = cur.fetchall()
        
        if carreras_a_borrar:
            carrera_ids = tuple(c[0] for c in carreras_a_borrar)
            print(f"Borrando {len(carrera_ids)} carreras universitarias y sus módulos...")
            
            cur.execute(f"SELECT id FROM modulos WHERE carrera_id IN %s", (carrera_ids,))
            modulos_a_borrar = cur.fetchall()
            
            if modulos_a_borrar:
                modulo_ids = tuple(m[0] for m in modulos_a_borrar)
                cur.execute(f"DELETE FROM temas WHERE modulo_id IN %s", (modulo_ids,))
                cur.execute(f"DELETE FROM modulos WHERE carrera_id IN %s", (carrera_ids,))
            
            cur.execute(f"DELETE FROM carreras WHERE id IN %s", (carrera_ids,))
        
        # Borrar módulos universitarios que estén colados
        cur.execute("DELETE FROM temas WHERE modulo_id IN (SELECT id FROM modulos WHERE nombre LIKE '%Cloud Computing%' OR nombre LIKE '%Algoritmos%' OR nombre LIKE '%Módulo Emergente%' OR nombre LIKE '%Base de Datos%')")
        cur.execute("DELETE FROM modulos WHERE nombre LIKE '%Cloud Computing%' OR nombre LIKE '%Algoritmos%' OR nombre LIKE '%Módulo Emergente%' OR nombre LIKE '%Base de Datos%'")
        
        conn.commit()
        print("Limpieza completada. Ahora re-sembrando datos oficiales del CEA...")
        
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
