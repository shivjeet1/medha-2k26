#include <ESP8266WiFi.h>

// -----------------------------
// Wi-Fi details
// -----------------------------
const char* ssid = "POCO_F6";
const char* password = "shivam2285k";

// -----------------------------
// PC IP address
// -----------------------------
const char* serverIP = "10.105.186.253"; // MAKE SURE THIS MATCHES YOUR PC'S IP
const int serverPort = 5000;

// -----------------------------
// Hardware Pins
// -----------------------------
const int ECG_PIN = A0;
// Connect AD8232 LO+ to ESP8266 D1 (GPIO 5)
const int LO_PLUS_PIN = 5;  
// Connect AD8232 LO- to ESP8266 D2 (GPIO 4)
const int LO_MINUS_PIN = 4; 

// -----------------------------
// Sampling
// -----------------------------
const unsigned long SAMPLE_INTERVAL_US = 4000; // 250 Hz

WiFiClient client;

void setup() {
  Serial.begin(115200);
  delay(1000);

  // Initialize Lead-Off pins
  pinMode(LO_PLUS_PIN, INPUT);
  pinMode(LO_MINUS_PIN, INPUT);

  Serial.println();
  Serial.println("ECG Wireless Transmitter (with Lead-Off Detection)");

  // Connect to Wi-Fi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWi-Fi connected");
  Serial.print("ESP8266 IP address: ");
  Serial.println(WiFi.localIP());

  // Connect to PC
  Serial.println("Connecting to PC...");
  while (!client.connect(serverIP, serverPort)) {
    Serial.println("Connection failed. Retrying...");
    delay(1000);
  }
  Serial.println("Connected to PC");
}

void loop() {
  static unsigned long nextSampleTime = micros();

  if ((long)(micros() - nextSampleTime) >= 0) {
    nextSampleTime += SAMPLE_INTERVAL_US;

    int ecgValue = analogRead(ECG_PIN);
    int loPlus = digitalRead(LO_PLUS_PIN);
    int loMinus = digitalRead(LO_MINUS_PIN);

    // Send data format: "ECG,LO+,LO-\n"
    client.print(ecgValue);
    client.print(",");
    client.print(loPlus);
    client.print(",");
    client.println(loMinus);
  }

  // Reconnect if connection is lost
  if (!client.connected()) {
    Serial.println("PC connection lost.");
    client.stop();
    while (!client.connect(serverIP, serverPort)) {
      delay(1000);
      Serial.println("Trying to reconnect...");
    }
    Serial.println("Reconnected.");
  }
}
