// CEA Elecciones — API Client v5.0 (Unified with Platform)
const API_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000'
    : 'https://educonnect-backend-ay2z.onrender.com';

const apiUrl = API_URL; // alias de compatibilidad

window.getApiUrl = () => API_URL;

async function apiFetch(endpoint, options = {}) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000);
  try {
    const headers = {};
    // Unificado: usa 'token' igual que el resto de la plataforma
    const token = localStorage.getItem("token") || localStorage.getItem("jwt_token");
    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }
    options.headers = { ...headers, ...options.headers };
    options.signal = controller.signal;

    const res = await fetch(`${API_URL}${endpoint}`, options);
    clearTimeout(timeoutId);

    if (res.status === 401) { cerrarSesion(); return; }
    return res;
  } catch (err) {
    clearTimeout(timeoutId);
    console.error("apiFetch Error:", err);
    const msg = err.name === "AbortError"
      ? "Tiempo de espera agotado. Verifica tu conexión."
      : `Error de conexión: ${err.message}`;
    return { ok: false, status: 503, json: async () => ({ detail: msg }) };
  }
}

function cerrarSesion() {
  localStorage.removeItem("token");
  localStorage.removeItem("jwt_token");
  localStorage.removeItem("user");
  localStorage.removeItem("user_rol");
  window.location.href = "../../login.html";
}

function volverPortal() {
  window.location.href = "../../portal/index.html";
}

function redirigirPorRol(rol) {
  const isLocal = window.location.protocol === 'file:';
  let base = window.location.origin + window.location.pathname.replace(/\/[^/]*$/, "").replace(/\/pages$/, "");
  if (isLocal) {
      base = window.location.pathname.replace(/\/[^/]*$/, "").replace(/\/pages$/, "");
  }
  
  if (rol === "admin" || rol === "administrador" || rol === "director") {
      window.location.href = base + "/pages/dashboard-admin.html";
  } else if (rol === "secretaria") {
      window.location.href = base + "/pages/dashboard-secretaria.html";
  } else if (rol === "jefe" || rol === "jefe_carrera") {
      window.location.href = base + "/pages/dashboard-jefe.html";
  } else {
      window.location.href = base + "/pages/dashboard-votante.html";
  }
}
