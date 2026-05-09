# 📚 Guía Completa de la Plataforma EduConnect CEA

Esta guía detalla la funcionalidad de cada módulo de la plataforma y proporciona las estructuras exactas (plantillas) que debes usar en tus archivos de Excel (`.xlsx`) para realizar importaciones masivas.

---

## 🏗️ 1. Funcionalidad de los Subsistemas

La plataforma está dividida en un Portal Principal y varios Subsistemas, diseñados para diferentes roles institucionales:

| Subsistema | Rol Principal | Funcionalidad Clave |
| :--- | :--- | :--- |
| **Portal Central** | Todos | Menú principal de acceso. Aquí los usuarios inician sesión y son redirigidos automáticamente al subsistema que les corresponde según su rol (Estudiante, Docente, Director, etc). |
| **Director** | Director | Panel de KPI's (Estadísticas), gráficos de aprobación. **Directorio Institucional Pro** para ver, buscar y eliminar estudiantes/docentes por área, carrera o nivel, y exportación a Excel de toda la base de datos. |
| **Secretaría** | Secretaria/o | Inscripción masiva de estudiantes y docentes mediante Excel. Generación automática de correos institucionales. Control de datos básicos. |
| **Jefe de Carrera** | Jefe de Carrera | Gestión de **Malla Curricular**. Creación de módulos por nivel (Básico, Auxiliar, Medio) y subida masiva de mallas vía Excel. |
| **Docente (Profesor)** | Docente | Gestión de notas, cuadro de calificaciones, registro de asistencia diaria y carga de recursos a la biblioteca. |
| **Estudiante** | Estudiante | Visualización de Kardex, notas, horarios, certificados ganados y acceso a biblioteca/evaluaciones. |
| **Elecciones** | Votantes/Admin | Sistema de votación electrónica. Autenticación rápida solo con CI para estudiantes. Carga de candidatos y votantes masivamente vía Excel por la secretaría. |

---

## 📊 2. Plantillas de Excel para Pruebas

Para que el sistema procese correctamente tus archivos Excel, **debes respetar exactamente el orden de las columnas**. Puedes copiar las siguientes tablas y pegarlas directamente en Excel. 

> [!IMPORTANT]
> - Asegúrate de guardar los archivos con extensión **`.xlsx`**.
> - La primera fila **siempre** debe ser el encabezado (título de las columnas). El sistema empieza a leer desde la segunda fila.

### 📝 A. Plantilla de Inscripción (Estudiantes / Docentes)
Esta plantilla se utiliza en el panel de **Secretaría** para registrar masivamente. El correo se genera solo (`nombreapellido@ceapailon.com`) y la contraseña por defecto es su número de CI.

| Nombre | Apellido | Carnet |
| :--- | :--- | :--- |
| Juan Carlos | Perez Lopez | 1234567 |
| Maria Elena | Gomez Sanchez | 7654321 |
| Roberto | Fernandez | 8888888 |

### 📚 B. Plantilla de Malla Curricular
Esta plantilla se utiliza en el panel del **Jefe de Carrera** para cargar las materias de una carrera automáticamente de un solo golpe.

| Nivel | Nombre del Módulo |
| :--- | :--- |
| Nivel Básico | Ofimática Básica |
| Nivel Básico | Sistemas Operativos |
| Nivel Auxiliar | Diseño Gráfico I |
| Nivel Medio I | Programación Web I |
| Nivel Medio II | Bases de Datos Avanzadas |

### 🗳️ C. Plantilla de Votantes (Elecciones)
Esta plantilla se utiliza en el panel de **Admin de Elecciones** o Secretaría para cargar el padrón electoral habilitado para votar.

| CI | Nombres | Apellidos |
| :--- | :--- | :--- |
| 1234567 | Juan Carlos | Perez Lopez |
| 7654321 | Maria Elena | Gomez Sanchez |
| 8888888 | Roberto | Fernandez |
| 9999999 | Ana Rosa | Martinez |

---

## 🎓 3. Sistema de Certificados y Constancias

El sistema maneja certificaciones de manera automatizada:
- **Certificados de Módulo:** Se generan automáticamente cuando un estudiante aprueba un módulo (supera la nota mínima configurada, generalmente 61). El estudiante puede descargarlo desde su portal.
- **Constancias de Estudio:** Documentos que acreditan que el estudiante está inscrito activamente en la institución.
- **Validez (QR):** Todos los certificados incluyen un código QR único que puede escanearse con el celular y dirige a una vista pública de verificación (pestaña `verificar.html`) para comprobar la autenticidad del documento. No se necesitan plantillas Excel para los certificados, ya que el diseño es renderizado internamente con HTML/CSS.

---
## 🚀 Cómo hacer tus pruebas paso a paso:

1. **Abre Excel** y copia los datos de las tablas de arriba.
2. Guarda el archivo (ej. `malla_sistemas.xlsx`).
3. Entra a la plataforma e **inicia sesión** (como Secretaria o Jefe de Carrera).
4. Ve al botón de **"Subir Excel"** y selecciona tu archivo.
5. El sistema procesará los datos y te mostrará un mensaje de éxito con la cantidad de registros importados.
