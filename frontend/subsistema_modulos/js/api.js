// CEA Módulos — API Client v6.0 Pro (SSO Unified)
const API_URL = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : 'https://educonnect-backend-ay2z.onrender.com';

async function apiFetch(endpoint, options = {}) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000);
  try {
    const headers = {};
    // Use the unified portal token key
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
    const msg = err.name === "AbortError"
      ? "Tiempo de espera agotado. El servidor puede estar despertando (Render). Espera 30s e intenta de nuevo."
      : `Error de conexión: ${err.message}`;
    return { ok: false, status: 503, json: async () => ({ detail: msg }) };
  }
}

function cerrarSesion() {
  localStorage.removeItem("token");
  localStorage.removeItem("jwt_token");
  localStorage.removeItem("user");
  localStorage.removeItem("user_rol");
  window.location.href = "../login.html";
}
