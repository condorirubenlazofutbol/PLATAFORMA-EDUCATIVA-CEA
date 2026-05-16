const XLSX = require('xlsx');
const fs = require('fs');
const path = require('path');

const baseDir = path.join(__dirname, '..', 'DATA_TEST_CEA_COMPLETE');
if (!fs.existsSync(baseDir)) fs.mkdirSync(baseDir);

function generateStudents(count, startIdx = 0) {
    const data = [['Nombres', 'Apellidos', 'Carnet / CI']];
    const names = ["Juan", "Maria", "Pedro", "Ana", "Luis", "Sofia", "Carlos", "Laura", "Miguel", "Elena", "Roberto", "Sandra", "Hugo", "Carmen", "Diego", "Paula", "Andres", "Lucia", "Fernando", "Valeria"];
    const lastNames = ["Gomez", "Lopez", "Perez", "Rodriguez", "Sanchez", "Martinez", "Vargas", "Mamani", "Quispe", "Flores", "Gutierrez", "Torres", "Rojas", "Castro", "Morales", "Herrera", "Medina", "Aguilar", "Chavez", "Mendoza"];
    
    for (let i = 0; i < count; i++) {
        const n = names[Math.floor(Math.random() * names.length)];
        const l = lastNames[Math.floor(Math.random() * lastNames.length)] + " " + lastNames[Math.floor(Math.random() * lastNames.length)];
        const ci = 2000000 + startIdx + i;
        data.push([n, l, ci.toString()]);
    }
    return data;
}

function saveExcel(data, filePath) {
    const ws = XLSX.utils.aoa_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Hoja 1");
    XLSX.writeFile(wb, filePath);
}

const tecnicoCarreras = [
    { name: 'SISTEMAS INFORMATICOS', students: [45, 25, 25, 25] },
    { name: 'CONTABILIDAD', students: [30, 25, 25, 25] },
    { name: 'SECRETARIADO EJECUTIVO', students: [25, 25, 25, 25] },
    { name: 'GASTRONOMIA', students: [40, 25, 25, 25] },
    { name: 'CONFECCION TEXTIL', students: [25, 25, 25, 25] }
];

const tecnicoNiveles = ["BASICO", "AUXILIAR", "MEDIO I", "MEDIO II"];

let globalIdx = 0;

tecnicoCarreras.forEach(carrera => {
    const cDir = path.join(baseDir, carrera.name);
    if (!fs.existsSync(cDir)) fs.mkdirSync(cDir);

    // Docentes (uno por nivel)
    const docData = [['Nombres', 'Apellidos', 'Carnet / CI']];
    tecnicoNiveles.forEach((niv, i) => {
        const ci = 7000000 + globalIdx;
        docData.push([`Prof ${niv}`, `${carrera.name}`, ci.toString()]);
        globalIdx++;
    });
    saveExcel(docData, path.join(cDir, `1. DOCENTES ${carrera.name} CEA.xlsx`));

    // Estudiantes
    carrera.students.forEach((count, i) => {
        const niv = tecnicoNiveles[i];
        const fileName = `1.${i+1} ESTUDIANTES ${carrera.name} ${niv} A.xlsx`;
        saveExcel(generateStudents(count, globalIdx), path.join(cDir, fileName));
        globalIdx += count;
    });
});

// Humanística
const humDir = path.join(baseDir, 'HUMANISTICA');
if (!fs.existsSync(humDir)) fs.mkdirSync(humDir);

const humNiveles = ["APLICADOS", "COMPLEMENTARIOS", "ESPECIALIZADOS"];
const humStudents = [45, 25, 25];

// Docentes Humanística
const humDocData = [['Nombres', 'Apellidos', 'Carnet / CI']];
humNiveles.forEach(niv => {
    const ci = 8000000 + globalIdx;
    humDocData.push([`Prof ${niv}`, `Humanistica`, ci.toString()]);
    globalIdx++;
});
saveExcel(humDocData, path.join(humDir, `1. DOCENTES Humanistica CEA.xlsx`));

// Estudiantes Humanística
humNiveles.forEach((niv, i) => {
    const count = humStudents[i];
    const fileName = `1.${i+1} ESTUDIANTES ${niv} A.xlsx`;
    saveExcel(generateStudents(count, globalIdx), path.join(humDir, fileName));
    globalIdx += count;
});

console.log('Todos los archivos generados en ' + baseDir);
