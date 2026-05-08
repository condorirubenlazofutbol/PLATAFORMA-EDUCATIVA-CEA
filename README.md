# Ecosistema CEA EduConnect Pro — Documentación Técnica

El **Centro de Educación Alternativa (CEA) EduConnect Pro** está diseñado bajo una arquitectura modular y desacoplada. Esto permite que cada subsistema funcione de manera independiente pero consumiendo una base de datos centralizada, garantizando una alta escalabilidad y un entorno seguro para docentes, estudiantes y administrativos.

## 👥 Arquitectura de Permisos y Roles
La plataforma utiliza un modelo de acceso basado en roles (`RBAC - Role Based Access Control`). Cada usuario solo visualiza en su Portal (Hub) las tarjetas/cuadros de los módulos a los que tiene acceso legítimo. 

A continuación, la matriz de acceso (`data-roles`) para cada módulo:

| Subsistema / Módulo | Administrador | Director | Secretaria | Jefe de Carrera | Docente | Estudiante |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Dashboard Director** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Panel Secretaría** | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Panel Jefatura** | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **Aula Virtual** | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| **Asistencia Diaria** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Registro de Notas** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Malla Curricular** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Horarios y Aulas** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Planes IA** | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ |
| **Biblioteca Digital** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Evaluaciones Online** | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| **Kardex Académico** | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Certificados** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Constancias** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Votaciones CEA** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Comunicados** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

> **Nota para Desarrolladores:** Para dar o quitar acceso a un rol sobre un módulo, simplemente edita el atributo `data-roles` en `frontend/portal/index.html`. El backend en FastAPI valida el token JWT para prevenir accesos no autorizados mediante inyección de rutas.

---

## 🏗️ Especificación Técnica por Subsistema

### 1. Núcleo Central (Hub)
- **Frontend:** `/frontend/portal/index.html`
- **Backend:** `/backend/routes/auth.py`
- **Responsabilidad:** Punto de entrada. Evalúa el token JWT y renderiza las tarjetas dinámicamente según el rol.
- **Escalabilidad:** Se puede agregar OAuth2 (Google Login) expandiendo el endpoint de `auth.py`.

### 2. Gestión Administrativa
- **Dashboard Director:** Inteligencia de Negocios (BI) para tasas de retención y egresos.
- **Panel Secretaría:** Sistema de matriculación de estudiantes (por Excel/manual) y reportes.
- **Panel Jefatura:** Asignación de carga horaria (quién dicta qué y cuándo).

### 3. Desarrollo Curricular y Aula
- **Malla Curricular:** Define la estructura de carreras (Sistemas Informáticos, Veterinaria, Belleza Integral) y sus módulos respectivos.
- **Planes IA:** Genera rúbricas y PDCs (Plan de Desarrollo Curricular) conectándose a Gemini AI para los módulos del CEA.
- **Aula Virtual & Notas:** Módulos para subir recursos y llenar el cuadro de valoración basado en el modelo boliviano (Ser, Saber, Hacer, Decidir).
- **Asistencia & Horarios:** Cruce de datos para control diario y asignación de aulas físicas o laboratorios.

### 4. Herramientas del Estudiante
- **Kardex Académico:** Concentra el avance histórico, descargas de boletines y registro biométrico/fotográfico del estudiante.
- **Evaluaciones Online:** Sistema de pruebas en tiempo real con límite de tiempo y calificación automatizada.
- **Biblioteca Digital:** Repositorio de recursos (videos, PDFs) filtrados inteligentemente por la carrera del estudiante.

### 5. Servicios Institucionales
- **Certificados & Constancias:** Generación de diplomas finales con validación por código QR y sistema de plantillas dinámicas (con variables como `[NOMBRE]`).
- **Elecciones (Votaciones CEA):** Módulo aislado para elecciones del centro de estudiantes garantizando el voto secreto de cada CI empadronado.

---

## 🛠️ Escalabilidad y Limpieza de Datos
El proyecto ha sido limpiado de módulos experimentales (como Ingenierías o Módulos Universitarios) para reflejar exclusivamente el ámbito del **Centro de Educación Alternativa (CEA)**.

- **Frontend Desacoplado:** Si quieres cambiar el diseño, solo debes tocar los archivos CSS y HTML dentro de las carpetas de `/frontend/`. No afectará a la base de datos ni a la lógica.
- **API Restful (FastAPI):** Cada subsistema tiene su propio archivo en `/backend/routes/`. Si deseas crear una App móvil en el futuro (React Native o Flutter), puedes consumir las *mismas rutas* sin modificar ni una línea de código del servidor.
- **Base de Datos (PostgreSQL):** Las tablas principales (`usuarios`, `carreras`, `modulos`, `notas`) operan bajo estricta integridad referencial. Para migrar o resembrar los datos del CEA, puedes usar los scripts `seed.py` (para usuarios) y `seed_cea.py` (para malla curricular).
