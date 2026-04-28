import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def seed_data():
    try:
        db_url = os.getenv("DATABASE_URL")
        connection = psycopg2.connect(db_url) if db_url else psycopg2.connect(
            host=os.getenv("DB_HOST","localhost"), user=os.getenv("DB_USER","postgres"),
            password=os.getenv("DB_PASSWORD","root"), dbname=os.getenv("DB_NAME","educonnect_ruben")
        )
        cursor = connection.cursor()

        cursor.execute("DELETE FROM contenidos")
        cursor.execute("DELETE FROM modulos")
        
        MALLA = [
            # NIVEL BÁSICO
            ("Básico", "1er SEMESTRE – BÁSICO", [
                ("Introducción a la Informática", ["Qué es informática", "Hardware y software", "Dispositivos de entrada y salida", "Uso básico del computador"]),
                ("Pensamiento Computacional", ["Qué es pensamiento computacional", "Resolución de problemas", "Abstracción", "Descomposición"]),
                ("Lógica de Programación I", ["Secuencias", "Algoritmos cotidianos", "Introducción a variables", "Representación de soluciones"]),
                ("Algoritmos I", ["Qué es un algoritmo", "Pseudocódigo", "Diagramas de flujo", "Ejercicios básicos"]),
                ("Módulo Emergente I (IA básica)", ["Qué es la IA", "Uso incorrecto de la IA", "Limitaciones", "Uso responsable"])
            ]),
            # NIVEL AUXILIAR (SEPARADO)
            ("Auxiliar", "2do SEMESTRE – AUXILIAR", [
                ("Lógica de Programación II", ["Variables y tipos de datos", "Operadores", "Expresiones lógicas", "Evaluación"]),
                ("Estructuras de Control", ["Condicionales", "Bucles", "Control de flujo", "Casos prácticos"]),
                ("Funciones", ["Definición", "Parámetros", "Retorno", "Modularidad"]),
                ("Bases de Datos Básicas", ["Qué es una base de datos", "Tablas", "Registros", "Relaciones"]),
                ("Módulo Emergente II (Prompts básicos)", ["Qué es un prompt", "Tipos de prompts", "Errores comunes", "Buenas prácticas"])
            ]),
            # NIVEL MEDIO
            ("Medio", "3er SEMESTRE – MEDIO I", [
                ("Programación con Python", ["Sintaxis básica", "Entrada y salida", "Condicionales y bucles", "Funciones"]),
                ("Estructuras de Datos", ["Listas", "Diccionarios", "Manipulación de datos", "Aplicaciones"]),
                ("Bases de Datos I", ["Introducción a SQL", "CRUD", "Consultas", "Filtros"]),
                ("Sistemas Operativos y Redes", ["Archivos", "Procesos", "Terminal", "Redes básicas"]),
                ("Módulo Emergente III (Prompt estructurado)", ["Prompt estructurado", "Componentes", "Uso en programación", "Mejora de resultados"])
            ]),
            ("Medio", "4to SEMESTRE – MEDIO II", [
                ("Frontend", ["JavaScript", "DOM", "Eventos", "Formularios"]),
                ("Backend Básico", ["Servidor", "Rutas", "APIs", "Testing básico"]),
                ("Base de Datos II", ["Relaciones", "Normalización", "Integración", "Consultas complejas"]),
                ("Control de Versiones", ["Git", "Repositorios", "Ramas", "Trabajo en equipo"]),
                ("Módulo Emergente IV (Contexto IA)", ["Contexto", "Control de salida", "Iteración", "Refinamiento"])
            ]),
            # NIVEL SUPERIOR
            ("Superior", "5to SEMESTRE – SUPERIOR I", [
                ("Frontend Avanzado", ["React", "Componentes", "Estado", "Consumo de APIs"]),
                ("Backend Avanzado", ["APIs REST", "Validaciones", "Autenticación (JWT)", "Seguridad básica"]),
                ("Arquitectura de Software", ["Capas", "MVC", "Separación de responsabilidades", "Diseño modular"]),
                ("Seguridad Informática", ["Validación de datos", "Autenticación", "SQL Injection", "Protección básica"]),
                ("Módulo Emergente V (SDD)", ["Qué es SDD", "Diferencias con desarrollo tradicional", "Ventajas", "Casos de uso"])
            ]),
            ("Superior", "6to SEMESTRE – SUPERIOR II", [
                ("DevOps Básico", ["CI/CD", "Automatización", "Entornos", "Integración continua"]),
                ("Testing de Software", ["Unit testing", "Integration testing", "Pruebas funcionales", "Automatización"]),
                ("Despliegue", ["Deploy", "Plataformas", "Variables de entorno", "Logs"]),
                ("Gestión de Proyectos", ["Scrum", "Tareas", "Priorización", "Trabajo en equipo"]),
                ("Módulo Emergente VI (Flujo con IA)", ["Idea del sistema", "Especificación", "Generación de código", "Iteración"])
            ]),
            # NIVEL INGENIERÍA
            ("Ingeniería", "7mo SEMESTRE – INGENIERÍA I", [
                ("Estructuras de Datos Avanzadas", ["Árboles", "Grafos", "Recorridos", "Aplicaciones"]),
                ("Algoritmos", ["Ordenamiento", "Búsqueda", "Recursividad", "Optimización"]),
                ("Complejidad Computacional", ["Big O", "Análisis de algoritmos", "Costos", "Comparación"]),
                ("Bases de Datos Avanzadas", ["Índices", "Optimización", "Consultas complejas", "Rendimiento"]),
                ("Módulo Emergente VII (Validación IA)", ["Validación de código", "Errores IA", "Seguridad", "Buenas prácticas"])
            ]),
            ("Ingeniería", "8vo SEMESTRE – INGENIERÍA II", [
                ("Arquitectura Avanzada", ["Microservicios", "Sistemas distribuidos", "Escalabilidad", "Diseño avanzado"]),
                ("Cloud Computing", ["AWS/Azure", "Servicios cloud", "Escalabilidad", "Costos"]),
                ("Infraestructura", ["Docker", "Contenedores", "Orquestación", "Implementación"]),
                ("Seguridad Avanzada", ["OAuth", "Protección APIs", "Seguridad web", "Auditoría"]),
                ("Módulo Emergente VIII (Automatización IA)", ["Automatización", "Scripts", "Flujos", "Integración"])
            ]),
            ("Ingeniería", "9no SEMESTRE – INGENIERÍA III", [
                ("IA en Desarrollo", ["Uso de IA", "Limitaciones", "Casos reales", "Integración"]),
                ("Spec-Driven Development (SDD)", ["Especificaciones", "Flujo", "Validación", "Aplicación"]),
                ("Ingeniería de Prompts", ["Tipos de prompts", "Estructura", "Optimización", "Casos prácticos"]),
                ("Automatización Avanzada", ["Scripts", "Procesos", "Integración", "Optimización"]),
                ("Módulo Emergente IX (Ética IA)", ["Ética", "Responsabilidad", "Riesgos", "Buenas prácticas"])
            ]),
            ("Ingeniería", "10mo SEMESTRE – INGENIERÍA IV", [
                ("Proyecto de Grado", ["Desarrollo del sistema", "Integración", "Validación", "Presentación"]),
                ("Documentación Técnica", ["Manual técnico", "Manual de usuario", "Documentación", "Estándares"]),
                ("Emprendimiento Tecnológico", ["Modelo de negocio", "Producto digital", "Mercado", "Estrategia"]),
                ("Inserción Laboral", ["Portafolio", "CV", "Entrevistas", "Marca personal"]),
                ("Módulo Emergente X (IA aplicada)", ["Uso profesional", "Integración IA", "Optimización", "Proyecto con IA"])
            ])
        ]

        orden = 1
        for nivel, semestre, modulos in MALLA:
            for mod_nombre, temas in modulos:
                cursor.execute(
                    "INSERT INTO modulos (nombre, nivel, subnivel, orden) VALUES (%s, %s, %s, %s) RETURNING id",
                    (mod_nombre, nivel, semestre, orden)
                )
                m_id = cursor.fetchone()[0]
                orden += 1
                for i, tema_nombre in enumerate(temas):
                    cursor.execute(
                        "INSERT INTO contenidos (modulo_id, tipo, titulo, url, tema_num) VALUES (%s, 'teoria', %s, '', %s)",
                        (m_id, tema_nombre, i + 1)
                    )
        
        connection.commit()
        print("Malla Auxiliar separada con éxito.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'connection' in locals() and connection:
            cursor.close(); connection.close()

if __name__ == "__main__":
    seed_data()
