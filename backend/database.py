import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Establece conexión con PostgreSQL usando DATABASE_URL, INTERNAL_DATABASE_URL o credenciales locales."""
    try:
        # Intentar primero con la URL de producción (Render)
        db_url = os.getenv("INTERNAL_DATABASE_URL") or os.getenv("DATABASE_URL")
        
        if db_url:
            # Render/Producción
            conn = psycopg2.connect(db_url)
            return conn
            
        # Si no hay URL, estamos en local o falta configuración
        is_render = os.getenv("RENDER") == "true"
        if is_render:
            raise Exception("DATABASE_URL no encontrada en el entorno de Render. Verifica tus Variables de Entorno.")

        # Local/Desarrollo
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "root"),
            dbname=os.getenv("DB_NAME", "educonnect_ruben")
        )
        return conn
    except Exception as e:
        print(f"CRITICAL ERROR: No se pudo conectar a la base de datos: {e}")
        raise e
 # Raise to see details in /cargar-datos



def init_db():
    connection = get_db_connection()
    if not connection:
        print("Could not connect to initialize tables")
        return
    try:
        cursor = connection.cursor()

        # 1. Tabla de Subsistemas (Sedes, Carreras o Colegios)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subsistemas (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(150) UNIQUE NOT NULL,
                descripcion TEXT,
                estado VARCHAR(20) DEFAULT 'activo'
            )
        ''')

        # 2. Tabla de Usuarios (con subsistema_id)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                subsistema_id INT,
                nombre VARCHAR(100) NOT NULL,
                apellido VARCHAR(100) NOT NULL,
                email VARCHAR(150) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                rol VARCHAR(20) NOT NULL DEFAULT 'estudiante', -- director, jefe_carrera, secretaria, docente, estudiante
                nivel_asignado VARCHAR(100),
                carnet VARCHAR(50),
                estado VARCHAR(20) DEFAULT 'activo',
                FOREIGN KEY (subsistema_id) REFERENCES subsistemas(id) ON DELETE SET NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS modulos (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(200) NOT NULL,
                nivel VARCHAR(100) NOT NULL,
                subnivel VARCHAR(100),
                orden INT DEFAULT 0
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contenidos (
                id SERIAL PRIMARY KEY,
                modulo_id INT NOT NULL,
                tipo VARCHAR(50) NOT NULL,
                titulo VARCHAR(200) NOT NULL,
                url TEXT NOT NULL DEFAULT '',
                tema_num INT DEFAULT 1,
                FOREIGN KEY (modulo_id) REFERENCES modulos(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS evaluaciones (
                id SERIAL PRIMARY KEY,
                modulo_id INT NOT NULL,
                pregunta TEXT NOT NULL,
                opciones JSONB NOT NULL,
                respuesta_correcta VARCHAR(200) NOT NULL,
                FOREIGN KEY (modulo_id) REFERENCES modulos(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS progreso (
                id SERIAL PRIMARY KEY,
                usuario_id INT NOT NULL,
                modulo_id INT NOT NULL,
                estado VARCHAR(50) DEFAULT 'inscrito',
                nota DECIMAL(5,2),
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                FOREIGN KEY (modulo_id) REFERENCES modulos(id) ON DELETE CASCADE,
                UNIQUE (usuario_id, modulo_id)
            )
        ''')

        # 3. Nuevas tablas Pro: Avisos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS avisos_institucionales (
                id SERIAL PRIMARY KEY,
                subsistema_id INT,
                autor_id INT NOT NULL,
                titulo VARCHAR(200) NOT NULL,
                contenido TEXT NOT NULL,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subsistema_id) REFERENCES subsistemas(id) ON DELETE CASCADE,
                FOREIGN KEY (autor_id) REFERENCES usuarios(id) ON DELETE CASCADE
            )
        ''')

        # 4. Nuevas tablas Pro: Planificaciones (Registro Pedagógico)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS planificaciones (
                id SERIAL PRIMARY KEY,
                docente_id INT NOT NULL,
                modulo_id INT NOT NULL,
                contenido_ia TEXT NOT NULL,
                fecha_generacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (docente_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                FOREIGN KEY (modulo_id) REFERENCES modulos(id) ON DELETE CASCADE
            )
        ''')

        # 5. Nuevas tablas Pro: Certificados
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS certificados (
                id SERIAL PRIMARY KEY,
                estudiante_id INT NOT NULL,
                modulo_id INT NOT NULL,
                codigo_qr VARCHAR(255) UNIQUE NOT NULL,
                fecha_emision TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (estudiante_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                FOREIGN KEY (modulo_id) REFERENCES modulos(id) ON DELETE CASCADE
            )
        ''')

        # 6. Nuevas tablas Pro: Elecciones y Votos (Votación)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS elecciones (
                id SERIAL PRIMARY KEY,
                subsistema_id INT,
                titulo VARCHAR(200) NOT NULL,
                descripcion TEXT,
                fecha_inicio TIMESTAMP NOT NULL,
                fecha_fin TIMESTAMP NOT NULL,
                estado VARCHAR(20) DEFAULT 'activa',
                FOREIGN KEY (subsistema_id) REFERENCES subsistemas(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS votos (
                id SERIAL PRIMARY KEY,
                eleccion_id INT NOT NULL,
                estudiante_id INT NOT NULL,
                candidato_id INT NOT NULL,
                fecha_voto TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (eleccion_id) REFERENCES elecciones(id) ON DELETE CASCADE,
                FOREIGN KEY (estudiante_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                FOREIGN KEY (candidato_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                UNIQUE (eleccion_id, estudiante_id)
            )
        ''')

        # Add columns if they dont exist yet (safe migrations for existing users)
        for col_sql in [
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS subsistema_id INT",
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS nivel_asignado VARCHAR(100)",
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS carnet VARCHAR(50)",
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS estado VARCHAR(20) DEFAULT 'activo'",
            "ALTER TABLE modulos ADD COLUMN IF NOT EXISTS orden INT DEFAULT 0",
            "ALTER TABLE contenidos ADD COLUMN IF NOT EXISTS tema_num INT DEFAULT 1",
            "ALTER TABLE contenidos ALTER COLUMN url SET DEFAULT ''",
        ]:
            try:
                cursor.execute(col_sql)
            except:
                connection.rollback()

        connection.commit()
        print("Tablas PostgreSQL creadas/verificadas correctamente.")
    except Exception as e:
        print(f"Init DB error: {e}")
    finally:
        cursor.close(); connection.close()

if __name__ == "__main__":
    init_db()
