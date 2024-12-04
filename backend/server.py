from flask import Flask, jsonify
from bleak import BleakScanner, BleakClient
import asyncio
import struct
from threading import Thread

app = Flask(__name__)

SERVICE_UUID = "917649A0-E98E-11E5-9EEC-0102A5D5C51B"  # UUID for the IMU service
CHAR_UUID = "917649A0-E98E-11E5-9EEC-0102A5D5C51B"    # UUID for the IMU characteristic

latest_imu_data = []

async def connect_and_read():
    # Scan for devices that provide the service UUID
    devices = await BleakScanner.discover()
    device_address = None
    
    for device in devices:
        if SERVICE_UUID in device.metadata.get('uuids', []):
            print(f"Found device: {device.name} - {device.address}")
            device_address = device.address
            break
    
    if device_address is None:
        print("No device found with the specified service UUID")
        return

    # Connect to the first device with the required service
    async with BleakClient(device_address) as client:
        if await client.is_connected():
            print("Connected to Arduino")

            def notification_handler(sender, data):
                global latest_imu_data
                imu_values = struct.unpack("f" * 4, data)  # Assuming there are 4 floats in the data
                latest_imu_data.append({
                    "accelX": imu_values[0],
                    "accelY": imu_values[1],
                    "accelZ": imu_values[2],
                    "peakSwingSpeed": imu_values[3]
                })
                print("Received IMU Data:", latest_imu_data[-1])

            await client.start_notify(CHAR_UUID, notification_handler)
            while await client.is_connected():
                await asyncio.sleep(1)

@app.route("/imu-data", methods=["GET"])
def get_imu_data():
    return jsonify(latest_imu_data)

def start_ble_loop():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(connect_and_read())

if __name__ == "__main__":
    # Start the BLE connection loop in a separate thread
    ble_thread = Thread(target=start_ble_loop)
    ble_thread.start()

    # Run the Flask web server
    app.run(host="0.0.0.0", port=5000)
