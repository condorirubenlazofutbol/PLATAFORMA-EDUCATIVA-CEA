const API = 'https://educonnect-backend-ay2z.onrender.com';

async function waitForDeploy(token, maxWaitMs = 300000) {
    const start = Date.now();
    while (Date.now() - start < maxWaitMs) {
        const res = await fetch(`${API}/estadisticas/purgar-carreras-invalidas`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const text = await res.text();
        console.log(`[${new Date().toLocaleTimeString()}] ${res.status}: ${text}`);
        
        if (res.status !== 404 || text.includes('purgar') || text.includes('eliminadas')) {
            return { ok: res.ok, status: res.status, text };
        }
        // Still old code — wait 30s and retry
        console.log("Deploy not ready yet, waiting 30s...");
        await new Promise(r => setTimeout(r, 30000));
    }
    return null;
}

async function run() {
    console.log("Logging in...");
    const loginRes = await fetch(`${API}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'username=ruben.director@educonnect.com&password=1234567'
    });
    const loginData = await loginRes.json();
    const token = loginData.access_token;
    if (!token) { console.error("No token", loginData); return; }
    console.log("Logged in. Waiting for Render deploy...");

    const result = await waitForDeploy(token);
    if (!result) { console.error("Timeout waiting for deploy"); return; }
    
    console.log("\nFinal carrera list:");
    const carrerasRes = await fetch(`${API}/malla/carreras`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await carrerasRes.json();
    (data.carreras || []).forEach(c => console.log(`  [${c.id}] ${c.nombre} (${c.area})`));
}

run();
