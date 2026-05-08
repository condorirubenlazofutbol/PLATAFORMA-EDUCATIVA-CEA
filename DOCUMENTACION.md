# Guía Técnica de EduConnect Pro v21.0 📚

Esta documentación detalla la arquitectura, el flujo de datos y los estándares del ecosistema para facilitar futuras mejoras y escalabilidad.

## 1. Arquitectura del Sistema
El sistema utiliza una arquitectura **Decoupled (Desacoplada)**:
- **Backend:** API RESTful construida con **FastAPI** (Python).
- **Frontend:** Single Page Application (SPA) conceptual usando **Vanilla Javascript**, HTML5 y CSS3.
- **Base de Datos:** **PostgreSQL** con persistencia relacional.

## 2. Estructura de Archivos
```text
/Educonnect-Ruben
  /backend
    /routes        -> Endpoints divididos por lógica (auth, notas, ai, etc.)
    main.py        -> Punto de entrada y configuración de FastAPI.
    database.py    -> Gestión de conexiones y esquemas SQL.
    models.py      -> Definición de objetos de datos (Pydantic).
    security.py    -> Lógica de hashing y JWT.
    seed.py        -> Datos iniciales (usuarios prueba).
    seed_modulos.py -> Malla curricular inicial.
  /frontend
    /js
      api.js       -> Configuración global de la URL del servidor.
    /portal        -> Dashboard central de acceso.
    /notas         -> Gestión de calificaciones y PDFs.
    /modulos       -> Aula virtual y materiales.
    /votacion      -> Sistema de elecciones.
    /planes        -> Generador IA para docentes.
    /secretaria    -> Panel administrativo.
    /director      -> Dashboard de analítica.
    index.html     -> Landing Page pública (Inicio).
    login.html     -> Acceso unificado.
```

## 3. Flujo de Autenticación
1. El usuario envía credenciales a `/auth/login`.
2. El servidor valida contra PostgreSQL y devuelve un **JWT (JSON Web Token)** y el **Rol**.
3. El frontend guarda el token en `localStorage`.
4. Cada petición subsiguiente incluye el token en el header: `Authorization: Bearer <TOKEN>`.

## 4. Integración de IA
El módulo de **Planes IA** (`/ai/generar-planificacion`) utiliza la librería `google-generativeai` (o similar) para procesar prompts educativos. 
- **Para mejorar:** Puedes cambiar el motor de IA en `backend/routes/ai_tools.py` simplemente actualizando la API Key y el modelo.

## 5. Base de Datos (Esquemas Clave)
- **usuarios:** id, nombre, email, password, rol, carnet, nivel_asignado.
- **modulos:** id, nombre, nivel, subnivel, orden.
- **progreso:** usuario_id, modulo_id, nota, estado (aprobado/reprobado/cursando).
- **votos:** eleccion_id, estudiante_id, candidato_id (anonimizado).

## 6. Estándares de Diseño (CSS)
Se utiliza un sistema de **Glassmorphism**:
- `background: rgba(19, 25, 41, 0.7)` para tarjetas.
- `backdrop-filter: blur(12px)` para profundidad.
- Colores principales: `#0ea5e9` (Primario), `#8b5cf6` (Acento), `#48d18e` (Éxito).

## 7. Despliegue
- **Local:** `python backend/main.py`.
- **Producción:** El sistema está configurado para **Railway**. Solo necesitas subir el repositorio y conectar la base de datos PostgreSQL. Las variables de entorno necesarias son:
  - `DATABASE_URL`
  - `JWT_SECRET`
  - `GEMINI_API_KEY` (Opcional para IA)

## 8. Recomendaciones para Mejoras Futuras
1. **Notificaciones:** Implementar WebSockets o Firebase para avisos en tiempo real.
2. **Chat Interno:** Añadir un módulo de mensajería entre docentes y alumnos.
3. **App Móvil:** El sistema ya es PWA (Progressive Web App), pero podrías usar Capacitor para convertirlo en APK/IPA nativo.
4. **Reportes Avanzados:** Usar librerías como `Pandas` en el backend para generar reportes Excel detallados en Secretaría.

---
Documentación generada para CEA "Prof. Hérman Ortiz Camargo".
