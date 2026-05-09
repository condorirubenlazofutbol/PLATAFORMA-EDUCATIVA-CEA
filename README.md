# 🎓 CEA EduConnect Pro — Ecosistema Educativo Escalable de Nueva Generación

![Preview](frontend/portal/images/compartir.png)

## 🌟 Visión General
**CEA EduConnect Pro** es una plataforma LMS (Learning Management System) y ERP académico de alto rendimiento, diseñada para la escalabilidad y el control institucional del **CEA Prof. Hérman Ortiz Camargo**. Combina una estética moderna basada en *Glassmorphism* con una arquitectura robusta, modular y lista para manejar grandes volúmenes de estudiantes y docentes de educación técnica tecnológica y humanística.

---

## 🏗️ Arquitectura y Escalabilidad (Nivel Pro)
El ecosistema está desacoplado en dos capas principales para garantizar una **alta escalabilidad y rendimiento**:

- **Backend Stateless (API RESTful):** Construido con **FastAPI (Python)** y base de datos relacional **PostgreSQL**. La autenticación se maneja completamente mediante tokens JWT (JSON Web Tokens), lo que permite que el backend no guarde estado de las sesiones, escalando horizontalmente sin fricción.
- **Frontend Modular (Micro-Frontends):** Implementado con **Vanilla HTML5, CSS3 (Flexbox/Grid)** y **JavaScript ES6+**. Al no usar frameworks pesados, cada módulo ("subsistema") carga independientemente en milisegundos, reduciendo el consumo de ancho de banda y memoria.
- **Data en Lote:** Todos los procesos pesados (inscripciones masivas, carga de mallas curriculares) están optimizados con procesamiento asíncrono y lectura de archivos Excel `.xlsx`, evitando saturación de requests.

---

## 📚 Documentación Técnica y Plantillas
Para conocer cómo estructurar la base de datos o usar las funciones masivas, revisa la documentación oficial:
👉 **[Ver Guía de Funcionalidad y Plantillas Excel](docs/FUNCIONALIDAD_Y_PLANTILLAS.md)**

---

## 🧩 Subsistemas y Módulos Escalables

### 1. 🌐 Portal Central (Hub de Enrutamiento)
Punto de entrada unificado con Single Sign-On (SSO). Redirige a los usuarios según su rol y mantiene la sesión segura e inmutable en todos los módulos (evitando el uso del botón "Atrás" post-login).

### 2. 👨‍💼 Subsistema del Director (Dashboard Pro)
- **Directorio Agrupado:** Control y eliminación masiva/individual de personal o estudiantes, con vista agrupada por **Área > Carrera > Nivel**.
- **Panel KPI:** Estadísticas de aprobación y asistencia en tiempo real.
- **Exportación Multinivel:** Descarga de Excel con hojas separadas para Estudiantes, Docentes y Resumen por Carreras.

### 3. 👩‍💻 Subsistema de Secretaría y Jefatura
- **Inscripción y Creación Masiva:** Carga de estudiantes, docentes y módulos completos de la **Malla Curricular** vía Excel, reduciendo el trabajo manual en un 90%.
- **Gestión de Identidades:** Generación automática de correos institucionales.

### 4. 📚 Aula Virtual y Gestión Académica (Docentes/Estudiantes)
- **Kardex y Cuadros de Calificación:** Cumplimiento de la Ley 070 (Ser, Saber, Hacer, Decidir).
- **Control de Asistencia Digital:** Registro diario ágil por módulo.
- **Emisión de Certificados Automatizados:** Certificados autogenerados con validación de código QR (cero falsificaciones).

### 5. 🗳️ Subsistema de Elecciones (Democracia Digital)
- **Alta Concurrencia:** Optimizado para soportar a todos los estudiantes votando simultáneamente usando validación rápida solo con CI.
- **Dashboard Electoral:** Gráficos de barras en tiempo real y seguridad contra el doble voto.

---

## 💎 Características "Nivel Pro" Adicionales
- **Diseño Ultra-Responsivo:** Flex-direction y grids dinámicos para que los paneles de administración complejos (tablas, cuadros) se adapten perfectamente a celulares sin romper el layout.
- **PWA Ready:** Instalable en dispositivos móviles como una aplicación nativa, mejorando la retención de estudiantes.
- **SEO & Open Graph:** Meta-tags configurados globalmente para compartir enlaces institucionales impecables en redes sociales.

---

## 🚀 Despliegue y Mantenimiento
1. **Backend:** Configurar `DATABASE_URL` y variables secretas en `.env`. Ejecutar con `uvicorn main:app --workers 4` para maximizar concurrencia.
2. **Frontend:** Listo para desplegar en cualquier CDN (Cloudflare Pages, Render, Vercel) ya que es completamente estático.
3. **Mantenimiento Cero:** Las actualizaciones de un subsistema no afectan a los demás gracias a la estructura de carpetas modular (`frontend/subsistema_*`).

---
**Desarrollado con 💙 para la excelencia educativa.**
*CEA Prof. Hérman Ortiz Camargo — Pailón, Bolivia.*
