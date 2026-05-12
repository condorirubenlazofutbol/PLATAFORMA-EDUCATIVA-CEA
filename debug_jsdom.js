const fs = require('fs');
const jsdom = require('jsdom');
const { JSDOM } = jsdom;

const html = fs.readFileSync('./frontend/subsistema_academico/secretaria/index.html', 'utf8');

const dom = new JSDOM(html, {
    runScripts: "dangerously",
    url: "http://localhost/",
    beforeParse(window) {
        // Mock localStorage and fetch
        window.localStorage = {
            getItem: (k) => {
                if (k === 'token') return 'fake-token';
                if (k === 'user') return JSON.stringify({ nombre: 'Test', rol: 'secretaria' });
                return null;
            },
            setItem: () => {}
        };
        window.fetch = async () => ({
            ok: true,
            json: async () => ({
                carreras: [],
                estudiantes: 10, profesores: 5, modulos: 3,
                usuarios: [], elecciones: [], inscritos: []
            })
        });
        // Mock SweetAlert
        window.Swal = { fire: () => {} };
        // Mock API_URL / API_BASE since api.js is not loaded normally in JSDOM due to external path
        window.API_URL = 'http://localhost';
        window.API_BASE = 'http://localhost';
        // Mock XLSX
        window.XLSX = { utils: {}, writeFile: () => {} };
    }
});

const window = dom.window;

// Listen for errors
window.addEventListener('error', event => {
    console.error('JSDOM Script Error:', event.error);
});
window.addEventListener('unhandledrejection', event => {
    console.error('JSDOM Unhandled Rejection:', event.reason);
});

setTimeout(() => {
    try {
        console.log("Calling showTab...");
        const navItem = window.document.querySelector('.nav-item'); // Get any nav item
        window.showTab('inscripciones', navItem);
        console.log("Called successfully.");
        
        const dash = window.document.getElementById('tab-dashboard');
        const ins = window.document.getElementById('tab-inscripciones');
        
        console.log("Dashboard visible?", dash.style.display !== 'none');
        console.log("Inscripciones visible?", ins.style.display !== 'none');
    } catch (e) {
        console.error("Error calling showTab:", e);
    }
}, 1000);
