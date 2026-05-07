/**
 * EduConnect Pro – Configuración de API
 * Detecta automáticamente si estás en local o producción.
 * En producción, usa la URL de Railway.
 * En local, apunta a localhost:8000.
 */
const API_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000'
    : 'https://educonnect-backend-production-1d08.up.railway.app';

// Alias para los módulos que usan API_BASE directamente
const API_BASE = API_URL;
