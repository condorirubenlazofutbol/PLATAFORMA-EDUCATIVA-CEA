const API = 'https://educonnect-backend-ay2z.onrender.com';

async function run() {
    // Login as director
    const login = await fetch(`${API}/auth/login`, {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: 'username=rubencondori%40ceapailon.com&password=1234567'
    });
    let loginData = await login.json();
    
    // Try other emails
    if (!loginData.access_token) {
        const login2 = await fetch(`${API}/auth/login`, {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: 'username=ruben.director%40educonnect.com&password=1234567'
        });
        loginData = await login2.json();
    }
    
    if (!loginData.access_token) {
        console.log("No login:", JSON.stringify(loginData));
        return;
    }
    
    console.log("Rol en login response:", loginData.rol);
    const token = loginData.access_token;
    
    // Decode JWT payload
    const parts = token.split('.');
    const payload = JSON.parse(Buffer.from(parts[1], 'base64').toString());
    console.log("JWT payload sub:", payload.sub);
    
    // Get users list
    const users = await fetch(`${API}/auth/usuarios`, {
        headers: {Authorization: `Bearer ${token}`}
    });
    const usersData = await users.json();
    
    if (Array.isArray(usersData)) {
        const directors = usersData.filter(u => ['director','administrador','admin'].includes(u.rol));
        console.log("Directors/admins in DB:");
        directors.forEach(u => console.log(`  [${u.rol}] ${u.nombre} ${u.apellido} - ${u.email}`));
    } else {
        console.log("Users response:", JSON.stringify(usersData).slice(0, 500));
    }
    
    // Test the jefe endpoint directly
    const testJefe = await fetch(`${API}/auth/promover-jefe-carrera`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json', Authorization: `Bearer ${token}`},
        body: JSON.stringify({usuario_id: 999999, especialidad_nombre: "TEST"})
    });
    const jefeResp = await testJefe.json();
    console.log("\nJefe endpoint test (expect 404/500, not 403):", testJefe.status, JSON.stringify(jefeResp));
}
run();
