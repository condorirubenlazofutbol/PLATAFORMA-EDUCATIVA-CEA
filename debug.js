const puppeteer = require('puppeteer');

(async () => {
    console.log("Launching browser...");
    const browser = await puppeteer.launch({ headless: 'new' });
    const page = await browser.newPage();
    
    // Catch console logs from the page
    page.on('console', msg => console.log('PAGE LOG:', msg.text()));
    page.on('pageerror', err => console.log('PAGE ERROR:', err));

    console.log("Navigating to local page...");
    await page.goto('http://localhost:8080/subsistema_academico/secretaria/index.html', { waitUntil: 'networkidle0' });

    console.log("Setting localStorage...");
    await page.evaluate(() => {
        localStorage.setItem('token', 'fake-token');
        localStorage.setItem('user', JSON.stringify({ nombre: 'Test', rol: 'secretaria' }));
    });

    console.log("Reloading...");
    await page.reload({ waitUntil: 'networkidle0' });

    console.log("Clicking Inscripciones...");
    await page.evaluate(() => {
        const items = document.querySelectorAll('.nav-item');
        for (let item of items) {
            if (item.textContent.includes('Inscripciones')) {
                item.click();
                console.log("Clicked:", item.textContent);
            }
        }
    });

    // Check if the tab changed
    const isDashboardVisible = await page.evaluate(() => {
        const dashboard = document.getElementById('tab-dashboard');
        return dashboard ? window.getComputedStyle(dashboard).display !== 'none' : false;
    });

    const isInscripcionesVisible = await page.evaluate(() => {
        const panel = document.getElementById('tab-inscripciones');
        return panel ? window.getComputedStyle(panel).display !== 'none' : false;
    });

    console.log(`Dashboard visible: ${isDashboardVisible}`);
    console.log(`Inscripciones visible: ${isInscripcionesVisible}`);

    await browser.close();
})();
