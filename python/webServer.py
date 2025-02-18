from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import mysql.connector
import time

app = Flask(__name__)
socketio = SocketIO(app)

def get_db_connection():
    config = {
        "host": "localhost",
        "user": "smartyPlantsWriter",
        "password": "smartyPass",
        "database": "SMARTYPLANTS"
    }
    return mysql.connector.connect(**config)

@app.route("/")
def index():
    # Establish a database connection
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get the current values
    cursor.execute("SELECT * FROM measuredData ORDER BY insertDateTime DESC LIMIT 1")
    latest = cursor.fetchone()
    
    # Get aggregate statistics for temperature
    cursor.execute("""
        SELECT AVG(temperatureValue) AS avg_temp, 
               MIN(temperatureValue) AS min_temp, 
               MAX(temperatureValue) AS max_temp 
        FROM measuredData
    """)
    temp_stats = cursor.fetchone()
    
    # Get aggregate statistics for humidity
    cursor.execute("""
        SELECT AVG(humidityValue) AS avg_hum, 
               MIN(humidityValue) AS min_hum, 
               MAX(humidityValue) AS max_hum 
        FROM measuredData
    """)
    humidity_stats = cursor.fetchone()
    
    conn.close()

    # Process alarms and status for temperature
    temperature_alarm = ""
    if latest.get("temperatureAlert"):
        temperature_alarm = "TEMPERATURE HIGH!"

    # Process alarms and status for humidity
    humidity_alarm = ""
    if latest.get("humidityAlert"):
        humidity_alarm = "HUMIDITY LOW!"

    # Process rainfall values
    rain_status = "Raining" if latest.get("rainfallValue") else "No Rain"
    rain_action = ""
    if latest.get("rainfallAlert") and latest.get("humidityAlert"):
        rain_action = "OPENING ROOF..."

    conn2 = get_db_connection()
    cursor2 = conn2.cursor(dictionary=True)
    cursor2.execute("""
        SELECT insertDateTime 
        FROM measuredData 
        WHERE rainfallValue = 1 
        ORDER BY insertDateTime DESC 
        LIMIT 1
    """)
    rain_entry = cursor2.fetchone()
    conn2.close()

    if rain_entry and rain_entry.get("insertDateTime"):
        latest_date = rain_entry.get("insertDateTime").date()
    else:
        latest_date = ""

    # Render the template with the initial data
    return render_template(
        "index.html",
        temperature=latest.get("temperatureValue"),
        avg_temp=round(temp_stats.get("avg_temp", 0), 1),
        min_temp=temp_stats.get("min_temp"),
        max_temp=temp_stats.get("max_temp"),
        temperature_alarm=temperature_alarm,
        humidity=latest.get("humidityValue"),
        avg_hum=round(humidity_stats.get("avg_hum", 0), 1),
        min_hum=humidity_stats.get("min_hum"),
        max_hum=humidity_stats.get("max_hum"),
        humidity_alarm=humidity_alarm,
        rain_status=rain_status,
        rain_action=rain_action,
        latest_time=latest_date
    )

# Background thread that polls the database every 5 seconds for new entries.
def background_thread():
    last_id = None  # ID of the last processed entry
    while True:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM measuredData ORDER BY insertDateTime DESC LIMIT 1")
        latest = cursor.fetchone()
        conn.close()
        
        if latest and latest.get("measureID") != last_id:
            last_id = latest.get("measureID")
            
            # Process alarms and status for temperature
            temperature_alarm = ""
            if latest.get("temperatureAlert"):
                temperature_alarm = "TEMPERATURE HIGH!"

            # Process alarms and status for humidity
            humidity_alarm = ""
            if latest.get("humidityAlert"):
                humidity_alarm = "HUMIDITY LOW!"

            # Process rainfall values
            rain_status = "Raining" if latest.get("rainfallValue") else "No Rain"
            rain_action = ""
            if latest.get("rainfallAlert") and latest.get("humidityAlert"):
                rain_action = "OPENING ROOF..."
                
            latest_datetime = latest.get("insertDateTime")
            latest_date = latest_datetime.date() if latest_datetime else ""
            
            data = {
                "temperature": latest.get("temperatureValue"),
                "temperature_alarm": temperature_alarm,
                "humidity": latest.get("humidityValue"),
                "humidity_alarm": humidity_alarm,
                "rain_status": rain_status,
                "rain_action": rain_action,
                "latest_time": str(latest_date)
            }
            socketio.emit("new_data", data)
        time.sleep(5)

if __name__ == "__main__":
    socketio.start_background_task(background_thread)
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
