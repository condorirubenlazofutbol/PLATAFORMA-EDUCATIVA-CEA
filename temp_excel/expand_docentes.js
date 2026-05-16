const XLSX = require('xlsx');
const fs = require('fs');
const path = require('path');

const baseDir = path.join(__dirname, '..', 'DATA_TEST_CEA');
if (!fs.existsSync(baseDir)) fs.mkdirSync(baseDir, { recursive: true });

function saveExcel(data, filePath) {
    const ws = XLSX.utils.aoa_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Hoja 1");
    XLSX.writeFile(wb, filePath);
}

const header = [['Nombres', 'Apellidos', 'Carnet / CI']];

const tecnicoCarreras = [
    'SISTEMAS INFORMATICOS', 'CONTABILIDAD', 'SECRETARIADO EJECUTIVO', 
    'GASTRONOMIA', 'CONFECCION TEXTIL', 'PARVULARIA', 'FISIOTERAPIA', 'BELLEZA INTEGRAL'
];

let globalIdx = 500;

tecnicoCarreras.forEach(carrera => {
    const cDir = path.join(baseDir, carrera);
    if (!fs.existsSync(cDir)) fs.mkdirSync(cDir, { recursive: true });

    // Generar 8 docentes por carrera para que alcancen para todos los paralelos
    const docData = [...header];
    const niveles = ["BASICO", "AUXILIAR", "MEDIO I", "MEDIO II"];
    
    niveles.forEach(niv => {
        // 2 docentes por nivel para tener "de sobra"
        for (let i = 1; i <= 2; i++) {
            const ci = 5000000 + globalIdx;
            docData.push([`Prof ${niv} ${i}`, `${carrera}`, ci.toString()]);
            globalIdx++;
        }
    });
    saveExcel(docData, path.join(cDir, `1. DOCENTES ${carrera}.xlsx`));
});

// Humanística con más docentes por materia
const humDir = path.join(baseDir, 'HUMANISTICA');
if (!fs.existsSync(humDir)) fs.mkdirSync(humDir, { recursive: true });

const subjects = [
    { name: 'MATEMATICA', count: 4 },
    { name: 'LENGUAJE', count: 4 },
    { name: 'CIENCIAS NATURALES', count: 3 },
    { name: 'CIENCIAS SOCIALES', count: 3 }
];

subjects.forEach(sub => {
    const data = [...header];
    for (let i = 1; i <= sub.count; i++) {
        const ci = 6000000 + globalIdx;
        data.push([`Docente ${sub.name} ${i}`, `Area Humanistica`, ci.toString()]);
        globalIdx++;
    }
    saveExcel(data, path.join(humDir, `${sub.name === 'MATEMATICA' ? '1' : sub.name === 'LENGUAJE' ? '2' : sub.name === 'CIENCIAS NATURALES' ? '3' : '4'}. DOCENTES ${sub.name}.xlsx`));
});

console.log('Listas de docentes ampliadas con éxito para cubrir todos los paralelos.');
