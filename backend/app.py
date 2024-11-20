from flask import Flask, jsonify, request
from bleak import BleakScanner, BleakClient
import logging
import asyncio
import struct
from threading import Thread
import numpy as np
import time

app = Flask(__name__)

# Logging setup
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s] %(message)s')
handler.setFormatter(formatter)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

SERVICE_UUID = "917649A0-E98E-11E5-9EEC-0102A5D5C51B"  # UUID for the IMU service
CHAR_UUID = "917649A0-E98E-11E5-9EEC-0102A5D5C51B"    # UUID for the IMU characteristic

delta_t = 0.00962 #s sampling rate of IMU
latest_imu_data = []
game_stats = {}
ble_task = None  # Track BLE task to prevent multiple connections
game_task = None
calculation_task = None

async def connect_and_read():
    app.logger.info("Starting BLE connection...")
    try:
        # Scan for devices that provide the service UUID
        devices = await BleakScanner.discover(timeout=10, return_adv=True)
        device_address = None

        for dev_address, adv_data in devices.items():
            if SERVICE_UUID.lower() in adv_data[1].service_uuids:
                app.logger.info(f"Found device: {adv_data[1].local_name} - {dev_address}")
                device_address = dev_address
                break

        if device_address is None:
            app.logger.info("No device found with the specified service UUID")
            return

        # Connect to the device
        async with BleakClient(device_address) as client:
            if client.is_connected:
                app.logger.info("Connected to Arduino")

                def notification_handler(sender, data):
                    global delta_t
                    imu_values = struct.unpack("f" * 6, data)  # Assuming 6 floats
                    imu_data = {
                        "accelX": imu_values[0],
                        "accelY": imu_values[1],
                        "accelZ": imu_values[2],
                        "gyroX": imu_values[3],
                        "gyroY": imu_values[4],
                        "gyroZ": imu_values[5],
                    }
                    position = get_trajectory_position(imu_data, delta_t)
                    app.logger.info(f"Current position of bat: {position}")
                    # latest_imu_data.append(imu_data)
                    # app.logger.info(f"Received IMU Data: {imu_data}")

                await client.start_notify(CHAR_UUID, notification_handler)

                # Keep the connection alive
                while client.is_connected:
                    await asyncio.sleep(1)

    except Exception as e:
        app.logger.error(f"Error in BLE connection: {e}")

# Define rotation matrices for yaw, pitch, and roll
def yaw_matrix(psi):
    return np.array([[np.cos(psi), np.sin(psi), 0],
                     [-np.sin(psi), np.cos(psi), 0],
                     [0, 0, 1]])

def pitch_matrix(theta):
    return np.array([[np.cos(theta), 0, -np.sin(theta)],
                     [0, 1, 0],
                     [np.sin(theta), 0, np.cos(theta)]])

def roll_matrix(phi):
    return np.array([[1, 0, 0],
                     [0, np.cos(phi), np.sin(phi)],
                     [0, -np.sin(phi), np.cos(phi)]])

# Function to calculate the Euler angle transformation matrix
def euler_rotation_matrix(psi, theta, phi):
    return np.dot(np.dot(yaw_matrix(psi), pitch_matrix(theta)), roll_matrix(phi))

# Function to apply IMU readings to a trajectory position
def get_trajectory_position(imu_data, delta_t):
    position = np.array([0.0, 0.0, 0.0], dtype=np.float64)  # Ensure position is float64
    velocity = np.array([0.0, 0.0, 0.0], dtype=np.float64)  # Ensure velocity is float64
    acceleration = np.array([0.0, 0.0, -9.81], dtype=np.float64)  # Gravity, float64
    
    
    # Extract gyroscope and accelerometer data from the IMU reading
    ax, ay, az = imu_data['accelX'], imu_data['accelY'], imu_data['accelZ']
    gx, gy, gz = imu_data['gyroX'], imu_data['gyroY'], imu_data['gyroZ']
    
    # Calculate the Euler angles from the gyroscope data (angular velocity integration)
    psi = gx * delta_t  # yaw
    theta = gy * delta_t  # pitch
    phi = gz * delta_t  # roll
    
    # Apply the Euler rotation matrix to the accelerometer data
    rotation_matrix = euler_rotation_matrix(psi, theta, phi)
    rotated_accel = np.dot(rotation_matrix, np.array([ax, ay, az], dtype=np.float64))
    
    # Update velocity and position using the rotated accelerometer data
    velocity += rotated_accel * delta_t
    position += velocity * delta_t
    
    return position


def generate_pitch():
    global game_stats
    # insert machine model to predict

    #spin and velocity


# def process_game():
    # global latest_imu_data, delta_t
    # while True:
    #     if latest_imu_data:
    #         # Perform the pitch calculation
    #         # pitch = calculate_pitch(accelX, accelY, accelZ)
    #         # app.logger.info(f"Calculated Pitch: {pitch} degrees")
    #         # Here you can extend the code to do more physics calculations, such as velocity or acceleration
            
    #     time.sleep(delta_t)  # Delay before the next calculation cycle (adjust as needed)

@app.route("/imu-data", methods=["GET"])
def get_imu_data():
    return jsonify(latest_imu_data)


@app.route("/start-pitch", methods=["POST"])
def start_ble():
    global ble_task

    if ble_task and not ble_task.done():
        return jsonify({"message": "BLE connection is already active"}), 400

    # Create a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    ble_task = loop.create_task(connect_and_read())

    # Run the event loop in a background thread
    def run_loop():
        loop.run_forever()

    thread = Thread(target=run_loop, daemon=True)
    thread.start()

    return jsonify({"message": "BLE connection started"})

if __name__ == "__main__":
    app.logger.info("Starting Flask server...")
    app.run(host="0.0.0.0", port=5000)
