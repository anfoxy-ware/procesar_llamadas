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
    
    # 1. Usamos una lista para acumular DataFrames en lugar de escribir al Excel en cada vuelta este funciona 100% real
    dfs_procesados = []
    
    for i, archivo in enumerate(archivos):
        if not archivo.filename.endswith('.xlsx'):
            continue
        try:
            print(f"⏳ Procesando matriz de archivo {i+1} de {len(archivos)}: {archivo.filename} ...")
            archivo_bytes = io.BytesIO(archivo.read())
            df = procesar_archivo_excel(archivo_bytes, archivo.filename)
            
            # Limpieza básica
            df['Número de extensión'] = df['Número de extensión'].fillna(0).astype(int)
            df['Hora de inicio'] = pd.to_datetime(df['Hora de inicio'], errors='coerce')
            df['Fecha'] = df['Hora de inicio'].dt.date
            df['Hora'] = df['Hora de inicio'].dt.time
            df['Duración'] = pd.to_timedelta(df['Duración'], errors='coerce', unit='s')
            df['Conectividad'] = df['Duración'] > pd.Timedelta(seconds=6)
            df['Efectividad'] = df['Duración'] > pd.Timedelta(seconds=48)
            
            # 2. Guardamos el DataFrame en la lista
            dfs_procesados.append(df)
            
        except Exception as e:
            # Log del error pero continuamos con los demás archivos
            print(f"Error con {archivo.filename}: {e}")
    
    # Verificamos si logramos extraer datos de algún archivo
    if not dfs_procesados:
        return jsonify({'error': 'No se pudo procesar ningún archivo válido'}), 400
    
    # 3. Concatenamos todo de un solo golpe (Pandas hace esto muy rápido y optimiza la memoria)
    df_final = pd.concat(dfs_procesados, ignore_index=True)
    
    # 4. Escribimos el Excel una sola vez
    output_buffer = io.BytesIO()
    with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
        df_final.to_excel(writer, index=False, sheet_name='Llamadas_Procesadas')
    
    # Liberamos el DataFrame gigante de la memoria
    del df_final
    del dfs_procesados
    
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