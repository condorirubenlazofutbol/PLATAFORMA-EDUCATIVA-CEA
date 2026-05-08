/* ═════════════════════════════════════════════
   EduConnect – Shared JavaScript  (app.js)
   ═════════════════════════════════════════════ */
const API = window.location.hostname === 'localhost'
    ? 'http://localhost:8000'
    : 'https://educonnect-backend-ay2z.onrender.com';

// Unify token: always use the portal's 'token' key
let token = localStorage.getItem('token');
let currentUser = JSON.parse(localStorage.getItem('user') || '{}');
// Normalise user fields from different portals
if (currentUser.nombre && !currentUser.first_name) currentUser.first_name = currentUser.nombre;
if (currentUser.rol && !currentUser.role)           currentUser.role = currentUser.rol;
/* ─── User UI Initialization ────────────────────────── */
function initUserUI() {
    const welcomeEl = document.getElementById('welcomeName');

    if (currentUser) {
        const name = currentUser.first_name || 'Usuario';
        const last = currentUser.last_name || '';
        const fullName = `${name} ${last}`.trim();

        if (welcomeEl) {
            welcomeEl.textContent = fullName;
        }
    }
}
document.addEventListener('DOMContentLoaded', () => {
    initUserUI();
});
/* ─── API Helper ─────────────────────────────────────── */
async function api(path, opts = {}) {
    const res = await fetch(API + path, {
        ...opts,
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
            ...(opts.headers || {})
        }
    });
    if (res.status === 401) { logout(); return null; }
    return res.json();
}
/* ─── Logout ─────────────────────────────────────────── */
function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = 'index.html';
}
/* ─── Custom Alert (replaces native alert()) ─────────── */
function showAlert(message, type = 'error', title = '') {
    // Remove any existing alert
    const existing = document.getElementById('customAlertOverlay');
    if (existing) existing.remove();
    const icons = { error: '⚠️', success: '✅', info: 'ℹ️', warning: '🔔' };
    const colors = { error: 'var(--red)', success: 'var(--green)', info: 'var(--blue)', warning: 'var(--yellow)' };
    const defaultTitles = { error: 'Error', success: '¡Éxito!', info: 'Información', warning: 'Atención' };
    const overlay = document.createElement('div');
    overlay.id = 'customAlertOverlay';
    overlay.className = 'alert-overlay';
    overlay.innerHTML = `
    <div class="alert-box">
      <div class="alert-icon">${icons[type] || icons.info}</div>
      <h3 style="color:${colors[type] || colors.info}">${title || defaultTitles[type]}</h3>
      <p>${message}</p>
      <button class="btn btn-primary" onclick="document.getElementById('customAlertOverlay').remove()">Entendido</button>
    </div>`;
    document.body.appendChild(overlay);
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
}
/* ─── Success Banner (for major actions) ─────────────── */
function showBanner(title, subtitle, extras = '') {
    const existing = document.getElementById('globalBanner');
    if (existing) existing.remove();
    const b = document.createElement('div');
    b.id = 'globalBanner';
    b.className = 'success-banner show';
    b.innerHTML = `
    <div style="color:var(--accent);font-size:1.4rem;margin-bottom:4px">✅</div>
    <strong style="color:var(--accent)">${title}</strong>
    <div style="font-size:.82rem;color:var(--muted);margin-top:4px">${subtitle}</div>
    ${extras ? `<div style="display:flex;gap:12px;justify-content:center;margin-top:8px;font-size:.8rem;color:var(--muted)">${extras}</div>` : ''}`;
    document.body.appendChild(b);
    setTimeout(() => b.remove(), 3500);
}
/* ─── Toast notification ─────────────────────────────── */
function showToast(message) {
    const existing = document.getElementById('globalToast');
    if (existing) existing.remove();
    const t = document.createElement('div');
    t.id = 'globalToast';
    t.className = 'toast show';
    t.textContent = message;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 2800);
}
/* ─── Profile Modal ──────────────────────────────────── */
function openProfileModal() {
    let overlay = document.getElementById('profileOverlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'profileOverlay';
        overlay.className = 'profile-overlay';
        overlay.innerHTML = `
      <div class="profile-box">
        <h3>👤 Mi Perfil</h3>
        <div style="background:rgba(255,255,255,0.05); padding:16px; border-radius:12px; margin-bottom:24px; border:1px solid var(--border);">
          <div style="font-size:1.1rem; font-weight:700; color:#fff; margin-bottom:4px;">${currentUser.first_name || ''} ${currentUser.last_name || ''}</div>
          <div style="display:flex; gap:8px; align-items:center;">
             <span style="background:var(--accent); color:#000; font-size:0.7rem; font-weight:800; padding:2px 8px; border-radius:4px; text-transform:uppercase;">${currentUser.role || 'Usuario'}</span>
             <span style="color:var(--text-muted); font-size:0.85rem;">CI: ${currentUser.carnet || '---'}</span>
          </div>
        </div>
        <h4 style="font-size:0.9rem; margin-bottom:12px; color:var(--text-muted); text-transform:uppercase; letter-spacing:1px;">Cambiar Contraseña</h4>
        <div class="form-group">
          <label>Contraseña Actual</label>
          <input type="password" id="pwOld" placeholder="Ingresa tu contraseña actual">
        </div>
        <div class="form-group">
          <label>Nueva Contraseña</label>
          <input type="password" id="pwNew" placeholder="Mínimo 6 caracteres">
        </div>
        <div class="form-group">
          <label>Confirmar Nueva Contraseña</label>
          <input type="password" id="pwConfirm" placeholder="Repite la nueva contraseña">
        </div>
        <button class="btn btn-primary" style="width:100%;margin-bottom:10px" onclick="changePassword()">🔒 Guardar Contraseña</button>
        <button class="btn" style="width:100%;background:var(--card2);color:var(--muted);" onclick="document.getElementById('profileOverlay').classList.remove('open')">Cancelar</button>
      </div>`;
        document.body.appendChild(overlay);
        overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.classList.remove('open'); });
    }
    overlay.classList.add('open');
}
async function changePassword() {
    const oldPw = document.getElementById('pwOld').value.trim();
    const newPw = document.getElementById('pwNew').value.trim();
    const confirm = document.getElementById('pwConfirm').value.trim();
    if (!oldPw || !newPw || !confirm) {
        showAlert('Por favor llena todos los campos.', 'warning');
        return;
    }
    if (newPw.length < 6) {
        showAlert('La nueva contraseña debe tener mínimo 6 caracteres.', 'warning');
        return;
    }
    if (newPw !== confirm) {
        showAlert('Las contraseñas no coinciden. Vuelve a intentarlo.', 'error');
        return;
    }
    const res = await api(`/api/users/${currentUser.id}/password`, {
        method: 'PUT',
        body: JSON.stringify({ old_password: oldPw, new_password: newPw })
    });
    if (res && res.message === 'Password updated') {
        document.getElementById('profileOverlay').classList.remove('open');
        showBanner('¡Contraseña Actualizada!', 'Tu nueva contraseña ya está activa.');
    } else {
        showAlert(res?.message || 'Error al cambiar contraseña. Verifica que escribiste bien la contraseña actual.', 'error');
    }
}
/* ─── Tab switching ──────────────────────────────────── */
function showTab(name, el) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('nav a').forEach(a => a.classList.remove('active'));
    const tabEl = document.getElementById('tab-' + name);
    if (tabEl) tabEl.classList.add('active');
    if (el) el.classList.add('active');
    // Auto-close sidebar on mobile after selecting a tab
    const sb = document.querySelector(".sidebar");
    const overlay = document.getElementById("sidebarOverlay");
    if (sb && sb.classList.contains("open")) {
        sb.classList.remove("open");
        if (overlay) overlay.classList.remove("open");
    }
}
/* ─── Message tab switching ──────────────────────────── */
function switchMsgTab(which) {
    const envEl = document.getElementById('msgHistoryEnviados');
    const recEl = document.getElementById('msgHistoryRecibidos');
    const btnEnv = document.getElementById('tabEnviados');
    const btnRec = document.getElementById('tabRecibidos');
    if (!envEl) return;
    if (which === 'enviados') {
        envEl.style.display = 'block'; recEl.style.display = 'none';
        btnEnv.style.background = 'var(--accent)'; btnEnv.style.color = '#fff';
        btnRec.style.background = 'rgba(255,255,255,.08)'; btnRec.style.color = 'var(--text)';
    } else {
        recEl.style.display = 'block'; envEl.style.display = 'none';
        btnRec.style.background = 'var(--accent)'; btnRec.style.color = '#fff';
        btnEnv.style.background = 'rgba(255,255,255,.08)'; btnEnv.style.color = 'var(--text)';
    }
}
/* ─── Announcement helpers ───────────────────────────── */
function formatLinks(text) {
    return (text || '').replace(/(https?:\/\/[^\s]+)/g, url =>
        `<br><a href="${url}" target="_blank"
      style="color:var(--accent);text-decoration:none;display:inline-flex;align-items:center;
             gap:6px;margin-top:8px;background:rgba(59,130,246,.1);padding:8px 12px;
             border-radius:6px;font-weight:600;">🔗 Abrir Enlace</a>`
    ).replace(/\n/g, '<br>');
}
function roleLabel(role) {
    const colors = { director: '#a78bfa', profesor: '#34d399', secretaria: '#60a5fa', estudiante: '#f59e0b' };
    const names = { director: '🏢 Director', profesor: '👨‍🏫 Profesor', secretaria: '💼 Secretaria', estudiante: '📚 Estudiante' };
    return `<span style="background:rgba(255,255,255,.07);color:${colors[role] || '#ccc'};
    padding:2px 8px;border-radius:20px;font-size:.72rem;font-weight:600;">${names[role] || role}</span>`;
}
function buildMsgCard(m, type) {
    const isOut = type === 'sent';
    const label = isOut
        ? `✉️ Para: <strong>${m.receiver || 'varios'}</strong>`
        : `👤 De: <strong>${m.sender}</strong> ${roleLabel(m.sender_role || '')}`;
    return `
    <div style="border-left:3px solid ${isOut ? 'var(--blue)' : 'var(--accent)'};
                padding:10px 14px;margin-bottom:12px;
                background:rgba(255,255,255,.03);border-radius:0 8px 8px 0;">
      <div style="display:flex;align-items:center;gap:8px;font-size:.78rem;color:var(--muted);margin-bottom:6px;">
        ${label}<span style="margin-left:auto">${m.date}</span>
      </div>
      <p style="font-size:.87rem;margin:0;line-height:1.5;">${formatLinks(m.message)}</p>
    </div>`;
}
function renderMsgHistory(sent, received) {
    const envEl = document.getElementById('msgHistoryEnviados');
    const recEl = document.getElementById('msgHistoryRecibidos');
    if (envEl) {
        envEl.innerHTML = (sent && sent.length)
            ? sent.map(m => buildMsgCard(m, 'sent')).join('')
            : '<p style="color:var(--muted);font-size:.85rem">Sin comunicados enviados.</p>';
    }
    if (recEl) {
        recEl.innerHTML = (received && received.length)
            ? received.map(m => buildMsgCard(m, 'recv')).join('')
            : '<p style="color:var(--muted);font-size:.85rem">No tienes comunicados recibidos.</p>';
    }
}
/* ─── Shared enviarAnuncio (with target_role select) ─── */
async function enviarAnuncio() {
    const msgText = document.getElementById('announcement').value.trim();
    const linkEl = document.getElementById('announcementLink');
    const linkText = linkEl ? linkEl.value.trim() : '';
    const targetEl = document.getElementById('announcementTarget');
    const target_role = targetEl ? targetEl.value : 'todos';
    if (!msgText) { showAlert('Escriba un mensaje antes de enviar.', 'warning'); return; }
    let finalMsg = msgText;
    if (linkText) finalMsg += `\nEnlace adjunto: ${linkText}`;
    const btn = document.getElementById('btnAnuncio');
    if (btn) { btn.innerHTML = '<span class="spinner"></span> Enviando...'; btn.disabled = true; }
    const res = await api('/api/announcement', {
        method: 'POST',
        body: JSON.stringify({ message: finalMsg, target_role })
    });
    if (btn) { btn.innerHTML = '📤 Enviar Anuncio'; btn.disabled = false; }
    if (res && res.count !== undefined) {
        showBanner('¡Anuncio Enviado!', `${res.message || 'Enviado correctamente.'}`);
        document.getElementById('announcement').value = '';
        if (linkEl) linkEl.value = '';
        if (typeof cargarDatos === 'function') cargarDatos();
        else if (typeof loadMessages === 'function') loadMessages();
    } else {
        showAlert(res?.message || 'Ocurrió un error al enviar el anuncio.', 'error');
    }
}

/* ─── Responsive Sidebar Toggle ───────────────────────── */
function toggleSidebar() {
    const sidebar = document.querySelector(".sidebar");
    const overlay = document.getElementById("sidebarOverlay");
    
    if (sidebar) {
        sidebar.classList.toggle("open");
    }
    const overlayRef = overlay || document.querySelector(".sidebar-overlay");
    if (overlayRef) {
        overlayRef.classList.toggle("open");
    }
}