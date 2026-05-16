const XLSX = require('xlsx');
const fs = require('fs');
const path = require('path');

const baseDir = path.join(__dirname, '..', 'DATA_TEST_CEA');
if (!fs.existsSync(baseDir)) fs.mkdirSync(baseDir);

function generateStudents(count, startIdx = 0) {
    const data = [['Nombres', 'Apellidos', 'Carnet / CI']];
    const names = ["Juan", "Maria", "Pedro", "Ana", "Luis", "Sofia", "Carlos", "Laura", "Miguel", "Elena"];
    const lastNames = ["Gomez", "Lopez", "Perez", "Rodriguez", "Sanches", "Martinez", "Vargas", "Mamani", "Quispe", "Flores"];
    
    for (let i = 0; i < count; i++) {
        const n = names[Math.floor(Math.random() * names.length)];
        const l = lastNames[Math.floor(Math.random() * lastNames.length)] + " " + lastNames[Math.floor(Math.random() * lastNames.length)];
        const ci = 1000000 + startIdx + i;
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

// Sistemas Informáticos
const sisDir = path.join(baseDir, 'SISTEMAS INFORMATICOS CEA');
if (!fs.existsSync(sisDir)) fs.mkdirSync(sisDir);

saveExcel([['Nombres', 'Apellidos', 'Carnet / CI'], ['Luis', 'Villarroel', '5566778'], ['Roberto', 'Camacho', '8899001']], path.join(sisDir, '1. DOCENTES Sistemas informaticos CEA.xlsx'));
saveExcel(generateStudents(45, 100), path.join(sisDir, '1.1 ESTUDIANTES Sistemas informaticos BASICO A.xlsx'));
saveExcel(generateStudents(45, 200), path.join(sisDir, '1.1 ESTUDIANTES Sistemas informaticos BASICO B.xlsx'));
saveExcel(generateStudents(25, 300), path.join(sisDir, '1.2 ESTUDIANTES Sistemas informaticos AUXILIAR A.xlsx'));
saveExcel(generateStudents(25, 400), path.join(sisDir, '1.3 ESTUDIANTES Sistemas informaticos MEDIO I-A.xlsx'));
saveExcel(generateStudents(25, 500), path.join(sisDir, '1.4 ESTUDIANTES Sistemas informaticos MEDIO II-A.xlsx'));

// Humanística
const humDir = path.join(baseDir, 'HUMANISTICA CEA');
if (!fs.existsSync(humDir)) fs.mkdirSync(humDir);

saveExcel([['Nombres', 'Apellidos', 'Carnet / CI'], ['Jesus', 'Mesias', '11223344'], ['Ana', 'Quiroga', '55667788']], path.join(humDir, '1. DOCENTES Humanistica CEA.xlsx'));
saveExcel(generateStudents(45, 1000), path.join(humDir, '1.1 ESTUDIANTES APLICADOS A.xlsx'));
saveExcel(generateStudents(25, 2000), path.join(humDir, '1.2 ESTUDIANTES COMPLEMENTARIOS A.xlsx'));
saveExcel(generateStudents(25, 3000), path.join(humDir, '1.3 ESTUDIANTES ESPECIALIZADOS A.xlsx'));

console.log('Archivos generados en ' + baseDir);
