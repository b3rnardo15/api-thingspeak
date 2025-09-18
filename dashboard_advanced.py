#!/usr/bin/env python3
"""
Dashboard Interativo para Dados do ThingSpeak
Usando Flask para criar uma aplicação web com gráficos dinâmicos
"""

from flask import Flask, render_template, jsonify
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
import json

app = Flask(__name__)

# Configurações da API do ThingSpeak
CHANNEL_ID = "2943258"
READ_API_KEY = "G3BDQS615PRGFEWR"
BASE_URL = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json"

def get_thingspeak_data(results=100):
    """Busca os dados mais recentes do canal ThingSpeak."""
    params = {
        "api_key": READ_API_KEY,
        "results": results
    }
    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar dados do ThingSpeak: {e}")
        return None

def process_data(thingspeak_data):
    """Processa os dados brutos do ThingSpeak e retorna um DataFrame do Pandas."""
    if not thingspeak_data or "feeds" not in thingspeak_data:
        return pd.DataFrame()

    feeds = thingspeak_data["feeds"]
    processed_records = []
    
    # Configurar fuso horário brasileiro
    utc = pytz.UTC
    brazil_tz = pytz.timezone('America/Sao_Paulo')

    for feed in feeds:
        try:
            # Converter UTC para horário brasileiro
            created_at_utc = pd.to_datetime(feed["created_at"])
            if created_at_utc.tz is None:
                created_at_utc = utc.localize(created_at_utc)
            created_at_brazil = created_at_utc.astimezone(brazil_tz)
            
            humidity = float(feed["field1"]) if feed["field1"] is not None else None
            temperature = float(feed["field2"]) if feed["field2"] is not None else None

            processed_records.append({
                "created_at": created_at_brazil,
                "humidity": humidity,
                "temperature": temperature
            })
        except (ValueError, TypeError) as e:
            continue

    df = pd.DataFrame(processed_records)
    if not df.empty:
        df = df.set_index("created_at")
        df = df.dropna()
    return df

def prepare_chart_data(df):
    """Prepara os dados para os gráficos Chart.js."""
    if df.empty:
        return {
            "labels": [],
            "humidity_data": [],
            "temperature_data": []
        }
    
    # Converter timestamps para strings formatadas
    labels = [timestamp.strftime("%d/%m %H:%M") for timestamp in df.index]
    
    return {
        "labels": labels,
        "humidity_data": df["humidity"].tolist(),
        "temperature_data": df["temperature"].tolist()
    }

@app.route("/")
def dashboard():
    """Página principal do dashboard."""
    return render_template("dashboard.html")

@app.route("/api/data")
def get_data():
    """API endpoint para obter dados atualizados."""
    data = get_thingspeak_data()
    if not data:
        return jsonify({"error": "Não foi possível obter dados do ThingSpeak"}), 500
    
    df = process_data(data)
    if df.empty:
        return jsonify({"error": "Nenhum dado válido encontrado"}), 404
    
    # Preparar dados para Chart.js
    chart_data = prepare_chart_data(df)
    
    # Estatísticas básicas
    stats = {
        "humidity": {
            "current": float(df["humidity"].iloc[-1]) if not df.empty else 0,
            "avg": float(df["humidity"].mean()) if not df.empty else 0,
            "min": float(df["humidity"].min()) if not df.empty else 0,
            "max": float(df["humidity"].max()) if not df.empty else 0
        },
        "temperature": {
            "current": float(df["temperature"].iloc[-1]) if not df.empty else 0,
            "avg": float(df["temperature"].mean()) if not df.empty else 0,
            "min": float(df["temperature"].min()) if not df.empty else 0,
            "max": float(df["temperature"].max()) if not df.empty else 0
        },
        "last_update": df.index[-1].strftime("%d/%m/%Y %H:%M:%S") if not df.empty else "N/A",
        "total_records": len(df)
    }
    
    return jsonify({
        "chart_data": chart_data,
        "stats": stats
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)


