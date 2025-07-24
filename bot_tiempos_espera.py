# bot_tiempos_espera_web.py

import logging
import requests
import html
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import asyncio
import nest_asyncio
import os

TELEGRAM_BOT_TOKEN = '7981567584:AAHAzp79UkoxQMzSzd7LSU9i-V1retEk9WU'

# Restricciones
ID_GRUPO = -1002739246559
ID_TEMA_COLAS = 2
ID_TEMA_BIENVENIDA = 58

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

PARQUES_CON_LOGICA_ESPECIAL = {19, 277, 9, 291, 301, 310, 274, 275, 284, 31}

REGIONES = {
    "🇪🇸 España": {
        "PortAventura Park": 19,
        "Ferrari Land": 277,
        "Parque Warner Madrid": 298,
    },
    "🇫🇷 Francia": {
        "Disneyland Paris": 4,
        "Walt Disney Studios": 28,
        "Parc Astérix": 9,
        "Futuroscope": 291,
        "Walibi Rhône-Alpes": 301
    },
    "🇩🇪 Alemania/🇧🇪 Bélgica": {
        "Europa Park": 51,
        "Phantasialand": 56,
        "Movie Park Germany": 310,
        "Heide Park": 25,
        "Walibi Belgium": 14
    },
    "🇮🇹 Italia": {
        "Gardaland": 12
    },
    "🇳🇱 Países Bajos": {
        "Efteling": 160,
        "Walibi Holland": 53
    },
    "🌎 América": {
        "Magic Kingdom": 6,
        "Epcot": 5,
        "Hollywood Studios": 7,
        "Animal Kingdom": 8,
        "Universal Orlando": 65,
        "Islands of Adventure": 64,
        "Disneyland California": 17,
        "Universal Hollywood": 66
    },
    "🌏 Asia": {
        "Tokyo Disneyland": 274,
        "DisneySea": 275,
        "Universal Studios Japan": 284,
        "Hong Kong Disneyland": 31,
        "Shanghai Disneyland": 30
    }
}

# Obtener tiempos
def obtener_esperas_por_id(parque_id):
    url = f"https://queue-times.com/parks/{parque_id}/queue_times.json"
    try:
        response = requests.get(url)
        if response.status_code != 200:
            return "error"

        data = response.json()
        if parque_id in PARQUES_CON_LOGICA_ESPECIAL:
            rides = data.get("rides", [])
        else:
            rides = []
            for land in data.get("lands", []):
                rides.extend(land.get("rides", []))

        if not rides:
            return "cerrado"
        abiertas = [r for r in rides if r.get("is_open")]
        if not abiertas:
            return "cerrado"

        ordenadas = sorted(abiertas, key=lambda r: r.get("wait_time", 999))
        return ordenadas

    except Exception as e:
        logging.error(f"Error al obtener parque {parque_id}: {e}")
        return "error"

# /colas
async def colas_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ID_GRUPO or update.message.message_thread_id != ID_TEMA_COLAS:
        await update.message.reply_text("❌ Este comando solo se puede utilizar en el tema: *Tiempos De Espera*", parse_mode="Markdown")
        return
    keyboard = [[InlineKeyboardButton(region, callback_data=f"region|{region}")] for region in REGIONES]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Selecciona una región:", reply_markup=reply_markup)

# Botones
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("region|"):
        region = data.split("|", 1)[1]
        parques = REGIONES.get(region, {})
        keyboard = [[InlineKeyboardButton(nombre, callback_data=f"parque|{parques[nombre]}|{nombre}")]
                    for nombre in parques]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Parques en {region}:", reply_markup=reply_markup)

    elif data.startswith("parque|"):
        _, parque_id, nombre_visible = data.split("|", 2)
        resultado = obtener_esperas_por_id(int(parque_id))

        if resultado == "error":
            await query.edit_message_text(f"❌ Error al obtener datos de {nombre_visible}")
        elif resultado == "cerrado":
            await query.edit_message_text(f"🚫 {nombre_visible} está cerrado ahora mismo")
        else:
            texto = f"🏝️ <b>{html.escape(nombre_visible)}</b>\n"
            for ride in resultado:
                nombre = html.escape(ride['name'])
                tiempo = ride['wait_time']
                texto += f"• {nombre}: <code>{tiempo} min</code>\n"
            await query.edit_message_text(texto[:4000], parse_mode="HTML")

# Bienvenida
async def bienvenida(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message.chat.id == ID_GRUPO and message.message_thread_id == ID_TEMA_BIENVENIDA:
        for usuario in message.new_chat_members:
            nombre = html.escape(usuario.full_name)
            texto = f"🎉 ¡Bienvenido/a a esta gran comunidad <b>{nombre}</b>! ¿Estás listo/a para pasarlo muy bien?"
            await message.reply_html(texto)

# Bot runner en segundo plano
def iniciar_bot():
    asyncio.set_event_loop(asyncio.new_event_loop())
    nest_asyncio.apply()
    loop = asyncio.get_event_loop()
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("colas", colas_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, bienvenida))
    loop.run_until_complete(application.run_polling())

# Flask app para Render
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot en ejecución.", 200

# Arrancar bot al iniciar
threading.Thread(target=iniciar_bot).start()

# Ejecutar web server para Render
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
