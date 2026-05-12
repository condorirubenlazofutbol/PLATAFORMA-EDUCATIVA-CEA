const fs = require('fs');
const jsdom = require('jsdom');
const { JSDOM } = jsdom;

const html = fs.readFileSync('./frontend/subsistema_academico/secretaria/index.html', 'utf8');

const dom = new JSDOM(html, {
    runScripts: "dangerously",
    url: "http://localhost/",
    beforeParse(window) {
        window.localStorage = {
            getItem: (k) => 'fake',
            setItem: () => {}
        };
        window.fetch = async () => ({
            ok: true,
            json: async () => ({
                registrados: 5, errores: []
            })
        });
        window.Swal = { 
            fire: () => Promise.resolve(),
            close: () => {},
            showLoading: () => {}
        };
        window.API_URL = 'http://localhost';
        window.API_BASE = 'http://localhost';
        window.XLSX = {};
    }
});

const window = dom.window;

setTimeout(async () => {
    try {
        const input = window.document.getElementById('excel-input');
        
        // Mock file
        const file = new window.File([''], 'test.xlsx', { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
        
        // Mock files array (since it's readonly, we use defineProperty)
        Object.defineProperty(input, 'files', {
            value: [file]
        });
        
        // Simulate first change
        console.log("First import...");
        await window.handleExcelImport(input);
        
        console.log("Input value after first import:", input.value);
        
        // Try to trigger again
        console.log("Second import...");
        await window.handleExcelImport(input);
        console.log("Input value after second import:", input.value);
        
    } catch (e) {
        console.error("Error:", e);
    }
}, 1000);
