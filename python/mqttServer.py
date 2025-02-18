import mysql.connector
import sqlite3
import json
import paho.mqtt.client as mqtt
from datetime import datetime

# Database Configuration
DB_TYPE = "mysql"

if DB_TYPE == "mysql" or DB_TYPE == "mariadb":
    db_config = {
        "host": "localhost",
        "user": "smartyPlantsWriter",
        "password": "smartyPass",
        "database": "SMARTYPLANTS"
    }
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
else:
    conn = sqlite3.connect("sensor_data.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
       CREATE TABLE IF NOT EXISTS measuredData(
           measureID INTEGER PRIMARY KEY AUTOINCREMENT,
           temperatureValue FLOAT,
           temperatureAlert BOOL,
           humidityValue FLOAT,
           humidityAlert BOOL,
           rainfallValue BOOL,
           rainfallAlert BOOL,
           insertDateTime DATETIME DEFAULT CURRENT_TIMESTAMP
       )
    """)
    conn.commit()

# MQTT Configuration
BROKER_ADDRESS = "172.20.10.5"
PORT = 1883
TOPIC = "sensor/data"

# Callback function when a message is received
def on_message(client, userdata, message):
    try:
        payload = message.payload.decode('utf-8')
        data = json.loads(payload)
        
        # Extract data from JSON
        temperatureValue = data.get("temperatureValue", None)
        temperatureAlert = data.get("temperatureAlert", False)
        humidityValue = data.get("humidityValue", None)
        humidityAlert = data.get("humidityAlert", False)
        rainfallValue = data.get("rainfallValue", False)
        rainfallAlert = data.get("rainfallAlert", False)

        # Check if required data exists
        if temperatureValue is None or humidityValue is None:
            print("Incomplete data received, skipping...")
            return

        # Insert data into the database
        if DB_TYPE == "mysql" or DB_TYPE == "mariadb":
            query = """
                INSERT INTO measuredData 
                (temperatureValue, temperatureAlert, humidityValue, humidityAlert, rainfallValue, rainfallAlert)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (temperatureValue, temperatureAlert, humidityValue, humidityAlert, rainfallValue, rainfallAlert))
            conn.commit()

        else:
            query = """
                INSERT INTO measuredData 
                (temperatureValue, temperatureAlert, humidityValue, humidityAlert, rainfallValue, rainfallAlert)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            cursor.execute(query, (temperatureValue, temperatureAlert, humidityValue, humidityAlert, rainfallValue, rainfallAlert))
            conn.commit()

        print(f"[{datetime.now()}] Data stored successfully: {data}")
    except json.JSONDecodeError:
        print("Error decoding JSON payload.")
    except Exception as e:
        print(f"Error processing message: {e}")

# MQTT Client Setup
client = mqtt.Client("RaspberryPiClient")
client.on_message = on_message
client.callback_api_version = 2
client.connect(BROKER_ADDRESS, PORT, 300)
client.subscribe(TOPIC)
client.loop_start()

# Loop
try:
    while True:
        pass
except KeyboardInterrupt:
    print("Exiting...")
    client.loop_stop()
    conn.close()
