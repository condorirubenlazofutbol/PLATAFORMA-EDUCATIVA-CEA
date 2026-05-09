/**
/**
 * EduConnect Pro – Configuración de API
 */
const API_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000'
    : 'https://educonnect-backend-ay2z.onrender.com';

// Alias para los módulos que usan API_BASE directamente
const API_BASE = API_URL;
