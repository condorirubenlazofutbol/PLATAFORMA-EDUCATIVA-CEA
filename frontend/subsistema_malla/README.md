# 🚀 Sistemas Informáticos CEA - Plataforma LMS

Bienvenido a la documentación oficial de la plataforma educativa para el **Centro de Educación Alternativa (CEA)**. Este sistema es un LMS (Learning Management System) diseñado para gestionar la malla curricular, estudiantes y evaluaciones de manera eficiente y moderna.

## 🛠️ Tecnologías Utilizadas

- **Backend:** [FastAPI](https://fastapi.tiangolo.com/) (Python 3.9+)
- **Frontend:** HTML5, CSS3 (Glassmorphism), JavaScript (Vanilla)
- **Base de Datos:** [PostgreSQL](https://www.postgresql.org/)
- **Despliegue:** [Railway](https://railway.app/)
- **PWA:** Service Workers para instalación como App nativa.

---

## 📈 Guía de Escalamiento (Scaling)

Para que esta aplicación pueda soportar miles de usuarios en el futuro, se recomiendan los siguientes pasos:

### 1. Nivel de Base de Datos
- **Réplicas de Lectura:** Configurar una réplica de PostgreSQL en Railway para manejar las consultas de los estudiantes mientras el servidor principal maneja las escrituras de los profesores.
- **Pooling de Conexiones:** Implementar `SQLAlchemy` con `PgBouncer` para optimizar el uso de conexiones a la base de datos.

### 2. Nivel de Backend (API)
- **Balanceo de Carga:** Desplegar múltiples instancias del cuadrito `BACKEND` en Railway. Railway balanceará el tráfico automáticamente entre ellas.
- **Caché con Redis:** Implementar Redis para cachear la Malla Curricular y las sesiones, reduciendo el tiempo de respuesta a milisegundos.

### 3. Nivel de Almacenamiento
- **CDN para Archivos:** Actualmente los archivos se sirven desde el servidor. Para escalar, se deben mover los materiales (PDFs, Videos) a un servicio como **Amazon S3** o **Google Cloud Storage** y servirlos mediante una CDN (Cloudflare).

### 4. Aplicación Móvil Nativa
- El sistema ya es una **PWA**. Para escalar a tiendas (Play Store/App Store), se recomienda usar **Capacitor** para envolver el código actual y convertirlo en una App nativa sin rehacer el proyecto.

---

## ⚙️ Instalación Local

Si deseas ejecutar el proyecto en tu propia computadora:

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/tu-usuario/Modulos-sistemas-informaticos-CEA.git
   ```

2. **Backend:**
   - Crear un entorno virtual: `python -m venv venv`
   - Instalar dependencias: `pip install -r backend/requirements.txt`
   - Configurar `.env` con tu `DATABASE_URL`.
   - Ejecutar: `uvicorn backend.main:app --reload`

3. **Frontend:**
   - Simplemente abre `frontend/login.html` en tu navegador o usa un servidor local como "Live Server".

---

## 📞 Soporte
Para más información sobre los componentes del equipo, consulta el archivo [PROYECTO_FINAL.md](PROYECTO_FINAL.md).

---
*Desarrollado con ❤️ para el CEA - 2024*

## ⚙️ Guía de Despliegue (Railway)

La plataforma está optimizada para ser desplegada en **Railway** de forma rápida y automatizada mediante Nixpacks.

### 1. Variables de Entorno (Environment Variables)
En el panel de Railway, debes configurar las siguientes variables en el servicio del backend:
- `DATABASE_URL`: URL de conexión a PostgreSQL (Ej: `postgresql://postgres:pass@host:5432/railway`). Railway puede inyectarla automáticamente si enlazas un servicio de Postgres.
- `PORT`: (Opcional) Railway asigna el puerto dinámicamente, Nixpacks lo lee por defecto.

### 2. Comandos de Arranque (Procfile)
El repositorio contiene un archivo `Procfile` en la raíz que instruye a Railway sobre cómo iniciar el servidor:
```bash
web: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
```

### 3. Migraciones y Base de Datos
El sistema incluye una función de "Auto-Migración". Al iniciar el servidor (startup event de Uvicorn), FastAPI llama a `database.init_db()` que:
1. Crea todas las tablas si no existen.
2. Agrega las columnas necesarias.

Para cargar la Malla Curricular y crear el usuario administrador por defecto (`admin@sistemas.com` / `admin123`), se debe visitar el endpoint:
---

## 📈 Guía para Escalar el Proyecto

Si la academia crece y necesitas escalar la plataforma, sigue estas recomendaciones:

### 1. Escalamiento de Base de Datos
- **Connection Pooling:** Actualmente se usa `psycopg2.connect()` directo. Para miles de usuarios concurrentes, implementa **PgBouncer** o usa un pool como `asyncpg` con `SQLAlchemy`.
- **Caché:** Implementa **Redis** para almacenar sesiones JWT cacheadas, configuraciones estáticas y la Malla Curricular, reduciendo lecturas a Postgres.

### 2. Escalamiento de Backend (FastAPI)
- **Workers:** En Railway, puedes cambiar el comando de arranque para usar múltiples workers de Uvicorn/Gunicorn:
  `gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
- **Asincronismo:** Migrar las consultas de la base de datos de síncronas (`psycopg2`) a asíncronas (`asyncpg`) para desbloquear el event loop de FastAPI.

### 3. Separación de Servicios (Microservicios)
- Si el tráfico aumenta demasiado, separa el Frontend y el Backend en dos servicios distintos en Railway.
- Modifica el archivo `frontend/js/api.js` para que `API_URL` apunte al subdominio exclusivo del backend.
- Habilita CORS estricto en FastAPI en lugar de `allow_origins=["*"]`.

### 4. Almacenamiento de Archivos
- Actualmente los materiales (PDFs, videos) se manejan por URLs externas.
- Para subir archivos propios, integra **Amazon S3** o **Cloudinary** en el backend para almacenar documentos sin saturar el disco del servidor.
