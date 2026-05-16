const XLSX = require('xlsx');
const fs = require('fs');
const path = require('path');

const humDir = path.join(__dirname, '..', 'DATA_TEST_CEA', 'HUMANISTICA');
if (!fs.existsSync(humDir)) fs.mkdirSync(humDir, { recursive: true });

function saveExcel(data, filePath) {
    const ws = XLSX.utils.aoa_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Hoja 1");
    XLSX.writeFile(wb, filePath);
}

const header = [['Nombres', 'Apellidos', 'Carnet / CI']];

// 1. Matemáticas (2 docentes)
saveExcel([
    ...header,
    ['Jose', 'Cruz', '2536366'],
    ['Maria', 'Zabala', '4455667']
], path.join(humDir, '1. DOCENTES MATEMATICA.xlsx'));

// 2. Lenguaje (2 docentes)
saveExcel([
    ...header,
    ['Ana', 'Quiroga', '5566778'],
    ['Pedro', 'Mamani', '8899001']
], path.join(humDir, '2. DOCENTES LENGUAJE.xlsx'));

// 3. Ciencias Naturales (1 docente)
saveExcel([
    ...header,
    ['Victor', 'Pedraza', '1122334']
], path.join(humDir, '3. DOCENTES CIENCIAS NATURALES.xlsx'));

// 4. Ciencias Sociales (1 docente)
saveExcel([
    ...header,
    ['Rosa', 'Mendez', '9988776']
], path.join(humDir, '4. DOCENTES CIENCIAS SOCIALES.xlsx'));

// Eliminar el archivo general anterior para no confundir
const oldFile = path.join(humDir, '1. DOCENTES Humanistica CEA.xlsx');
if (fs.existsSync(oldFile)) fs.unlinkSync(oldFile);

console.log('Archivos de docentes por materia generados en HUMANISTICA');
