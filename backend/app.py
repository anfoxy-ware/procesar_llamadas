import pandas as pd
import io
import os
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Permite peticiones desde Netlify

def procesar_archivo_excel(archivo_bytes, nombre_archivo):
    """
    Procesa un solo archivo Excel (bytes) y devuelve un DataFrame
    con la unión de las hojas 'Llamadas' y 'LLamadas 6 segundos'
    siguiendo la lógica original del notebook.
    """
    try:
        # Leer ambas hojas
        hoja1 = pd.read_excel(archivo_bytes, sheet_name='Llamadas')
        hoja2 = pd.read_excel(archivo_bytes, sheet_name='LLamadas 6 segundos')
        
        # Filtrar columnas de hoja2 como en el original
        columnas_hoja2 = ['Nombre completo', 'Hora de inicio', 'Número de extensión',
                          'Duración', 'Tipo de llamada', 'Dígitos marcados', 'dia', 'Hora']
        # Solo conservar las que existen (por si acaso)
        columnas_existentes = [col for col in columnas_hoja2 if col in hoja2.columns]
        hoja2 = hoja2[columnas_existentes]
        
        # Agregar metadatos
        hoja1['Archivo'] = nombre_archivo
        hoja1['Hoja'] = 'Llamadas'
        hoja2['Archivo'] = nombre_archivo
        hoja2['Hoja'] = 'LLamadas 6 segundos'
        
        # Unir ambas hojas
        df_combinado = pd.concat([hoja1, hoja2], ignore_index=True)
        return df_combinado
    except Exception as e:
        # Si falla, devolvemos None y el error se capturará arriba
        raise Exception(f"Error en archivo {nombre_archivo}: {str(e)}")

@app.route('/procesar', methods=['POST'])
def procesar():
    """
    Recibe múltiples archivos Excel, los procesa uno por uno,
    aplica todas las transformaciones y devuelve un Excel final.
    """
    if 'archivos' not in request.files:
        return jsonify({'error': 'No se enviaron archivos'}), 400
    
    archivos = request.files.getlist('archivos')
    if len(archivos) == 0:
        return jsonify({'error': 'Lista de archivos vacía'}), 400
    
    dataframes_por_archivo = []
    
    for archivo in archivos:
        if not archivo.filename.endswith('.xlsx'):
            continue  # omitir si no es Excel
        try:
            # Leer bytes del archivo
            archivo_bytes = io.BytesIO(archivo.read())
            df_archivo = procesar_archivo_excel(archivo_bytes, archivo.filename)
            dataframes_por_archivo.append(df_archivo)
        except Exception as e:
            # Opcional: podrías registrar el error, pero seguimos con los demás
            print(str(e))
    
    if not dataframes_por_archivo:
        return jsonify({'error': 'No se pudo procesar ningún archivo válido'}), 400
    
    # Unir todos los DataFrames (como en el original)
    df_final = pd.concat(dataframes_por_archivo, ignore_index=True)
    
    # ---------- LIMPIEZA Y TRANSFORMACIONES (EXACTAMENTE IGUAL AL NOTEBOOK) ----------
    df_mod = df_final.copy()
    
    # Número de extensión: nulos a 0 y convertir a int
    df_mod['Número de extensión'] = df_mod['Número de extensión'].fillna(0).astype(int)
    
    # Hora de inicio a datetime
    df_mod['Hora de inicio'] = pd.to_datetime(df_mod['Hora de inicio'], errors='coerce')
    df_mod['Fecha'] = df_mod['Hora de inicio'].dt.date
    df_mod['Hora'] = df_mod['Hora de inicio'].dt.time
    
    # Duración: convertir a timedelta (asumiendo que viene en segundos)
    df_mod['Duración'] = pd.to_timedelta(df_mod['Duración'], errors='coerce', unit='s')
    
    # Columnas booleanas
    df_mod['Conectividad'] = df_mod['Duración'] > pd.Timedelta(seconds=6)
    df_mod['Efectividad'] = df_mod['Duración'] > pd.Timedelta(seconds=48)
    
    # ----- EXPORTAR A EXCEL EN MEMORIA -----
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_mod.to_excel(writer, index=False, sheet_name='Llamadas_Procesadas')
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='REGISTRO_LLAMADAS_PROCESADO.xlsx'
    )

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)