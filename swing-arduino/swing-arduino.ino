#include <ArduinoBLE.h>
#include <Arduino_LSM6DS3.h> // IMU library

// Bluetooth
BLEService imuService("917649A0-E98E-11E5-9EEC-0102A5D5C51B"); // Define a BLE service UUID
BLECharacteristic imuChar("917649A0-E98E-11E5-9EEC-0102A5D5C51B", BLERead | BLENotify, sizeof(float) * 4); // Characteristic to send IMU data in small chunks

// Thresholds and constants
const float SWING_THRESHOLD = 15.0; // Acceleration threshold in m/s^2 for swing detection
const int DATA_WINDOW_SIZE = 10;    // Number of samples around the swing to capture
const int SWING_DETECTION_INTERVAL = 200; // Minimum interval in milliseconds between swings

// Variables to capture sensor data
float accelX, accelY, accelZ;
float gyroX, gyroY, gyroZ;
float swingData[DATA_WINDOW_SIZE][3]; // Store accelX, accelY, accelZ for each sample
float peakSwingSpeed = 0.0;
bool swingDetected = false;
unsigned long lastSwingTime = 0;

void setup() {
  Serial.begin(9600);
  if (!BLE.begin()) {
    Serial.println("BLE initialization failed");
    while (1);
  }
  Serial.println("BLE initialized");

  if (!IMU.begin()) {
    Serial.println("Failed to initialize IMU!");
    while (1);
  }
  Serial.println("IMU initialized!");

  // Set up BLE service and characteristic
  BLE.setLocalName("Nano33IMU");
  BLE.setAdvertisedService(imuService);
  imuService.addCharacteristic(imuChar);
  BLE.addService(imuService);

  // Start advertising
  BLE.advertise();
  Serial.println("BLE advertising started");
}

void loop() {
  if (IMU.accelerationAvailable() && IMU.gyroscopeAvailable()) {
    IMU.readAcceleration(accelX, accelY, accelZ);
    IMU.readGyroscope(gyroX, gyroY, gyroZ);

    // Calculate resultant acceleration vector
    float resultantAccel = sqrt(accelX * accelX + accelY * accelY + accelZ * accelZ);

    // Check if swing threshold is exceeded
    if (resultantAccel >= SWING_THRESHOLD && millis() - lastSwingTime > SWING_DETECTION_INTERVAL) {
      lastSwingTime = millis();
      swingDetected = true;

      // Capture data window around the swing event and record peak swing speed
      captureSwingData();
      peakSwingSpeed = calculateSwingSpeed();

      // Send data to backend
      sendSwingData();
    }
  }
}

// Function to capture a window of accelerometer data around the swing
void captureSwingData() {
  for (int i = 0; i < DATA_WINDOW_SIZE; i++) {
    if (IMU.accelerationAvailable()) {
      IMU.readAcceleration(accelX, accelY, accelZ);
      swingData[i][0] = accelX;
      swingData[i][1] = accelY;
      swingData[i][2] = accelZ;
      delay(10); // Capture data every 10 ms
    }
  }
}

// Function to calculate peak swing speed using gyroscope data
float calculateSwingSpeed() {
  float maxGyro = 0.0;
  for (int i = 0; i < DATA_WINDOW_SIZE; i++) {
    if (IMU.gyroscopeAvailable()) {
      IMU.readGyroscope(gyroX, gyroY, gyroZ);
      maxGyro = max(maxGyro, sqrt(gyroX * gyroX + gyroY * gyroY + gyroZ * gyroZ));
      delay(10);
    }
  }
  return maxGyro;
}

// Function to send captured swing data to the backend
void sendSwingData() {
  Serial.println("Sending Swing Data:");

  // Pack data into a byte array in chunks to handle BLE size limits
  uint8_t buffer[16]; // Buffer for 4 floats per send
  for (int i = 0; i < DATA_WINDOW_SIZE; i++) {
    memcpy(buffer, &swingData[i][0], sizeof(float));      // accelX
    memcpy(buffer + 4, &swingData[i][1], sizeof(float));  // accelY
    memcpy(buffer + 8, &swingData[i][2], sizeof(float));  // accelZ
    memcpy(buffer + 12, &peakSwingSpeed, sizeof(float));  // Peak swing speed

    imuChar.writeValue(buffer, sizeof(buffer)); // Send data in chunks
    delay(50); // Delay to manage BLE send rate
  }
}
