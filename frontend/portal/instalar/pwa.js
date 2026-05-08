// Configuración del botón de instalación
const installButton = document.createElement('button');
installButton.id = 'pwa-install-button';
installButton.textContent = 'Instalar App';
Object.assign(installButton.style, {
  position: 'fixed',
  bottom: '20px', // <--- ¡PARA EL BOTON DE INSTALAR ESTE ARRIBA!
  right: '20px',
  padding: '10px 20px',
  backgroundColor: '#3367D6',
  color: 'white',
  border: 'none',
  borderRadius: '5px',
  fontSize: '16px',
  cursor: 'pointer',
  display: 'none',
  zIndex: '1000'
});
document.body.appendChild(installButton);

// Manejo del evento de instalación
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
  console.log('[PWA] Evento beforeinstallprompt recibido');
  
  // 1. Prevenir el banner automático
  e.preventDefault();
  
  // 2. Guardar el evento para usarlo luego
  deferredPrompt = e;
  
  // 3. Mostrar NUESTRO botón de instalación
  installButton.style.display = 'block';
  
  // 4. Opcional: Ocultar después de 30 segundos
  setTimeout(() => {
    if (installButton.style.display === 'block') {
      installButton.style.display = 'none';
    }
  }, 30000);
});

// Manejo del clic en nuestro botón
installButton.addEventListener('click', async () => {
  if (!deferredPrompt) return;
  
  console.log('[PWA] Mostrando diálogo de instalación');
  
  try {
    // Mostrar el prompt de instalación
    deferredPrompt.prompt();
    
    // Esperar a que el usuario decida
    const { outcome } = await deferredPrompt.userChoice;
    
    console.log(`[PWA] Usuario ${outcome === 'accepted' ? 'aceptó' : 'rechazó'} la instalación`);
    
    if (outcome === 'accepted') {
      installButton.textContent = '✓ ¡Instalada!';
      setTimeout(() => {
        installButton.style.display = 'none';
      }, 2000);
    }
  } catch (error) {
    console.error('[PWA] Error al mostrar el prompt:', error);
  } finally {
    deferredPrompt = null;
    installButton.style.display = 'none';
  }
});

// Registro del Service Worker (sin cambios)
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/instalar/sw.js')
      .then(registration => {
        console.log('[PWA] Service Worker registrado con éxito:', registration.scope);
      })
      .catch(error => {
        console.error('[PWA] Error al registrar Service Worker:', error);
      });
  });
}

// Detección de iOS (para mostrar instrucciones especiales)
if (/iPad|iPhone|iPod/.test(navigator.userAgent) || 
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)) {
  const iosBanner = document.createElement('div');
  iosBanner.innerHTML = `
    <div style="
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      padding: 12px;
      background: #f8f9fa;
      text-align: center;
      border-top: 1px solid #ddd;
      z-index: 999;
    ">
      <p style="margin: 0;">📱 Para instalar: Toca <strong>Compartir</strong> → <strong>Añadir a Inicio</strong></p>
    </div>
  `;
  document.body.appendChild(iosBanner);
}
