const fs = require('fs');

const API = 'https://educonnect-backend-ay2z.onrender.com';

async function run() {
    console.log("Logging in...");
    const loginRes = await fetch(`${API}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'username=ruben.director@educonnect.com&password=1234567'
    });
    
    if (!loginRes.ok) {
        console.error("Login failed status", loginRes.status, await loginRes.text());
        return;
    }

    const loginData = await loginRes.json();
    const token = loginData.access_token;
    
    if (!token) {
        console.error("No token", loginData);
        return;
    }
    
    console.log("Logged in. Getting directory...");
    const dirRes = await fetch(`${API}/estadisticas/directorio-agrupado`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const dirData = await dirRes.json();
    
    const estudiantes = dirData.estudiantes || [];
    console.log(`Found ${estudiantes.length} estudiantes.`);
    
    let deletedCount = 0;
    
    console.log("Bulk deleting all students...");
    const delRes = await fetch(`${API}/estadisticas/eliminar-inscripciones`, {
        method: 'DELETE',
        headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify({ tipo: 'todos', rol: 'estudiante' })
    });
    const delData = await delRes.json();
    console.log("Bulk delete students result:", delData);
    
    console.log("Bulk deleting all docentes...");
    const delDocRes = await fetch(`${API}/estadisticas/eliminar-inscripciones`, {
        method: 'DELETE',
        headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify({ tipo: 'todos', rol: 'docente' })
    });
    const delDocData = await delDocRes.json();
    console.log("Bulk delete docentes result:", delDocData);

    console.log("Finished deleting.");
}

run();
