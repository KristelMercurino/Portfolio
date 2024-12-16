import os
import sys
import json
import time
import requests
import pandas as pd
from tqdm import tqdm
from twilio.rest import Client

# ====================== Carga de Configuración ======================
# Cargar el archivo twilio_config_template.py
try:
    from twilio_config_template import API_KEY_WAPI, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, PHONE_NUMBER, TO_PHONE_NUMBER
except ImportError:
    raise ImportError("Error: No se pudo importar twilio_config_template.py. Asegúrate de configurarlo correctamente.")

# Verificar si las credenciales están configuradas
if not all([API_KEY_WAPI, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, PHONE_NUMBER, TO_PHONE_NUMBER]):
    raise ValueError("Error: Faltan credenciales en twilio_config_template.py. Configúralas antes de ejecutar el script.")

# ====================== Configuración del Clima ======================
# Aca la query del endpoint se arma en base a lo que puse que quería mostrar cuando cree la cuenta de weather api
query = "Santiago"
api_key = API_KEY_WAPI
# Endpoint
# http://api.weatherapi.com/v1/forecast.json?key=f3cf65ff7ae64bccad9210657220807&q=Bogotá&days=1&aqi=no&alerts=no
url_clima = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={query}&days=1&aqi=no&alerts=no"

# ====================== Funciones ======================
# Función que contiene todas las conversiones de los datos e itera uno por uno por las 24 horas 
# para mostrar al final todo esto por hora
def get_forecast(response, i):
    fecha = response['forecast']['forecastday'][0]['hour'][i]['time'].split()[0]
    hora = int(response['forecast']['forecastday'][0]['hour'][i]['time'].split()[1].split(':')[0])
    condicion = response['forecast']['forecastday'][0]['hour'][i]['condition']['text']
    tempe = response['forecast']['forecastday'][0]['hour'][i]['temp_c']
    rain = response['forecast']['forecastday'][0]['hour'][i]['will_it_rain']
    prob_rain = response['forecast']['forecastday'][0]['hour'][i]['chance_of_rain']
    return fecha, hora, condicion, tempe, rain, prob_rain

# Función para obtener el pronóstico por hora
def obtener_pronostico():
    # Haremos la petición con la librería request.get y esto lo convertimos en un json,
    # la respuesta del clima se guarda en json
    response = requests.get(url_clima).json()
    # tqdm es una libreria que sirve para mostrar una barra de progreso. El número de registros es 24 (24 horas)
    datos = [get_forecast(response, i) for i in tqdm(range(24), colour="green", desc="Procesando Pronóstico")]
    return pd.DataFrame(datos, columns=['Fecha', 'Hora', 'Tiempo', 'Temperatura', 'Lluvia', 'prob_lluvia'])

# Función para generar el mensaje SMS
def generar_mensaje(df):
    # Filtrar las filas donde está lloviendo y la hora está entre las 7 AM y las 9 PM
    df_rain = df[(df['Lluvia'] != 0) & (df['Hora'] > 6) & (df['Hora'] < 22)]
    if df_rain.empty:
        # Mensaje para el caso en que no haya lluvias
        return f"¡Hola! 🌤️ \n\nNo se esperan lluvias hoy {df['Fecha'][0]} en {query}. ¡Que tengas un buen día! ☀️"
    else:
        # Crear un mensaje detallado con las horas y condiciones de lluvia
        lluvia_horas = "\n".join(
            [f"{hora} hrs: {row['Tiempo']} con {row['prob_lluvia']}% de probabilidad de lluvia"
             for hora, row in df_rain.iterrows()])
        return f"¡Hola! ☔️ \n\nEl pronóstico de lluvia hoy {df['Fecha'][0]} en {query} es:\n\n{lluvia_horas}"

# Función para enviar el SMS con Twilio
def enviar_sms(mensaje):
    # Generación del mensaje
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        body=mensaje,
        from_=PHONE_NUMBER,
        to=TO_PHONE_NUMBER
    )
    print('Mensaje Enviado con SID:', message.sid)

# ====================== Ejecución del Script ======================
if __name__ == "__main__":
    print("Obteniendo pronóstico del clima...")
    # Obtener datos del clima
    df = obtener_pronostico()
    print(df)

    # Generar mensaje
    print("\nGenerando mensaje...")
    mensaje = generar_mensaje(df)
    print("\nMensaje a enviar:")
    print(mensaje)

    # Enviar SMS
    print("\nEnviando SMS...")
    enviar_sms(mensaje)
    print("\n¡Proceso completado con éxito!")
