from flask import Flask, jsonify, request
from bleak import BleakScanner, BleakClient
import logging
import asyncio
import struct
from threading import Thread

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

latest_imu_data = []
ble_task = None  # Track BLE task to prevent multiple connections


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
            if await client.is_connected():
                app.logger.info("Connected to Arduino")

                def notification_handler(sender, data):
                    global latest_imu_data
                    imu_values = struct.unpack("f" * 6, data)  # Assuming 6 floats
                    imu_data = {
                        "accelX": imu_values[0],
                        "accelY": imu_values[1],
                        "accelZ": imu_values[2],
                        "gyroX": imu_values[3],
                        "gyroY": imu_values[4],
                        "gyroZ": imu_values[5],
                    }
                    latest_imu_data.append(imu_data)
                    app.logger.info(f"Received IMU Data: {imu_data}")

                await client.start_notify(CHAR_UUID, notification_handler)

                # Keep the connection alive
                while await client.is_connected():
                    await asyncio.sleep(1)

    except Exception as e:
        app.logger.error(f"Error in BLE connection: {e}")


@app.route("/imu-data", methods=["GET"])
def get_imu_data():
    return jsonify(latest_imu_data)


@app.route("/start-ble", methods=["POST"])
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
