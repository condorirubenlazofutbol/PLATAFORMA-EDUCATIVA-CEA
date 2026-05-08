import os
import psycopg2
from dotenv import load_dotenv
import security as auth

load_dotenv()

from database import get_db_connection

def seed_users():
    """Crea el administrador y usuarios de prueba si no existen."""
    print("Iniciando creación de usuarios...")
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()


        # 1. Administrador
        admin_pass = auth.get_password_hash("1234567")
        cursor.execute("""
            INSERT INTO usuarios (nombre, apellido, email, password, rol) 
            VALUES (%s, %s, %s, %s, %s) 
            ON CONFLICT (email) DO UPDATE SET password = EXCLUDED.password, rol = EXCLUDED.rol
        """, ("Ruben", "Admin", "ruben.admin@educonnect.com", admin_pass, "administrador"))

        # 2. Profesor
        profe_pass = auth.get_password_hash("1234567")
        cursor.execute("""
            INSERT INTO usuarios (nombre, apellido, email, password, rol) 
            VALUES (%s, %s, %s, %s, %s) 
            ON CONFLICT (email) DO UPDATE SET password = EXCLUDED.password, rol = EXCLUDED.rol
        """, ("Ruben", "Profesor", "ruben.profe@educonnect.com", profe_pass, "docente"))

        # 3. Estudiante
        estu_pass = auth.get_password_hash("1234567")
        cursor.execute("""
            INSERT INTO usuarios (nombre, apellido, email, password, rol) 
            VALUES (%s, %s, %s, %s, %s) 
            ON CONFLICT (email) DO UPDATE SET password = EXCLUDED.password, rol = EXCLUDED.rol
        """, ("Ruben", "Estudiante", "ruben.estudiante@educonnect.com", estu_pass, "estudiante"))

        # 4. Secretaria
        sec_pass = auth.get_password_hash("1234567")
        cursor.execute("""
            INSERT INTO usuarios (nombre, apellido, email, password, rol) 
            VALUES (%s, %s, %s, %s, %s) 
            ON CONFLICT (email) DO UPDATE SET password = EXCLUDED.password, rol = EXCLUDED.rol
        """, ("Ruben", "Secretaria", "ruben.secretaria@educonnect.com", sec_pass, "secretaria"))

        # 5. Director
        dir_pass = auth.get_password_hash("1234567")
        cursor.execute("""
            INSERT INTO usuarios (nombre, apellido, email, password, rol) 
            VALUES (%s, %s, %s, %s, %s) 
            ON CONFLICT (email) DO UPDATE SET password = EXCLUDED.password, rol = EXCLUDED.rol
        """, ("Ruben", "Director", "ruben.director@educonnect.com", dir_pass, "director"))




        connection.commit()
        print("¡Usuarios creados/actualizados exitosamente!")
        return True
        
    except Exception as e:
        print(f"Error al insertar usuarios: {e}")
        if connection:
            connection.rollback()
        raise e # Raise to see details in /cargar-datos
    finally:

        if connection:
            cursor.close()
            connection.close()

if __name__ == "__main__":
    seed_users()

