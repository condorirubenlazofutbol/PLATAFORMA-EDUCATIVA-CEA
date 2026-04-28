# 📚 EduConnect Ruben – Documentación Técnica

## Índice
1. [Descripción del Proyecto](#1-descripción-del-proyecto)
2. [Arquitectura General](#2-arquitectura-general)
3. [Estructura del Repositorio](#3-estructura-del-repositorio)
4. [Sistema de Roles y Accesos](#4-sistema-de-roles-y-accesos)
5. [Estructura Académica](#5-estructura-académica)
6. [Backend (FastAPI)](#6-backend-fastapi)
7. [Frontend (HTML/CSS/JS)](#7-frontend-htmlcssjs)
8. [Base de Datos (PostgreSQL)](#8-base-de-datos-postgresql)
9. [Despliegue en Railway](#9-despliegue-en-railway)
10. [Credenciales por Defecto](#10-credenciales-por-defecto)
11. [Cómo Escalar la Plataforma](#11-cómo-escalar-la-plataforma)
12. [API Reference](#12-api-reference)

---

## 1. Descripción del Proyecto

**EduConnect Ruben** es una plataforma LMS (Learning Management System) académica diseñada para gestionar cursos de Sistemas Informáticos estructurados en 5 niveles y 10 semestres.

### Tecnologías principales
| Capa | Tecnología |
|---|---|
| Backend | Python 3.13 + FastAPI |
| Base de Datos | PostgreSQL |
| Frontend | HTML5 + CSS3 + JavaScript (Vanilla) |
| Hosting | Railway.app |
| Control de versiones | Git + GitHub |

### URLs de producción
| Servicio | URL |
|---|---|
| Frontend | https://educonnect-frontend-production-5d49.up.railway.app |
| Backend API | https://educonnect-backend-production-1d08.up.railway.app |
| API Docs (Swagger) | https://educonnect-backend-production-1d08.up.railway.app/docs |

---

## 2. Arquitectura General

```
┌─────────────────────────────────────────────────────────┐
│                     RAILWAY.APP                          │
│                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │  Frontend   │───▶│   Backend   │───▶│  PostgreSQL │  │
│  │  (serve)    │    │  (FastAPI)  │    │  Database   │  │
│  │  :$PORT     │    │  :$PORT     │    │  :5432      │  │
│  └─────────────┘    └─────────────┘    └─────────────┘  │
│         │                  │                             │
│   Static HTML/JS      REST API + JWT                     │
└─────────────────────────────────────────────────────────┘
          │
    ┌─────┴──────┐
    │  GitHub    │ (condorirubenlazofutbol/Educonnect-Ruben)
    │  (CI/CD)   │ Auto-deploy on push to main
    └────────────┘
```

**Flujo de datos:**
1. El usuario accede al Frontend estático
2. El JS del frontend llama a la API del Backend usando `API_URL`
3. El Backend verifica JWT tokens y consulta/modifica PostgreSQL
4. La respuesta JSON regresa al frontend y se renderiza en el DOM

---

## 3. Estructura del Repositorio

```
Educonnect-Ruben/
│
├── backend/                    # API FastAPI
│   ├── main.py                 # Punto de entrada, CORS, rutas
│   ├── database.py             # Conexión PostgreSQL + creación de tablas
│   ├── security.py             # JWT tokens + bcrypt hashing
│   ├── seed_modulos.py         # Script seed: usuarios + malla curricular
│   ├── requirements.txt        # Dependencias Python
│   ├── Procfile                # Comando de inicio para Railway
│   └── routes/
│       ├── auth.py             # Login, registro, gestión de usuarios
│       ├── modulos.py          # CRUD módulos y contenidos
│       └── evaluaciones.py     # Evaluaciones y calificaciones
│
├── frontend/                   # Aplicación web estática
│   ├── index.html              # Página pública (visitantes sin login)
│   ├── login.html              # Pantalla de inicio de sesión
│   ├── package.json            # Config para servir con `serve` en Railway
│   ├── js/
│   │   └── api.js              # API_URL + utilidades compartidas
│   ├── css/
│   │   └── style.css           # Estilos globales legacy
│   ├── images/                 # Logo y assets de niveles
│   ├── student/
│   │   └── dashboard.html      # Panel del estudiante
│   ├── admin/
│   │   └── dashboard.html      # Panel del administrador
│   ├── profesor/
│   │   └── dashboard.html      # Panel del profesor
│   └── instalar/               # PWA manifest
│
├── render.yaml                 # Blueprint Render (legacy, usar Railway)
└── README.md                   # Esta documentación
```

---

## 4. Sistema de Roles y Accesos

### Roles disponibles

| Rol | Descripción | Panel |
|---|---|---|
| `administrador` | Control total del sistema | `admin/dashboard.html` |
| `profesor` | Sube material a su nivel/semestre | `profesor/dashboard.html` |
| `estudiante` | Ve módulos y materiales de su nivel | `student/dashboard.html` |

### Flujo de acceso

```
Visitante (sin login)
  └── index.html → Ve todos los niveles/módulos/temas (SIN materiales)

Login → Redirección según rol:
  ├── administrador → admin/dashboard.html
  ├── profesor      → profesor/dashboard.html
  └── estudiante    → student/dashboard.html
```

### Lógica de visibilidad

| Contenido | Visitante | Estudiante | Profesor | Admin |
|---|---|---|---|---|
| Niveles (5) | ✅ Todos | ✅ Solo su nivel | ✅ Su nivel | ✅ Todos |
| Módulos | ✅ Nombres | ✅ Su nivel | ✅ Su nivel | ✅ Todos |
| Temas (4 por módulo) | ✅ Nombres | ✅ Con materiales | ✅ Con materiales | ✅ Todo |
| Materiales del profesor | ❌ Bloqueado | ✅ Su nivel | ✅ Puede subir/borrar | ✅ Todo |

---

## 5. Estructura Académica

La plataforma tiene **5 niveles**, **10 semestres** y módulos con **4 temas** cada uno:

| Nivel | Semestres | Módulos | Temas/módulo |
|---|---|---|---|
| 🔰 Básico | 1 | 5 | 4 |
| ⚙️ Auxiliar | 1 | 5 | 4 |
| 📚 Medio | 2 (M1, M2) | 5 por semestre | 4 |
| 🚀 Superior | 2 (S1, S2) | 5 por semestre | 4 |
| 🏗️ Ingeniería | 4 (I1–I4) | 4 por semestre | 4 |

### Asignación de profesores
- El **Admin** asigna a cada profesor un nivel/semestre específico (ej. "Medio - M1")
- El valor se guarda en el campo `nivel_asignado` del usuario en la BD
- El panel del profesor filtra los módulos usando ese valor

---

## 6. Backend (FastAPI)

### Endpoints principales

#### Autenticación (`/auth`)
| Método | Endpoint | Descripción | Acceso |
|---|---|---|---|
| POST | `/auth/login` | Login con email y contraseña | Público |
| GET | `/auth/me` | Datos del usuario actual | Token |
| POST | `/auth/register-profesor` | Crear profesor | Admin |
| POST | `/auth/register-estudiante` | Inscribir estudiante | Admin |
| GET | `/auth/profesores` | Listar profesores | Admin |
| GET | `/auth/estudiantes` | Listar estudiantes | Admin |
| DELETE | `/auth/usuarios/{id}` | Eliminar usuario | Admin |

#### Módulos (`/modulos`)
| Método | Endpoint | Descripción | Acceso |
|---|---|---|---|
| GET | `/modulos/` | Listar todos los módulos | Público |
| GET | `/modulos/nivel/{nivel}` | Módulos por nivel | Público |
| GET | `/modulos/{id}/contenidos` | Contenidos de un módulo | Público |
| POST | `/modulos/{id}/contenidos` | Subir material | Profesor/Admin |
| PUT | `/modulos/contenidos/{id}` | Editar material | Profesor/Admin |
| DELETE | `/modulos/contenidos/{id}` | Eliminar material | Profesor/Admin |

#### Utilidades
| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/` | Estado de la API y BD |
| GET | `/cargar-datos` | Seed: crea usuarios + malla curricular |

### Variables de entorno requeridas

```env
DATABASE_URL=postgresql://user:pass@host:5432/dbname
SECRET_KEY=tu-clave-secreta-jwt-muy-segura
```

---

## 7. Frontend (HTML/CSS/JS)

### Diseño
- **Tipografía**: Inter (Google Fonts)
- **Paleta principal**: `#6c63ff` (violeta), `#48d18e` (verde), `#0b0f1a` (fondo)
- **Estilo**: Glassmorphism + Dark Mode + gradientes suaves
- **Animaciones**: fadeIn en tarjetas, accordion con CSS transition

### Archivo `js/api.js`
Contiene la variable global `API_URL` que apunta al backend. 
**Para cambiar el backend, solo edita esta línea:**
```javascript
const API_URL = "https://educonnect-backend-production-1d08.up.railway.app";
```

### Agregar una nueva página
1. Crear el archivo HTML en la carpeta correspondiente
2. Incluir `<script src="../js/api.js"></script>` al inicio
3. Verificar el token JWT al cargar: `localStorage.getItem('token')`
4. Redirigir a `../login.html` si no hay token

---

## 8. Base de Datos (PostgreSQL)

### Tablas

```sql
-- Usuarios del sistema
usuarios (
  id SERIAL PRIMARY KEY,
  nombre VARCHAR(100),
  apellido VARCHAR(100),
  email VARCHAR(150) UNIQUE,
  password VARCHAR(255),        -- bcrypt hash
  rol VARCHAR(20),              -- 'administrador' | 'profesor' | 'estudiante'
  nivel_asignado VARCHAR(100)   -- ej: 'Básico', 'Medio - M1', 'Ingeniería'
)

-- Módulos académicos
modulos (
  id SERIAL PRIMARY KEY,
  nombre VARCHAR(200),          -- ej: 'Programación Intermedia'
  nivel VARCHAR(100),           -- ej: 'Medio'
  subnivel VARCHAR(100),        -- ej: '3er SEMESTRE - MEDIO I'
  orden INT                     -- orden de aparición
)

-- Contenidos/materiales de cada módulo
contenidos (
  id SERIAL PRIMARY KEY,
  modulo_id INT REFERENCES modulos(id) ON DELETE CASCADE,
  tipo VARCHAR(50),             -- 'video' | 'teoria' | 'pdf' | 'presentacion' | 'audio'
  titulo VARCHAR(200),
  url TEXT,                     -- URL del material
  tema_num INT                  -- 1, 2, 3 o 4
)

-- Progreso de estudiantes
progreso (
  id SERIAL PRIMARY KEY,
  usuario_id INT REFERENCES usuarios(id),
  modulo_id INT REFERENCES modulos(id),
  estado VARCHAR(50),           -- 'inscrito' | 'aprobado' | 'reprobado'
  nota DECIMAL(5,2),
  UNIQUE(usuario_id, modulo_id)
)

-- Evaluaciones por módulo
evaluaciones (
  id SERIAL PRIMARY KEY,
  modulo_id INT REFERENCES modulos(id),
  pregunta TEXT,
  opciones JSONB,
  respuesta_correcta VARCHAR(200)
)
```

---

## 9. Despliegue en Railway

### Proyecto actual
- **Proyecto Railway**: `comfortable-alignment`
- **Servicios**: `educonnect-backend`, `educonnect-frontend`, `Postgres`

### Variables configuradas en Railway
```
# Backend
DATABASE_URL    → (referencia automática a Postgres)
SECRET_KEY      → (configurar manualmente)

# Backend - Settings
Root Directory  → /backend
Start Command   → uvicorn main:app --host 0.0.0.0 --port $PORT

# Frontend - Settings
Root Directory  → /frontend
```

### CI/CD
Railway despliega automáticamente en cada `git push` a la rama `main`.

### Inicializar datos en producción
Después de cada reset de base de datos, ejecutar:
```
GET https://educonnect-backend-production-1d08.up.railway.app/cargar-datos
```
Esto crea: usuarios por defecto + malla curricular completa.

---

## 10. Credenciales por Defecto

> ⚠️ **Cambiar las contraseñas después del primer inicio de sesión en producción.**

| Rol | Email | Contraseña |
|---|---|---|
| 👑 Administrador | admin@educonnect.com | Admin2026! |
| 👨‍🏫 Profesor | profesor@educonnect.com | Profesor2026! |
| 🎓 Estudiante | estudiante@educonnect.com | Estud2026! |

---

## 11. Cómo Escalar la Plataforma

### Agregar un nuevo nivel académico
1. **Frontend** (`js/api.js` o `student/dashboard.html`): Agregar el nivel al array `CURRICULUM`
2. **Seed** (`backend/seed_modulos.py`): Agregar las entradas al array `MALLA`
3. **Admin panel**: El dropdown de "Nivel asignado" se actualiza manualmente en `admin/dashboard.html`
4. Ejecutar `/cargar-datos` para regenerar la BD

### Agregar un nuevo tipo de material
1. En `profesor/dashboard.html`: agregar opción al `<select id="tipo-...">`
2. En `student/dashboard.html`: agregar el ícono en el objeto `typeIcon` y color en `typeColor`

### Agregar evaluaciones interactivas
- Usar la tabla `evaluaciones` existente
- El endpoint `POST /evaluaciones` ya está preparado
- Crear `student/evaluacion.html` con el formulario de preguntas

### Agregar chat o foros
- Crear nueva tabla `mensajes` en `database.py`
- Agregar ruta en `backend/routes/`
- Crear componente en el frontend

### Agregar notificaciones por email
- Integrar `fastapi-mail` en el backend
- Usar `sendgrid` o `resend.com` como proveedor SMTP
- Disparar notificaciones desde los endpoints de registro

---

## 12. API Reference

Documentación interactiva Swagger disponible en:
```
https://educonnect-backend-production-1d08.up.railway.app/docs
```

Documentación alternativa ReDoc:
```
https://educonnect-backend-production-1d08.up.railway.app/redoc
```

---

*Documentación generada automáticamente · EduConnect Ruben v5.0 · 2026*
