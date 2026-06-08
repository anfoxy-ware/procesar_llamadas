import pandas as pd
import io
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def procesar_archivo_excel(archivo_bytes, nombre_archivo):
    """Procesa un solo archivo y devuelve un DataFrame (sin acumular en lista)."""
    hoja1 = pd.read_excel(archivo_bytes, sheet_name='Llamadas')
    hoja2 = pd.read_excel(archivo_bytes, sheet_name='LLamadas 6 segundos')
    
    columnas_hoja2 = ['Nombre completo', 'Hora de inicio', 'Número de extensión',
                      'Duración', 'Tipo de llamada', 'Dígitos marcados', 'dia', 'Hora']
    columnas_existentes = [col for col in columnas_hoja2 if col in hoja2.columns]
    hoja2 = hoja2[columnas_existentes]
    
    hoja1['Archivo'] = nombre_archivo
    hoja1['Hoja'] = 'Llamadas'
    hoja2['Archivo'] = nombre_archivo
    hoja2['Hoja'] = 'LLamadas 6 segundos'
    
    df_combinado = pd.concat([hoja1, hoja2], ignore_index=True)
    return df_combinado

@app.route('/procesar', methods=['POST'])
def procesar():
    if 'archivos' not in request.files:
        return jsonify({'error': 'No se enviaron archivos'}), 400
    
    archivos = request.files.getlist('archivos')
    if len(archivos) == 0:
        return jsonify({'error': 'Lista de archivos vacía'}), 400
    
    # Usaremos un archivo temporal en disco (RAM) para no acumular todo en memoria
    output_buffer = io.BytesIO()
    # Escribimos el primer archivo (inicializamos el Excel)
    primer_archivo = True
    
    for archivo in archivos:
        if not archivo.filename.endswith('.xlsx'):
            continue
        try:
            archivo_bytes = io.BytesIO(archivo.read())
            df = procesar_archivo_excel(archivo_bytes, archivo.filename)
            
            # Limpieza básica necesaria antes de escribir (para evitar errores de tipos)
            df['Número de extensión'] = df['Número de extensión'].fillna(0).astype(int)
            df['Hora de inicio'] = pd.to_datetime(df['Hora de inicio'], errors='coerce')
            df['Fecha'] = df['Hora de inicio'].dt.date
            df['Hora'] = df['Hora de inicio'].dt.time
            df['Duración'] = pd.to_timedelta(df['Duración'], errors='coerce', unit='s')
            df['Conectividad'] = df['Duración'] > pd.Timedelta(seconds=6)
            df['Efectividad'] = df['Duración'] > pd.Timedelta(seconds=48)
            
            # Escribir en el buffer (si es el primer archivo, crea el Excel; si no, append)
            with pd.ExcelWriter(output_buffer, engine='openpyxl', mode='a' if not primer_archivo else 'w') as writer:
                df.to_excel(writer, index=False, sheet_name='Llamadas_Procesadas')
            
            primer_archivo = False
            
            # Liberar memoria del DataFrame y del buffer de lectura
            del df
            del archivo_bytes
            
        except Exception as e:
            # Log del error pero continuamos con los demás archivos
            print(f"Error con {archivo.filename}: {e}")
    
    if primer_archivo:
        return jsonify({'error': 'No se pudo procesar ningún archivo válido'}), 400
    
    output_buffer.seek(0)
    return send_file(
        output_buffer,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='REGISTRO_LLAMADAS_PROCESADO.xlsx'
    )

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)