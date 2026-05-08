# 🎓 PROYECTO FINAL - Sistemas Informáticos CEA

Este documento detalla la estructura del equipo, los roles desempeñados y la documentación técnica de los componentes desarrollados para la plataforma educativa del Centro de Educación Alternativa.

## 👥 Equipo de Desarrollo y Funciones

### 1. 🧠 Desarrollador Backend (API & Seguridad)
**Responsabilidades:**
- Arquitectura del servidor utilizando **FastAPI**.
- Implementación de seguridad mediante **JWT Tokens** y hash de contraseñas (SHA-256).
- Creación de endpoints para la gestión de usuarios, módulos, contenidos y calificaciones.
- Integración con base de datos **PostgreSQL** y gestión de migraciones de datos.

### 2. 🎨 Desarrollador Frontend (Interfaz & UX)
**Responsabilidades:**
- Diseño de interfaces dinámicas con **HTML5, CSS3 y Vanilla JavaScript**.
- Implementación de dashboards específicos para Administradores, Profesores y Estudiantes.
- Aplicación de diseño **Glassmorphism** y adaptabilidad (Responsive Design) para móviles.
- Lógica de comunicación con la API mediante peticiones asíncronas (`fetch`).

### 3. 🧪 Tester (Aseguramiento de Calidad)
**Responsabilidades:**
- Pruebas de funcionamiento de todos los endpoints de la API.
- Validación de la responsividad en múltiples dispositivos y navegadores.
- Identificación y corrección de errores en la carga de archivos estáticos.
- Pruebas de flujo de usuario completo (Registro -> Login -> Carga de Material -> Visualización).

### 4. 🚀 Especialista en Despliegue (DevOps)
**Responsabilidades:**
- Configuración y mantenimiento del entorno en **Railway**.
- Gestión de dominios personalizados (`modulos-cea-frontend` y `modulos-cea-backend`).
- Solución de problemas de enrutamiento y variables de entorno en producción.
- Configuración de la estrategia de "Root Directory" para separar servicios eficientemente.

### 5. ✍️ Documentador Técnico
**Responsabilidades:**
- Redacción de manuales de uso y guías de instalación.
- Documentación de la **Malla Curricular** oficial del CEA (20 módulos).
- Creación del archivo de escalamiento (`README.md`) y este resumen final.
- Comentado del código fuente para facilitar el mantenimiento futuro.

---

## 🏆 Resumen del Impacto
La plataforma **Sistemas Informáticos CEA** representa una solución tecnológica robusta que digitaliza por completo el seguimiento académico del instituto. Gracias al trabajo coordinado del equipo, se ha logrado un sistema estable, seguro y listo para ser utilizado por cientos de estudiantes.

---
*Este proyecto ha sido desarrollado como parte del programa de Sistemas Informáticos - 2024.*
