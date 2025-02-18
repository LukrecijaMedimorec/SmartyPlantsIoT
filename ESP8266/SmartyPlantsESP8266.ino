#include "Simple-Sensor-SOLDERED.h"
#include "Simple-Rain-Sensor-SOLDERED.h"
#include <DHT.h>
#include <Servo.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>

#define DHTPIN 4
#define DHTTYPE DHT22
#define RAIN_PIN 16
#define LED_GREEN 2
#define LED_RED 15
#define BUZZER_PIN 14
#define SERVO_PIN 12
#define SENSOR_A0_PIN 0

#define TEMP_THRESHOLD 30
#define HUMIDITY_THRESHOLD 40
#define HUMIDITY_OPTIMAL 50

const char* ssid = "paulina";
const char* password = "idegas123";
const char* mqtt_server = "172.20.10.5";

WiFiClient espClient;
PubSubClient client(espClient);

DHT dht(DHTPIN, DHTTYPE);
Servo krovServo;
simpleRainSensor rainSensor(SENSOR_A0_PIN, RAIN_PIN);

bool krovOtvoren = false;
unsigned long lastSendTime = 0;
const unsigned long sendInterval = 5000; 

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.println("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");  
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());

}

void printWiFiNetworks() {
  Serial.println("Scanning for WiFi networks...");
  int numberOfNetworks = WiFi.scanNetworks();

  Serial.println("Number of networks found: " + String(numberOfNetworks));

  for (int i = 0; i < numberOfNetworks; i++) {
    Serial.print("Network Name: ");
    Serial.println(WiFi.SSID(i));
    Serial.print("Signal Strength: ");
    Serial.println(WiFi.RSSI(i));
    Serial.println("-----------------------");
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Connecting to MQTT server at: ");
    Serial.println(mqtt_server);
    Serial.print("Attempting MQTT connection...");
    if (client.connect("ESP8266Client")) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void sendSensorData(float temperature, float humidity, bool isRaining, bool tempAlert, bool humidityAlert, bool rainAlert) {
  String payload = "{";
  payload += "\"temperatureValue\":" + String(temperature) + ","; 
  payload += "\"temperatureAlert\":" + String(tempAlert) + ",";
  payload += "\"humidityValue\":" + String(humidity) + ",";
  payload += "\"humidityAlert\":" + String(humidityAlert) + ",";
  payload += "\"rainfallValue\":" + String(isRaining) + ",";
  payload += "\"rainfallAlert\":" + String(rainAlert);
  payload += "}";
  client.publish("sensor/data", payload.c_str());
  Serial.println("Data sent: " + payload);  // Dodan ispis za provjeru
}

void setup() {
  Serial.begin(9600);
  dht.begin();
  rainSensor.begin();

  krovServo.attach(SERVO_PIN);
  krovServo.write(0);

  pinMode(RAIN_PIN, INPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_RED, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  digitalWrite(LED_GREEN, LOW);
  digitalWrite(LED_RED, LOW);
  digitalWrite(BUZZER_PIN, LOW);

  printWiFiNetworks();
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  
}

void loop() {

  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();
  bool isRaining = rainSensor.isRaining();

  bool tempAlert = temperature > TEMP_THRESHOLD;
  bool humidityAlert = humidity < HUMIDITY_THRESHOLD;
  bool rainAlert = isRaining;
  unsigned long currentMillis = millis();

  if (currentMillis - lastSendTime >= sendInterval) {
    sendSensorData(temperature, humidity, isRaining, tempAlert, humidityAlert, rainAlert);
    lastSendTime = currentMillis;
  }

  if (!tempAlert && !humidityAlert && !krovOtvoren) {
    digitalWrite(LED_GREEN, LOW);
  } else {
    digitalWrite(LED_GREEN, HIGH);
  }

  if (tempAlert) {
    Serial.println("ALERT: Temperature is too high!");
    tone(BUZZER_PIN, 1000);
    for (int i = 0; i < 3; i++) {
      digitalWrite(LED_RED, HIGH);
      delay(500);
      digitalWrite(LED_RED, LOW);
      delay(500);
    }
    noTone(BUZZER_PIN);
  }

  if (humidityAlert && !krovOtvoren) {
    Serial.println("ALERT: Humidity is too low! Water the plants!");
    tone(BUZZER_PIN, 1000);
    for (int i = 0; i < 3; i++) {
      digitalWrite(LED_RED, HIGH);
      delay(500);
      digitalWrite(LED_RED, LOW);
      delay(500);
    }
    noTone(BUZZER_PIN);
  }

  if (isRaining && humidity < HUMIDITY_THRESHOLD && !krovOtvoren) {
    Serial.println("Rain detected and humidity low. Opening the roof...");
    for (int pos = 0; pos <= 90; pos += 5) {
      krovServo.write(pos);
      delay(200);
    }
    krovOtvoren = true;
    digitalWrite(LED_RED, LOW);
  }

  if (krovOtvoren && humidity >= HUMIDITY_OPTIMAL) {
    Serial.println("Optimal humidity reached. Closing the roof...");
    for (int pos = 90; pos >= 0; pos -= 5) {
      krovServo.write(pos);
      delay(200);
    }
    krovOtvoren = false;
    digitalWrite(LED_RED, HIGH);
  }

  delay(1000);
}
