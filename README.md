# Arquitectura Funcional: Ecosistema CEA EduConnect Pro

El **Centro de Educación Alternativa (CEA) EduConnect Pro** está diseñado bajo una arquitectura modular y desacoplada (Frontend en HTML/JS/CSS puro + Backend en FastAPI/PostgreSQL). Esto permite que cada subsistema funcione de manera independiente pero consumiendo una base de datos centralizada.

A continuación, se detalla la función completa de la plataforma y cada uno de sus subsistemas para facilitar su escalabilidad y futuras actualizaciones.

---

## 1. Núcleo Central (Hub)

### Portal Hub (`/frontend/portal`)
*   **Función:** Es el punto de entrada unificado. Tras el login, evalúa el `rol` del usuario (director, secretaria, jefe_carrera, docente, estudiante) a través de un token JWT.
*   **Escalabilidad:** Las tarjetas (`app-card`) del portal se muestran u ocultan mediante el atributo `data-roles`. Para agregar un nuevo subsistema en el futuro, solo se requiere crear una nueva tarjeta HTML e indicar qué roles pueden verla.

### Sistema de Autenticación (`/backend/routes/auth.py`)
*   **Función:** Manejo de sesiones con tokens seguros (JWT). Centraliza la creación de usuarios y la gestión de roles.
*   **Futura actualización:** Integrar autenticación de Google (OAuth2) o restablecimiento de contraseñas por email.

---

## 2. Subsistemas Académicos y Administrativos

### 🏛️ Dashboard Director (`/frontend/subsistema_director`)
*   **Función:** Panel de inteligencia de negocios (BI). Extrae datos estadísticos en tiempo real sobre la tasa de aprobación, abandono y crecimiento poblacional de las carreras.
*   **Escalabilidad:** Agregar exportación de reportes PDF gerenciales y gráficos comparativos de gestiones anteriores.

### 📋 Panel Secretaría (`/frontend/subsistema_academico/secretaria`)
*   **Función:** Módulo de inscripciones (carga manual y masiva por Excel), gestión de la comunidad estudiantil, publicación de comunicados oficiales e inicio de procesos electorales.
*   **Escalabilidad:** Integrar pasarelas de pago para el cobro de matrículas o mensualidades, y generación automática de recibos.

### 📐 Panel Jefatura (`/frontend/subsistema_academico/jefe_carrera`)
*   **Función:** Asignación de carga horaria. El Jefe de Carrera designa qué docente imparte qué módulo en cada nivel/carrera.

---

## 3. Subsistemas de Desarrollo Curricular

### 🧩 Malla Curricular (`/frontend/subsistema_malla`)
*   **Función:** Define la estructura académica del CEA. (Carreras → Niveles → Módulos → Temas). Permite carga masiva vía Excel.
*   **Escalabilidad:** Vincular los temas directamente con repositorios del Ministerio de Educación.

### 🤖 Generador de Planes IA (`/frontend/subsistema_planes`)
*   **Función:** Integración directa con Google Gemini AI. Lee automáticamente la Malla Curricular y redacta Planes Semestrales y de Aula-Taller adaptados al modelo MESCP boliviano.
*   **Escalabilidad:** Incorporar IA para la generación de rúbricas de evaluación dinámicas basadas en el plan generado.

---

## 4. Subsistemas de Seguimiento en Aula

### ✅ Control de Asistencia (`/frontend/subsistema_asistencia`)
*   **Función:** Registro diario por sesión. El docente marca Presente, Ausente, Tardanza o Permiso. El estudiante visualiza una barra de rendimiento porcentual.
*   **Escalabilidad:** Integrar notificaciones Push (vía Web Push API) al teléfono del estudiante cuando acumule más de 3 faltas.

### 📅 Horarios y Aulas (`/frontend/subsistema_horarios`)
*   **Función:** Asignación de bloques de tiempo y espacios físicos.
*   **Escalabilidad:** Detectar cruces de horarios de forma automática antes de que el Director guarde el bloque.

### 📊 Cuadro de Valoración (Notas) (`/frontend/subsistema_notas`)
*   **Función:** Registro de calificaciones segmentadas (Ser, Saber, Hacer, Decidir) según el reglamento del CEA. Diferencia entre área Humanística y Técnica. Genera el acta en formato Excel oficial.

---

## 5. Subsistemas del Estudiante y Recursos

### 📁 Kardex Académico (`/frontend/subsistema_kardex`)
*   **Función:** El expediente central de cada estudiante. Consolida: notas, asistencia, constancias y estado académico.
*   **Escalabilidad:** Digitalización de documentos (subir fotos del CI, Certificado de Nacimiento y Título de Bachiller anterior).

### 📚 Biblioteca Digital (`/frontend/subsistema_biblioteca`)
*   **Función:** Repositorio de links, PDFs y videos catalogados por módulo.
*   **Escalabilidad:** Integrar previsualizadores de documentos directamente en el navegador (para que no tengan que descargar archivos pesados).

### 📝 Evaluaciones Online (`/frontend/subsistema_evaluaciones`)
*   **Función:** Creación de exámenes contra reloj con calificación automática vinculada directamente al progreso del estudiante.
*   **Escalabilidad:** Soporte para preguntas abiertas calificadas con IA o integradas con subida de imágenes/archivos.

---

## 6. Subsistemas Institucionales Especiales

### 📜 Certificaciones (`/frontend/subsistema_certificados`) y Constancias (`/frontend/subsistema_constancias`)
*   **Función:** Generación de documentos oficiales. Las certificaciones se generan al aprobar con nota ≥51 (con Código QR). Las constancias se generan a partir de plantillas dinámicas redactadas por el Director con variables (ej. `[NOMBRE]`).
*   **Escalabilidad:** Firmas digitales oficiales encriptadas o validación blockchain para evitar falsificaciones.

### 🗳️ Votación Institucional (`/frontend/subsistema_elecciones`)
*   **Función:** Automatiza las elecciones del centro de estudiantes. Valida que el votante esté inscrito, garantiza el voto secreto y genera escrutinios en tiempo real.

---

## 🚀 Resumen para Escalabilidad Futura

1.  **Frontend Desacoplado:** Si quieres cambiar el diseño, solo debes tocar los archivos CSS y HTML dentro de las carpetas de `/frontend/`. No afectará a la base de datos ni a la lógica.
2.  **API Restful (FastAPI):** Cada subsistema tiene su propio archivo en `/backend/routes/`. Si deseas crear una App móvil en el futuro (React Native o Flutter), puedes consumir las *mismas rutas* sin modificar ni una línea de código del servidor.
3.  **Base de Datos Relacional:** El uso de PostgreSQL garantiza integridad. Cualquier módulo nuevo debe relacionarse con la tabla `usuarios` o `modulos` para mantener el ecosistema conectado.
