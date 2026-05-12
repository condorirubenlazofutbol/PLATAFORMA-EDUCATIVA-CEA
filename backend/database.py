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

        # 1.5 Nueva Tabla: Carreras / Especialidades / Áreas Humanísticas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS carreras (
                id SERIAL PRIMARY KEY,
                subsistema_id INT,
                nombre VARCHAR(150) NOT NULL,
                area VARCHAR(50) NOT NULL, -- 'Técnica' o 'Humanística'
                descripcion TEXT,
                jefe_id INT,
                estado VARCHAR(20) DEFAULT 'activo',
                FOREIGN KEY (subsistema_id) REFERENCES subsistemas(id) ON DELETE CASCADE
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
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subsistema_id) REFERENCES subsistemas(id) ON DELETE SET NULL
            )
        ''')
        
        # Add column if table already exists (for backwards compatibility without data loss)
        cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS curso_asignado VARCHAR(200)")
        cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS es_jefe BOOLEAN DEFAULT FALSE")

        # 2.5 Nueva Tabla: Inscripciones (Dualidad)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inscripciones (
                id SERIAL PRIMARY KEY,
                usuario_id INT NOT NULL,
                carrera_id INT NOT NULL,
                nivel VARCHAR(100), -- ej. Técnico Medio, Aprendizajes Aplicados
                paralelo VARCHAR(5) DEFAULT 'A',
                turno VARCHAR(20) DEFAULT 'Noche',
                fecha_inscripcion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                estado VARCHAR(20) DEFAULT 'activo',
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                FOREIGN KEY (carrera_id) REFERENCES carreras(id) ON DELETE CASCADE
            )
        ''')
        cursor.execute("ALTER TABLE inscripciones ADD COLUMN IF NOT EXISTS turno VARCHAR(20) DEFAULT 'Noche'")
        # Eliminar la restricción antigua si existe y crear una que incluya el turno
        cursor.execute("ALTER TABLE inscripciones DROP CONSTRAINT IF EXISTS inscripciones_usuario_id_carrera_id_key")
        cursor.execute("ALTER TABLE inscripciones ADD CONSTRAINT inscripciones_usuario_id_carrera_id_turno_key UNIQUE (usuario_id, carrera_id, turno)")
        # Reparar inscripciones con estado NULL (migración de datos)
        cursor.execute("UPDATE inscripciones SET estado = 'activo' WHERE estado IS NULL")

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS modulos (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(200) NOT NULL,
                nivel VARCHAR(100) NOT NULL,
                subnivel VARCHAR(100),
                orden INT DEFAULT 0,
                carrera_id INT,
                periodo VARCHAR(100), -- '1er Semestre', 'Gestión 2026', etc.
                docente_id INT,
                area VARCHAR(50),      -- 'Técnica' o 'Humanística'
                descripcion TEXT,
                FOREIGN KEY (carrera_id) REFERENCES carreras(id) ON DELETE SET NULL,
                FOREIGN KEY (docente_id) REFERENCES usuarios(id) ON DELETE SET NULL
            )
        ''')
        cursor.execute("ALTER TABLE modulos ADD COLUMN IF NOT EXISTS docente_id INT")
        cursor.execute("ALTER TABLE modulos ADD COLUMN IF NOT EXISTS area VARCHAR(50)")
        cursor.execute("ALTER TABLE modulos ADD COLUMN IF NOT EXISTS descripcion TEXT")
        # No podemos agregar el foreign key de docente_id tan fácilmente con if not exists en postgres sin un bloque DO, pero dejaremos el foreign key en el CREATE.

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
                nota_ser DECIMAL(5,2) DEFAULT 0,
                nota_saber DECIMAL(5,2) DEFAULT 0,
                nota_hacer DECIMAL(5,2) DEFAULT 0,
                nota_decidir DECIMAL(5,2) DEFAULT 0,
                nota_autoevaluacion DECIMAL(5,2) DEFAULT 0,
                nota_final DECIMAL(5,2) DEFAULT 0,
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
            CREATE TABLE IF NOT EXISTS candidatos (
                id SERIAL PRIMARY KEY,
                eleccion_id INT NOT NULL,
                nombre VARCHAR(150) NOT NULL,
                sigla VARCHAR(50),
                cargo VARCHAR(100),
                frente VARCHAR(150),
                descripcion TEXT,
                foto TEXT,
                imagen_base64 TEXT,
                FOREIGN KEY (eleccion_id) REFERENCES elecciones(id) ON DELETE CASCADE
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
                FOREIGN KEY (candidato_id) REFERENCES candidatos(id) ON DELETE CASCADE,
                UNIQUE (eleccion_id, estudiante_id)
            )
        ''')

        # 7. Temas por módulo (4 temas fijos con subtítulos)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS temas (
                id SERIAL PRIMARY KEY,
                modulo_id INT NOT NULL,
                numero INT NOT NULL,
                titulo VARCHAR(250) NOT NULL,
                subtitulos JSONB DEFAULT '[]',
                FOREIGN KEY (modulo_id) REFERENCES modulos(id) ON DELETE CASCADE,
                UNIQUE(modulo_id, numero)
            )
        ''')

        # 8. Planes didácticos generados por IA
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS planes_didacticos (
                id SERIAL PRIMARY KEY,
                docente_id INT NOT NULL,
                carrera_id INT,
                modulo_id INT,
                tema_id INT,
                tipo VARCHAR(50) NOT NULL,
                titulo VARCHAR(300),
                contenido_ia TEXT NOT NULL,
                fecha_generacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (docente_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                FOREIGN KEY (carrera_id) REFERENCES carreras(id) ON DELETE SET NULL,
                FOREIGN KEY (modulo_id) REFERENCES modulos(id) ON DELETE SET NULL,
                FOREIGN KEY (tema_id) REFERENCES temas(id) ON DELETE SET NULL
            )
        ''')

        # 9. Log de importaciones de malla desde Excel
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS malla_imports (
                id SERIAL PRIMARY KEY,
                usuario_id INT NOT NULL,
                carrera_id INT NOT NULL,
                archivo_nombre VARCHAR(200),
                modulos_importados INT DEFAULT 0,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                FOREIGN KEY (carrera_id) REFERENCES carreras(id) ON DELETE CASCADE
            )
        ''')

        # 10. Plantillas de certificados/constancias (creadas por el director)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plantillas_certificado (
                id SERIAL PRIMARY KEY,
                titulo VARCHAR(300) NOT NULL,
                nivel VARCHAR(200),
                carrera_id INT,
                area VARCHAR(50),
                cuerpo_texto TEXT NOT NULL,
                pie_texto TEXT DEFAULT '',
                activa BOOLEAN DEFAULT TRUE,
                creado_por INT NOT NULL,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (creado_por) REFERENCES usuarios(id) ON DELETE CASCADE,
                FOREIGN KEY (carrera_id) REFERENCES carreras(id) ON DELETE SET NULL
            )
        ''')

        # 11. Constancias generadas por estudiantes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS constancias (
                id SERIAL PRIMARY KEY,
                estudiante_id INT NOT NULL,
                plantilla_id INT NOT NULL,
                codigo VARCHAR(60) UNIQUE NOT NULL,
                fecha_generacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                datos_snapshot JSONB DEFAULT '{}',
                FOREIGN KEY (estudiante_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                FOREIGN KEY (plantilla_id) REFERENCES plantillas_certificado(id) ON DELETE CASCADE
            )
        ''')

        # 12. Asistencia por sesión
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS asistencia (
                id SERIAL PRIMARY KEY,
                modulo_id INT NOT NULL,
                docente_id INT NOT NULL,
                estudiante_id INT NOT NULL,
                fecha DATE NOT NULL,
                estado VARCHAR(20) DEFAULT 'presente',
                observacion TEXT DEFAULT '',
                FOREIGN KEY (modulo_id) REFERENCES modulos(id) ON DELETE CASCADE,
                FOREIGN KEY (docente_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                FOREIGN KEY (estudiante_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                UNIQUE(modulo_id, estudiante_id, fecha)
            )
        ''')

        # 13. Horarios semanales
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS horarios (
                id SERIAL PRIMARY KEY,
                carrera_id INT,
                nivel VARCHAR(200),
                dia VARCHAR(20) NOT NULL,
                hora_inicio TIME NOT NULL,
                hora_fin TIME NOT NULL,
                modulo_id INT,
                docente_id INT,
                aula VARCHAR(100) DEFAULT '',
                FOREIGN KEY (carrera_id) REFERENCES carreras(id) ON DELETE CASCADE,
                FOREIGN KEY (modulo_id) REFERENCES modulos(id) ON DELETE SET NULL,
                FOREIGN KEY (docente_id) REFERENCES usuarios(id) ON DELETE SET NULL
            )
        ''')

        # 14. Recursos/Biblioteca digital
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recursos (
                id SERIAL PRIMARY KEY,
                modulo_id INT,
                tema_id INT,
                titulo VARCHAR(300) NOT NULL,
                tipo VARCHAR(50) DEFAULT 'enlace',
                url TEXT NOT NULL,
                descripcion TEXT DEFAULT '',
                subido_por INT NOT NULL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (modulo_id) REFERENCES modulos(id) ON DELETE CASCADE,
                FOREIGN KEY (tema_id) REFERENCES temas(id) ON DELETE SET NULL,
                FOREIGN KEY (subido_por) REFERENCES usuarios(id) ON DELETE CASCADE
            )
        ''')

        # 15. Evaluaciones online
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS evaluaciones (
                id SERIAL PRIMARY KEY,
                modulo_id INT,
                docente_id INT NOT NULL,
                titulo VARCHAR(300) NOT NULL,
                descripcion TEXT DEFAULT '',
                tiempo_minutos INT DEFAULT 60,
                intentos_max INT DEFAULT 1,
                activa BOOLEAN DEFAULT FALSE,
                fecha_inicio TIMESTAMP,
                fecha_fin TIMESTAMP,
                FOREIGN KEY (modulo_id) REFERENCES modulos(id) ON DELETE CASCADE,
                FOREIGN KEY (docente_id) REFERENCES usuarios(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS preguntas (
                id SERIAL PRIMARY KEY,
                evaluacion_id INT NOT NULL,
                texto TEXT NOT NULL,
                tipo VARCHAR(30) DEFAULT 'multiple',
                puntos INT DEFAULT 1,
                orden INT DEFAULT 0,
                FOREIGN KEY (evaluacion_id) REFERENCES evaluaciones(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS opciones_pregunta (
                id SERIAL PRIMARY KEY,
                pregunta_id INT NOT NULL,
                texto TEXT NOT NULL,
                es_correcta BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (pregunta_id) REFERENCES preguntas(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS respuestas_alumno (
                id SERIAL PRIMARY KEY,
                evaluacion_id INT NOT NULL,
                estudiante_id INT NOT NULL,
                pregunta_id INT NOT NULL,
                opcion_id INT,
                respuesta_texto TEXT DEFAULT '',
                es_correcta BOOLEAN,
                puntos_obtenidos DECIMAL(5,2) DEFAULT 0,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (evaluacion_id) REFERENCES evaluaciones(id) ON DELETE CASCADE,
                FOREIGN KEY (estudiante_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                FOREIGN KEY (pregunta_id) REFERENCES preguntas(id) ON DELETE CASCADE,
                UNIQUE(evaluacion_id, estudiante_id, pregunta_id)
            )
        ''')

        for col_sql in [
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS subsistema_id INT",
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS nivel_asignado VARCHAR(100)",
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS carnet VARCHAR(50)",
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS estado VARCHAR(20) DEFAULT 'activo'",
            "ALTER TABLE modulos ADD COLUMN IF NOT EXISTS orden INT DEFAULT 0",
            "ALTER TABLE modulos ADD COLUMN IF NOT EXISTS carrera_id INT",
            "ALTER TABLE modulos ADD COLUMN IF NOT EXISTS periodo VARCHAR(100)",
            "ALTER TABLE modulos ADD COLUMN IF NOT EXISTS descripcion TEXT",
            "ALTER TABLE modulos ADD COLUMN IF NOT EXISTS area VARCHAR(20)",
            "ALTER TABLE contenidos ADD COLUMN IF NOT EXISTS tema_num INT DEFAULT 1",
            "ALTER TABLE contenidos ALTER COLUMN url SET DEFAULT ''",
            "ALTER TABLE progreso ADD COLUMN IF NOT EXISTS nota_ser DECIMAL(5,2) DEFAULT 0",
            "ALTER TABLE progreso ADD COLUMN IF NOT EXISTS nota_saber DECIMAL(5,2) DEFAULT 0",
            "ALTER TABLE progreso ADD COLUMN IF NOT EXISTS nota_hacer DECIMAL(5,2) DEFAULT 0",
            "ALTER TABLE progreso ADD COLUMN IF NOT EXISTS nota_decidir DECIMAL(5,2) DEFAULT 0",
            "ALTER TABLE progreso ADD COLUMN IF NOT EXISTS nota_autoevaluacion DECIMAL(5,2) DEFAULT 0",
            "ALTER TABLE progreso ADD COLUMN IF NOT EXISTS nota_final DECIMAL(5,2) DEFAULT 0",
            # Columnas nuevas de candidatos
            "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS sigla VARCHAR(50)",
            "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS cargo VARCHAR(100)",
            "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS frente VARCHAR(150)",
            "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS descripcion TEXT",
            "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS imagen_base64 TEXT",
            # Modificar la FK de candidato_id en votos para apuntar a candidatos
            "ALTER TABLE votos DROP CONSTRAINT IF EXISTS votos_candidato_id_fkey",
            "ALTER TABLE votos ADD CONSTRAINT votos_candidato_id_fkey FOREIGN KEY (candidato_id) REFERENCES candidatos(id) ON DELETE CASCADE"
        ]:

            try:
                cursor.execute(col_sql)
            except:
                connection.rollback()
                
        # Asegurar que existe el subsistema 1
        try:
            cursor.execute("INSERT INTO subsistemas (id, nombre, descripcion) VALUES (1, 'CEA Central', 'Subsistema principal') ON CONFLICT (id) DO NOTHING")
        except:
            connection.rollback()
            try:
                # If ON CONFLICT fails because no constraint on id (should have PRIMARY KEY though), try this:
                cursor.execute("INSERT INTO subsistemas (id, nombre, descripcion) SELECT 1, 'CEA Central', 'Subsistema principal' WHERE NOT EXISTS (SELECT 1 FROM subsistemas WHERE id = 1)")
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
