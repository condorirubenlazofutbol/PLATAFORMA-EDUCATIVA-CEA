# 🎓 EduConnect Ruben – Plataforma Educativa Pro

> Sistema de gestión académica completo con roles de Administrador, Profesor y Estudiante. Desplegado en Railway con base de datos PostgreSQL.

---

## 🌐 URLs de Producción

| Recurso | URL |
|---|---|
| **Frontend** | https://condorirubenlazofutbol.github.io/Educonnect-Ruben/ |
| **Backend API** | https://educonnect-backend-production-1d08.up.railway.app |
| **Docs API** | https://educonnect-backend-production-1d08.up.railway.app/docs |
| **Cargar Datos** | https://educonnect-backend-production-1d08.up.railway.app/cargar-datos |

---

## 🏗️ Arquitectura

```
Educonnect-Ruben/
├── backend/                  # FastAPI + PostgreSQL
│   ├── main.py               # Entry point + CORS + rutas
│   ├── database.py           # Conexión PostgreSQL
│   ├── security.py           # JWT + bcrypt
│   ├── seed_modulos.py       # Carga malla curricular completa
│   └── routes/
│       ├── auth.py           # Login, registro, usuarios
│       ├── modulos.py        # Módulos y contenidos
│       └── evaluaciones.py   # Evaluaciones
├── frontend/
│   ├── index.html            # Página pública (malla curricular)
│   ├── login.html            # Login universal
│   ├── js/api.js             # Configuración API
│   ├── admin/dashboard.html  # Panel Administrador
│   ├── profesor/dashboard.html # Panel Profesor
│   └── student/dashboard.html  # Panel Estudiante
└── requirements.txt
```

---

## 👥 Roles del Sistema

### 🔑 Administrador
- Registra profesores y estudiantes (manual o Excel masivo)
- Asigna niveles y semestres
- Ve estadísticas generales: total inscritos, por nivel
- Elimina usuarios

### 👨‍🏫 Profesor
- Ve sus módulos asignados por semestre
- Publica materiales por Tema (5 temas × 5 tipos):
  - 📄 Teoría | 📊 PPT | 🎥 Video | 🎵 Audio | 📝 Evaluación
- Puede pegar links externos o adjuntar archivos

### 🎓 Estudiante
- Accede a su nivel/semestre asignado
- Navega por semestres con pestañas
- Abre cada módulo y ve el material de cada tema

---

## 📐 Malla Curricular (10 Semestres)

| Nivel | Semestres |
|---|---|
| 🔰 Básico | 1er Semestre |
| ⚙️ Auxiliar | 2do Semestre |
| 📚 Medio | 3ro y 4to Semestre |
| 🚀 Superior | 5to y 6to Semestre |
| 🏗️ Ingeniería | 7mo, 8vo, 9no y 10mo Semestre |

- **5 Módulos** por semestre
- **5 Temas** por módulo
- **5 Tipos de material** por tema

---

## 🔐 Sistema de Acceso

| Dato | Valor |
|---|---|
| **Email** | `nombre.apellido@educonnect.com` (generado automáticamente) |
| **Contraseña inicial** | Número de Carnet del usuario |
| **Carga masiva** | Excel (.xlsx) con columnas: Nombre, Apellido, Carnet |

---

## 🚀 Stack Tecnológico

| Capa | Tecnología |
|---|---|
| **Backend** | Python 3.11 + FastAPI |
| **Base de Datos** | PostgreSQL (Railway) |
| **Autenticación** | JWT + bcrypt |
| **Frontend** | HTML5 + CSS3 + JavaScript Vanilla |
| **Deploy** | Railway (backend) + GitHub Pages (frontend) |
| **Excel** | openpyxl |

---

## ⚙️ Variables de Entorno (Railway)

```env
DATABASE_URL=postgresql://...
SECRET_KEY=tu_clave_secreta
ALGORITHM=HS256
```

---

## 📦 Instalación Local

```bash
# 1. Clonar repositorio
git clone https://github.com/condorirubenlazofutbol/Educonnect-Ruben.git
cd Educonnect-Ruben

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env  # Editar con tus datos

# 4. Iniciar servidor
cd backend
uvicorn main:app --reload

# 5. Cargar malla curricular
python seed_modulos.py
```

---

## 🔄 Endpoints Principales

```
POST   /auth/login                    → Login (devuelve JWT)
POST   /auth/register-profesor        → Crear profesor
POST   /auth/register-estudiante      → Inscribir estudiante
POST   /auth/bulk-register            → Carga masiva Excel
GET    /auth/profesores               → Lista profesores
GET    /auth/estudiantes              → Lista estudiantes
DELETE /auth/usuarios/{id}            → Eliminar usuario

GET    /modulos/                      → Listar módulos
GET    /modulos/{id}/contenidos       → Ver materiales de un módulo
POST   /modulos/contenido             → Publicar material (profesor)

GET    /cargar-datos                  → Inicializar/resetear malla
```

---

## 📈 Próximas Mejoras Sugeridas

- [ ] Sistema de calificaciones y notas
- [ ] Cambio de contraseña desde el panel del usuario
- [ ] Notificaciones de nuevo material
- [ ] Foro o chat por módulo
- [ ] App móvil nativa (React Native)
- [ ] Reporte de progreso del estudiante en PDF
- [ ] Autenticación con Google

---

## 👨‍💻 Desarrollado por

**Ruben Lazo** – EduConnect Ruben  
Potenciado por **Antigravity AI**

---

*Versión 16.0 – Abril 2026*
