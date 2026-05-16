const XLSX = require('xlsx');
const fs = require('fs');
const path = require('path');

const destDir = path.join(__dirname, '..', 'DATA_TEST_CEA_VETERINARIA');
if (!fs.existsSync(destDir)) fs.mkdirSync(destDir, { recursive: true });

function saveExcel(data, filePath) {
    const ws = XLSX.utils.aoa_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Hoja 1");
    XLSX.writeFile(wb, filePath);
}

const header = [['Nombres', 'Apellidos', 'Carnet / CI']];
const names = ["Juan Carlos", "Maria Rene", "Pedro Luis", "Ana Belen", "Luis Fernando", "Sofia Isabel", "Carlos Eduardo", "Laura Beatriz", "Miguel Angel", "Elena Sofia", "Roberto Carlos", "Sandra Patricia", "Hugo Alberto", "Carmen Rosa", "Diego Andres", "Paula Andrea", "Andres Felipe", "Lucia Fernanda", "Fernando Jose", "Valeria Cristina", "Gustavo Adolfo", "Patricia Lorena", "Ricardo Daniel", "Susana Beatriz", "Oscar Manuel", "Silvia Elena", "Jorge Mario", "Rosa Maria", "Victor Hugo", "Claudia Ines"];
const lastNames = ["Gutierrez", "Mamani", "Quispe", "Flores", "Garcia", "Martinez", "Rodriguez", "Lopez", "Sanchez", "Perez", "Torres", "Vargas", "Rojas", "Castro", "Ruiz", "Morales", "Jimenez", "Herrera", "Medina", "Aguilar", "Mendoza", "Chavez", "Salazar", "Reyes", "Chavez", "Arias", "Pinto", "Guzman", "Suarez", "Ortiz"];

let nameIdx = 0;
let globalIdx = 1000;

function generatePerson() {
    const n = names[nameIdx % names.length];
    const l = lastNames[(nameIdx + 3) % lastNames.length] + " " + lastNames[(nameIdx + 9) % lastNames.length];
    const ci = 4500000 + globalIdx;
    nameIdx++;
    globalIdx++;
    return [n, l, ci.toString()];
}

const tecnicoCarreras = [
    { name: 'SISTEMAS INFORMATICOS', students: [45, 25, 25, 25] },
    { name: 'CONTABILIDAD', students: [30, 25, 25, 25] },
    { name: 'VETERINARIA', students: [45, 25, 25, 25] },
    { name: 'GASTRONOMIA', students: [40, 25, 25, 25] },
    { name: 'CONFECCION TEXTIL', students: [25, 25, 25, 25] },
    { name: 'PARVULARIA', students: [35, 25, 25, 25] },
    { name: 'FISIOTERAPIA', students: [45, 25, 25, 25] },
    { name: 'BELLEZA INTEGRAL', students: [25, 25, 25, 25] }
];

const tecnicoNiveles = ["BASICO", "AUXILIAR", "MEDIO I", "MEDIO II"];

tecnicoCarreras.forEach(carrera => {
    const cDir = path.join(destDir, carrera.name);
    if (!fs.existsSync(cDir)) fs.mkdirSync(cDir, { recursive: true });

    // 12 Docentes (3 por nivel para que sea ultra completo)
    const docData = [...header];
    for (let i = 0; i < 12; i++) {
        docData.push(generatePerson());
    }
    saveExcel(docData, path.join(cDir, `1. DOCENTES ${carrera.name}.xlsx`));

    // Estudiantes
    carrera.students.forEach((count, i) => {
        const niv = tecnicoNiveles[i];
        const fileName = `1.${i+1} ESTUDIANTES ${carrera.name} ${niv} A.xlsx`;
        saveExcel(Array.from({ length: count + 1 }, (_, idx) => idx === 0 ? header[0] : generatePerson()), path.join(cDir, fileName));
    });
});

// Humanística
const humDir = path.join(destDir, 'HUMANISTICA');
if (!fs.existsSync(humDir)) fs.mkdirSync(humDir, { recursive: true });

const humNiveles = ["ALFABETIZACION", "APLICADOS", "COMPLEMENTARIOS", "ESPECIALIZADOS"];
const humStudents = [25, 45, 25, 25];

// Docentes por materia (6 por materia para cubrir todos los paralelos)
const subjects = [
    { name: 'MATEMATICA', count: 6 },
    { name: 'LENGUAJE', count: 6 },
    { name: 'CIENCIAS NATURALES', count: 5 },
    { name: 'CIENCIAS SOCIALES', count: 5 }
];

subjects.forEach(sub => {
    const data = [...header];
    for (let i = 0; i < sub.count; i++) {
        data.push(generatePerson());
    }
    const subNum = sub.name === 'MATEMATICA' ? '1' : sub.name === 'LENGUAJE' ? '2' : sub.name === 'CIENCIAS NATURALES' ? '3' : '4';
    saveExcel(data, path.join(humDir, `${subNum}. DOCENTES ${sub.name}.xlsx`));
});

// Estudiantes Humanística
humNiveles.forEach((niv, i) => {
    const count = humStudents[i];
    const fileName = `1.${i+1} ESTUDIANTES ${niv} A.xlsx`;
    saveExcel(Array.from({ length: count + 1 }, (_, idx) => idx === 0 ? header[0] : generatePerson()), path.join(humDir, fileName));
});

console.log('Carpeta VETERINARIA y el resto generadas con éxito.');
