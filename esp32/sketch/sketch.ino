#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>

// ================= SERVER =================
const String serverName = "https://lavender-monkey-657081.hostingersite.com/api.php";

// ================= SENSOR & PINS =================
const int pulsePin = 13; 

// ================= WI-FI CREDENTIALS =================
const char* ssid = "Xiaomi 15";
const char* password = "qwerty123";

void setup() {
  Serial.begin(115200);
  delay(2000);
  Serial.println("\n--- MediMate BPM Monitor Started ---");
  pinMode(pulsePin, INPUT);
}

void loop() {
  // 1. DISCONNECT WI-FI TO CLEAN UP ANALOG READINGS
  WiFi.disconnect();
  WiFi.mode(WIFI_OFF);
  delay(500); // Let power stabilize

  Serial.println("Please place your finger steadily on the sensor...");
  Serial.println("Calculating BPM (Sampling for 10 seconds)...");

  // ====== BPM DETECTION VARIABLES ======
  unsigned long sampleWindowStartTime = millis();
  unsigned long lastBeatTime = 0;
  int peakValue = 2000;         // Dynamic threshold tracking
  int troughValue = 2000;
  int threshold = 2200;         // Midpoint to look for a beat
  bool preBeat = false;
  int beatCount = 0;
  
  // Keep sampling for 10000 milliseconds (10 seconds)
  while (millis() - sampleWindowStartTime < 10000) {
    int signal = analogRead(pulsePin);
    delay(20); // 50Hz Sample Rate

    // Track the highest and lowest points of the wave to auto-adjust threshold
    if (signal > peakValue) peakValue = signal;
    if (signal < troughValue) troughValue = signal;

    // Decay peak/trough slowly over time to adapt to movement
    peakValue = peakValue - 2;
    troughValue = troughValue + 2;
    threshold = (peakValue + troughValue) / 2;

    // Detect the upward surge of a heartbeat pulse
    if (signal > threshold && preBeat == false && (millis() - lastBeatTime) > 300) { 
      preBeat = true;
      beatCount++;
      
      unsigned long currentBeatTime = millis();
      if (lastBeatTime != 0) {
        long ibi = currentBeatTime - lastBeatTime; // Time between beats
        int instantBPM = 60000 / ibi;
        Serial.print("-> Beat Detected! Instant BPM: ");
        Serial.println(instantBPM);
      }
      lastBeatTime = currentBeatTime;
    }

    // Detect when the signal falls back down below the threshold
    if (signal < threshold && preBeat == true) {
      preBeat = false; 
    }
  }

  // 2. CALCULATE FINAL BPM FROM THE 10-SECOND WINDOW
  // (Beats in 10 seconds) * 6 = Beats in 60 seconds
  int finalBPM = beatCount * 6; 

  // Guard rails for bad/unrealistic readings (finger missing or moving)
  if (finalBPM < 40 || finalBPM > 180 || beatCount < 5) {
    Serial.println("⚠️ Warning: Unstable reading. Please hold still and try again.");
    finalBPM = 0; // Mark as invalid read
  }

  Serial.print("\n>>> FINAL CALCULATED PULSE: ");
  Serial.print(finalBPM);
  Serial.println(" BPM <<<\n");

  connectWifi();

  if (WiFi.status() == WL_CONNECTED) {
    WiFiClientSecure client;
    client.setInsecure();
    HTTPClient http;
      
    // Sending actual BPM instead of raw noise values
    String serverPath = serverName + "?pulse=" + String(finalBPM);

    Serial.println("Uploading BPM to server...");
    if (http.begin(client, serverPath)) {
        int httpCode = http.GET();
        Serial.print("Server Response Code: ");
        Serial.println(httpCode);
        http.end();
      }
    }
    Serial.println("-------------------------------------");
}

void connectWifi() {
  Serial.println("Connecting to Wi-Fi...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 100) {
    delay(100);
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("✔️ Connected.");
  } else {
    Serial.println("✖️ Wi-Fi Timeout.");
  }
}