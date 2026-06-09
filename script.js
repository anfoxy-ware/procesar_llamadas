// Configura la URL de tu backend en Render (cámbiala cuando despliegues)
const API_URL = 'https://procesar-llamadas.onrender.com/procesar';

// Elementos del DOM
const fileInput = document.getElementById('fileInput');
const fileListDiv = document.getElementById('fileList');
const processBtn = document.getElementById('processBtn');
const statusDiv = document.getElementById('status');

let selectedFiles = [];

fileInput.addEventListener('change', (e) => {
    selectedFiles = Array.from(e.target.files);
    renderFileList();
    processBtn.disabled = selectedFiles.length === 0;
});

function renderFileList() {
    if (selectedFiles.length === 0) {
        fileListDiv.innerHTML = '<em>No hay archivos seleccionados</em>';
        return;
    }
    const html = selectedFiles.map(file => `
        <div class="file-item">
            <span>📄 ${file.name}</span>
            <span>${(file.size / 1024).toFixed(1)} KB</span>
        </div>
    `).join('');
    fileListDiv.innerHTML = html;
}

processBtn.addEventListener('click', async () => {
    if (selectedFiles.length === 0) return;

    statusDiv.innerHTML = '⏳ Subiendo y procesando archivos... (puede tomar unos segundos)';
    processBtn.disabled = true;

    const formData = new FormData();
    selectedFiles.forEach(file => {
        formData.append('archivos', file);
    });

    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Error en el servidor');
        }

        // Descargar el archivo Excel resultante
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'REGISTRO_LLAMADAS_PROCESADO.xlsx';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        statusDiv.innerHTML = '✅ ¡Procesado correctamente! Se ha descargado el archivo.';
    } catch (error) {
        console.error(error);
        statusDiv.innerHTML = `❌ Error: ${error.message}`;
    } finally {
        processBtn.disabled = false;
        // Opcional: limpiar selección
        // fileInput.value = '';
        // selectedFiles = [];
        // renderFileList();
    }
});