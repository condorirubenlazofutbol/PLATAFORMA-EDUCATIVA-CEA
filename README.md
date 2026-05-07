# 🎓 EduConnect Pro v21.0

Plataforma educativa multi-subsistema con roles jerárquicos, IA pedagógica, votaciones, certificados y gestión académica integral.

---

## 🗂 Estructura del Proyecto

```
Educonnect-Ruben/
├── backend/                    ← API FastAPI (Python)
│   ├── main.py                 ← Entrada principal
│   ├── database.py             ← Esquema PostgreSQL
│   ├── models.py               ← Modelos Pydantic
│   ├── security.py             ← JWT y hashing
│   ├── seed_modulos.py         ← Datos iniciales
│   ├── requirements.txt
│   └── routes/
│       ├── auth.py             ← Login, registro, JWT
│       ├── modulos.py          ← Materias y contenidos
│       ├── notas.py            ← Calificaciones y progreso
│       ├── certificados.py     ← Emisión de certificados
│       ├── comunicados.py      ← Avisos institucionales
│       ├── votaciones.py       ← Elecciones y votos
│       ├── evaluaciones.py     ← Evaluaciones
│       └── ai_tools.py         ← Generador con IA
│
├── frontend/                   ← Sitio estático
│   ├── index.html              ← Landing page pública
│   ├── login.html              ← Acceso unificado
│   ├── instalar/               ← PWA (manifest, pwa.js)
│   ├── images/                 ← Logo y share-icon
│   ├── js/api.js               ← URL automática (local/prod)
│   ├── portal/                 ← Dashboard principal
│   ├── notas/                  ← Calificaciones y certificados
│   ├── modulos/                ← Aula virtual
│   ├── malla_curricular/       ← Programa de estudios
│   ├── planes/                 ← Generador IA (Docentes)
│   ├── votacion/               ← Sistema electoral
│   ├── comunicados/            ← Tablón de avisos
│   └── secretaria/             ← Panel de Secretaría
│
├── .env.example                ← Plantilla de variables
├── railway.json                ← Config de Railway
└── render.yaml                 ← Config de Render
```

---

## 👥 Roles del Sistema

| Rol | Acceso |
|-----|--------|
| `director` | Todo |
| `jefe_carrera` | Malla, Notas (read), Planes IA |
| `secretaria` | Panel Secretaría, Comunicados, Votaciones, Usuarios |
| `docente` | Aula Virtual, Notas (write), Planes IA |
| `estudiante` | Notas, Módulos, Votaciones, Malla |

---

## 🚀 Despliegue en Railway

### Paso 1: Backend
1. En Railway, crea un nuevo proyecto.
2. Conecta tu repositorio de GitHub.
3. Railway detecta `railway.json` automáticamente.
4. Agrega las **Variables de Entorno**:

```env
DATABASE_URL=<url-de-tu-postgres-en-railway>
SECRET_KEY=<clave-aleatoria-de-32-caracteres>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
```

5. Para activar la IA real, agrega también:
```env
OPENAI_API_KEY=sk-proj-...
```

### Paso 2: Base de Datos
1. En Railway, agrega un servicio **PostgreSQL**.
2. Railway inyecta `DATABASE_URL` automáticamente al backend.
3. Para inicializar las tablas, visita:
   ```
   https://tu-backend.railway.app/cargar-datos
   ```

### Paso 3: Frontend
1. El frontend es **HTML estático puro** — no necesita servidor.
2. Sube la carpeta `frontend/` a Railway Static, Netlify, Vercel o GitHub Pages.
3. El archivo `frontend/js/api.js` ya detecta automáticamente si está en producción.

---

## 💻 Desarrollo Local

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/Educonnect-Ruben.git
cd Educonnect-Ruben

# 2. Crear entorno virtual Python
python -m venv venv
.\venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Instalar dependencias
pip install -r backend/requirements.txt

# 4. Configurar variables de entorno
copy .env.example .env
# Edita .env con tus credenciales de PostgreSQL local

# 5. Inicializar la base de datos
python backend/database.py

# 6. Iniciar el servidor
uvicorn backend.main:app --reload

# 7. Abrir el frontend
# Abre frontend/index.html en tu navegador
```

Luego visita `http://localhost:8000/docs` para ver la documentación interactiva de la API.

---

## 📡 Endpoints Principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/auth/login` | Inicio de sesión |
| GET  | `/auth/me` | Perfil del usuario actual |
| GET  | `/notas/mis-notas` | Notas del estudiante |
| PUT  | `/notas/actualizar` | Guardar calificación |
| GET  | `/modulos/` | Lista de módulos |
| POST | `/votaciones/elecciones` | Crear votación |
| POST | `/votaciones/votar` | Emitir voto |
| POST | `/comunicados/avisos` | Publicar aviso |
| POST | `/ai/generar-planificacion` | Generar plan con IA |
| POST | `/certificados/emitir` | Emitir certificado |

---

## 🌐 URLs del Proyecto (Producción)

- **Backend API:** https://educonnect-backend-production-1d08.up.railway.app
- **Docs API:** https://educonnect-backend-production-1d08.up.railway.app/docs

---

Desarrollado con ❤️ por **Ruben Lazo** · Powered by **EduConnect Pro v21.0**
