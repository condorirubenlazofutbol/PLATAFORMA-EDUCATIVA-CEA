const XLSX = require('xlsx');
const fs = require('fs');
const path = require('path');

const baseDir = path.join(__dirname, '..', 'DATA_TEST_CEA');

function saveExcel(data, filePath) {
    const ws = XLSX.utils.aoa_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Hoja 1");
    XLSX.writeFile(wb, filePath);
}

const header = [['Nombres', 'Apellidos', 'Carnet / CI']];

const names = ["Juan Carlos", "Maria Rene", "Pedro Luis", "Ana Belen", "Luis Fernando", "Sofia Isabel", "Carlos Eduardo", "Laura Beatriz", "Miguel Angel", "Elena Sofia", "Roberto Carlos", "Sandra Patricia", "Hugo Alberto", "Carmen Rosa", "Diego Andres", "Paula Andrea", "Andres Felipe", "Lucia Fernanda", "Fernando Jose", "Valeria Cristina"];
const lastNames = ["Gutierrez", "Mamani", "Quispe", "Flores", "Garcia", "Martinez", "Rodriguez", "Lopez", "Sanchez", "Perez", "Torres", "Vargas", "Rojas", "Castro", "Ruiz", "Morales", "Jimenez", "Herrera", "Medina", "Aguilar"];

let nameIdx = 0;
let globalIdx = 800;

function generatePerson() {
    const n = names[nameIdx % names.length];
    const l = lastNames[(nameIdx + 5) % lastNames.length] + " " + lastNames[(nameIdx + 12) % lastNames.length];
    const ci = 4000000 + globalIdx;
    nameIdx++;
    globalIdx++;
    return [n, l, ci.toString()];
}

const tecnicoCarreras = [
    'SISTEMAS INFORMATICOS', 'CONTABILIDAD', 'SECRETARIADO EJECUTIVO', 
    'GASTRONOMIA', 'CONFECCION TEXTIL', 'PARVULARIA', 'FISIOTERAPIA', 'BELLEZA INTEGRAL'
];

tecnicoCarreras.forEach(carrera => {
    const cDir = path.join(baseDir, carrera);
    if (!fs.existsSync(cDir)) fs.mkdirSync(cDir, { recursive: true });

    const docData = [...header];
    for (let i = 0; i < 8; i++) {
        docData.push(generatePerson());
    }
    saveExcel(docData, path.join(cDir, `1. DOCENTES ${carrera}.xlsx`));
});

// Humanística
const humDir = path.join(baseDir, 'HUMANISTICA');
const subjects = [
    { name: 'MATEMATICA', count: 4 },
    { name: 'LENGUAJE', count: 4 },
    { name: 'CIENCIAS NATURALES', count: 3 },
    { name: 'CIENCIAS SOCIALES', count: 3 }
];

subjects.forEach(sub => {
    const data = [...header];
    for (let i = 0; i < sub.count; i++) {
        data.push(generatePerson());
    }
    const subNum = sub.name === 'MATEMATICA' ? '1' : sub.name === 'LENGUAJE' ? '2' : sub.name === 'CIENCIAS NATURALES' ? '3' : '4';
    saveExcel(data, path.join(humDir, `${subNum}. DOCENTES ${sub.name}.xlsx`));
});

console.log('Docentes actualizados con nombres y apellidos reales.');
