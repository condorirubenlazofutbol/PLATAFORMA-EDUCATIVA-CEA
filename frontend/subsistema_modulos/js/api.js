// CEA Módulos — API Client v5.0 (Local Backend)
const API_URL = "http://localhost:8000";

async function apiFetch(endpoint, options = {}) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000);
  try {
    const headers = {};
    const token = localStorage.getItem("jwt_token");
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
      ? "Tiempo de espera agotado. ¿Está el backend corriendo en localhost:8000?"
      : `Error de conexión: ${err.message}`;
    return { ok: false, status: 503, json: async () => ({ detail: msg }) };
  }
}

function cerrarSesion() {
  localStorage.removeItem("jwt_token");
  localStorage.removeItem("user_rol");
  window.location.href = "../login.html";
}
