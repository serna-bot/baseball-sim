from flask import Flask, jsonify, request
from bleak import BleakScanner, BleakClient
import logging
import asyncio
import struct
from threading import Thread
import numpy as np
import time
from scipy.integrate import solve_ivp
from velocity import VelocityBattingEstimator

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

estimator = None
initialize_flag = False
stop_flag = False
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
            global stop_flag
            if client.is_connected:
                app.logger.info("Connected to Arduino")

                def notification_handler(sender, data):
                    global delta_t, initialize_flag
                    imu_values = struct.unpack("f" * 6, data)  # Assuming 6 floats
                    ax, ay, az, gx, gy, gz = imu_values[0], imu_values[1], imu_values[2], imu_values[3], imu_values[4], imu_values[5]
                    if (not initialize_flag):
                        estimator.initialize_euler_parameters_cosine_matrix(ax, ay, az)
                        initialize_flag = True
                    else:
                        velocity = estimator.update_velocity(ax, ay, az, gx, gy, gz, delta_t)
                        app.logger.info(f"Current velocity: {velocity}")
                    

                await client.start_notify(CHAR_UUID, notification_handler)

                # Keep the connection alive
                while client.is_connected and not stop_flag:
                    await asyncio.sleep(1)

    except Exception as e:
        app.logger.error(f"Error in BLE connection: {e}")

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
    global ble_task, stop_flag, initialize_flag, estimator

    stop_flag = False
    initialize_flag = False
    estimator = VelocityBattingEstimator()

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
