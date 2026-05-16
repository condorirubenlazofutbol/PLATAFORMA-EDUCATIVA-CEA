const XLSX = require('xlsx');
const fs = require('fs');
const path = require('path');

const srcDir = path.join(__dirname, '..', 'DATA_TEST_CEA');
const destDir = path.join(__dirname, '..', 'DATA_TEST_CEA_REAL');

if (!fs.existsSync(destDir)) fs.mkdirSync(destDir, { recursive: true });

function saveExcel(data, filePath) {
    const ws = XLSX.utils.aoa_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Hoja 1");
    XLSX.writeFile(wb, filePath);
}

const header = [['Nombres', 'Apellidos', 'Carnet / CI']];
const names = ["Juan Carlos", "Maria Rene", "Pedro Luis", "Ana Belen", "Luis Fernando", "Sofia Isabel", "Carlos Eduardo", "Laura Beatriz", "Miguel Angel", "Elena Sofia", "Roberto Carlos", "Sandra Patricia", "Hugo Alberto", "Carmen Rosa", "Diego Andres", "Paula Andrea", "Andres Felipe", "Lucia Fernanda", "Fernando Jose", "Valeria Cristina", "Gustavo Adolfo", "Patricia Lorena", "Ricardo Daniel", "Susana Beatriz", "Oscar Manuel"];
const lastNames = ["Gutierrez", "Mamani", "Quispe", "Flores", "Garcia", "Martinez", "Rodriguez", "Lopez", "Sanchez", "Perez", "Torres", "Vargas", "Rojas", "Castro", "Ruiz", "Morales", "Jimenez", "Herrera", "Medina", "Aguilar", "Mendoza", "Chavez", "Salazar", "Reyes", "Chavez"];

let nameIdx = 0;
let globalIdx = 900;

function generatePerson() {
    const n = names[nameIdx % names.length];
    const l = lastNames[(nameIdx + 7) % lastNames.length] + " " + lastNames[(nameIdx + 15) % lastNames.length];
    const ci = 4000000 + globalIdx;
    nameIdx++;
    globalIdx++;
    return [n, l, ci.toString()];
}

// Copy Students and Create Teachers
const dirs = fs.readdirSync(srcDir, { withFileTypes: true }).filter(dirent => dirent.isDirectory());

dirs.forEach(dir => {
    const dName = dir.name;
    const sPath = path.join(srcDir, dName);
    const dPath = path.join(destDir, dName);
    if (!fs.existsSync(dPath)) fs.mkdirSync(dPath, { recursive: true });

    // Copy student files
    const files = fs.readdirSync(sPath);
    files.forEach(f => {
        if (f.includes('ESTUDIANTES')) {
            fs.copyFileSync(path.join(sPath, f), path.join(dPath, f));
        }
    });

    // Create realistic teachers
    const docData = [...header];
    for (let i = 0; i < 10; i++) {
        docData.push(generatePerson());
    }
    saveExcel(docData, path.join(dPath, `1. DOCENTES ${dName}.xlsx`));
});

// Humanística Subjects
const humDest = path.join(destDir, 'HUMANISTICA');
const subjects = [
    { name: 'MATEMATICA', count: 5 },
    { name: 'LENGUAJE', count: 5 },
    { name: 'CIENCIAS NATURALES', count: 4 },
    { name: 'CIENCIAS SOCIALES', count: 4 }
];

subjects.forEach(sub => {
    const data = [...header];
    for (let i = 0; i < sub.count; i++) {
        data.push(generatePerson());
    }
    const subNum = sub.name === 'MATEMATICA' ? '1' : sub.name === 'LENGUAJE' ? '2' : sub.name === 'CIENCIAS NATURALES' ? '3' : '4';
    saveExcel(data, path.join(humDest, `${subNum}. DOCENTES ${sub.name}.xlsx`));
});

console.log('Nueva carpeta DATA_TEST_CEA_REAL generada con nombres reales.');
