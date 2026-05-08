// CEA Elecciones — API Client v5.0 (Local Backend)
const API_URL = "http://localhost:8000";

window.getApiUrl = () => API_URL;

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
    console.error("apiFetch Error:", err);
    const msg = err.name === "AbortError"
      ? "Tiempo de espera agotado. ¿Está el backend corriendo en localhost:8000?"
      : `Error de conexión: ${err.message}`;
    return { ok: false, status: 503, json: async () => ({ detail: msg }) };
  }
}

function cerrarSesion() {
  localStorage.removeItem("jwt_token");
  localStorage.removeItem("user_rol");
  const base = window.location.origin + window.location.pathname.split("/pages/")[0].split("/index.html")[0];
  window.location.href = base + "/index.html";
}

function redirigirPorRol(rol) {
  const base = window.location.origin +
    window.location.pathname.replace(/\/[^/]*$/, "").replace(/\/pages$/, "");
  if (rol === "admin") window.location.href = base + "/pages/dashboard-admin.html";
  else if (rol === "secretaria") window.location.href = base + "/pages/dashboard-secretaria.html";
  else if (rol === "jefe") window.location.href = base + "/pages/dashboard-jefe.html";
  else if (rol === "votante") window.location.href = base + "/pages/dashboard-votante.html";
  else window.location.href = base + "/index.html";
}
