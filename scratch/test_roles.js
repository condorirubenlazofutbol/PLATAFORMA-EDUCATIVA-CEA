const API = 'https://educonnect-backend-ay2z.onrender.com';

async function test(email, pass) {
    try {
        const r = await fetch(API + '/auth/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: 'username=' + encodeURIComponent(email) + '&password=' + encodeURIComponent(pass)
        });
        const d = await r.json();
        if (!d.access_token) {
            console.log(email, '=> LOGIN FAIL:', JSON.stringify(d));
            return;
        }
        console.log(email, '=> rol en token:', d.rol);

        // Test promover-jefe endpoint
        const r2 = await fetch(API + '/auth/promover-jefe-carrera', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + d.access_token},
            body: JSON.stringify({usuario_id: 999, especialidad_nombre: 'Test'})
        });
        const d2 = await r2.json();
        console.log('  -> jefe endpoint:', r2.status, d2.detail || d2.mensaje || JSON.stringify(d2));
    } catch(e) {
        console.log(email, '=> ERROR:', e.message);
    }
}

async function main() {
    await test('ruben.director@educonnect.com', '1234567');
    await test('ruben.admin@educonnect.com', 'admin123');
    await test('ruben.secretaria@educonnect.com', '1234567');
}
main();
