# EduConnect Pro Ecosystem v21.0 🚀

Plataforma educativa integral, modular y escalable diseñada para la gestión académica moderna. Implementada con una arquitectura desacoplada (FastAPI + Vanilla JS) y lista para despliegue inmediato en la nube.

## 🏗️ Arquitectura del Sistema

El ecosistema se divide en 9 subsistemas inteligentes que comparten una base de datos centralizada y autenticación segura basada en JWT:

1.  **Portal Central:** Dashboard inteligente con filtrado dinámico de aplicaciones según el rol del usuario.
2.  **Notas y Certificados:** Registro de calificaciones y emisión de diplomas digitales en PDF con códigos de validación.
3.  **Aula Virtual:** Gestión de materiales de estudio (PDF, Video, Tareas) y seguimiento de progreso.
4.  **Malla Curricular:** Visualización interactiva del programa de estudios organizado por niveles y semestres.
5.  **Sistema de Votaciones:** Módulo de elecciones democráticas con votación anónima y segura.
6.  **Planes IA (Docentes):** Generador de planificaciones pedagógicas basado en Inteligencia Artificial.
7.  **Comunicados:** Tablón de avisos institucionales con roles de publicación jerárquicos.
8.  **Panel de Secretaría:** Gestión administrativa de usuarios, inscripciones y procesos institucionales.
9.  **Panel de Dirección / Jefatura:** Dashboards especializados con estadísticas gráficas y supervisión académica.

## 🛠️ Tecnologías Utilizadas

*   **Backend:** FastAPI (Python 3.9+), PostgreSQL, SQLAlchemy, JWT Authentication, Pydantic.
*   **Frontend:** Vanilla Javascript (ES6+), HTML5 Semántico, CSS3 Premium (Glassmorphism, Gradients), Chart.js, jsPDF, SweetAlert2.
*   **IA:** Integración con modelos de lenguaje (OpenAI/Gemini) para generación de contenido.
*   **Despliegue:** Configuración lista para Railway (`railway.json`).

## 🚀 Instalación y Configuración

### 1. Clonar y configurar variables
Copia el archivo `.env.example` a `.env` y configura tus claves:
```env
DATABASE_URL=postgresql://user:pass@localhost/dbname
JWT_SECRET=tu_secreto_super_seguro
GEMINI_API_KEY=tu_clave_de_ia
```

### 2. Backend
```bash
cd backend
pip install -r requirements.txt
python main.py
```
El servidor correrá en `http://localhost:8000`.

### 3. Frontend
Simplemente sirve la carpeta `frontend/` con cualquier servidor web (ej: Live Server en VS Code). El sistema detectará automáticamente si estás en local o en producción gracias a `js/api.js`.

## 🔒 Roles y Permisos

*   **Administrador / Director:** Acceso total a todos los subsistemas y estadísticas.
*   **Secretaria:** Gestión de usuarios, inscripciones y comunicados.
*   **Jefe de Carrera:** Gestión de malla curricular y supervisión de notas.
*   **Docente:** Publicación de materiales, registro de notas y uso de Planes IA.
*   **Estudiante:** Acceso a materiales, consulta de notas y participación en votaciones.

## 📝 Notas de Versión (v21.0)
*   Modularización completa de todos los subsistemas.
*   Limpieza de codificación UTF-8 en todos los archivos front-end.
*   Implementación de detección automática de entorno de API.
*   Nuevos dashboards especializados para Dirección y Jefatura.
*   Mejora estética en la generación de certificados y planes PDF.

---
Desarrollado con ❤️ para la educación del futuro.
