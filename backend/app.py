from flask import Flask, jsonify, Response, request
from bleak import BleakScanner, BleakClient
import logging
import asyncio
import math
import struct
import time
import pickle

app = Flask(__name__)

SERVICE_UUID = "917649A0-E98E-11E5-9EEC-0102A5D5C51B"
CHAR_UUID = "917649A0-E98E-11E5-9EEC-0102A5D5C51B"

# Logging setup
app.logger.setLevel(logging.INFO)
handler = logging.FileHandler('app.log')
app.logger.addHandler(handler)

# BLE global variables
ble_client = None
latest_imu_data = []

# Load the model with pickle
# with open('ai_coach_model.pkl', 'rb') as model_file:
#     model = pickle.load(model_file)

# Pitch properties
pitch_distance = 18.44  # meters (60 ft, 6 in)
gravity = 9.81  # m/s^2
streaming_active = False  # Control flag for streaming


def get_pitch_from_model(stats):
    """Use the ML model to predict the pitch type and properties."""
    # formatted_stats = [stats]  # Ensure it matches the model's expected shape
    # prediction = model.predict(formatted_stats)[0]

    # Map prediction to pitch properties
    # pitch_map = {
    #     0: "Four-Seam Fastball",
    #     1: "Slider",
    #     2: "Curveball",
    #     3: "Changeup",
    #     4: "Knuckleball",
    # }
    # pitch_type = pitch_map.get(prediction["pitch_type"], "Four-Seam Fastball")

    # Add 3D properties (velocity, elevation, and azimuth angles)
    # return pitch_type, {
    #     "velocity": prediction["velocity"],  # m/s
    #     "elevation_angle": prediction["elevation_angle"],  # degrees
    #     "azimuth_angle": prediction["azimuth_angle"],  # degrees
    # }

    return "Four-Seam Fastball", {
        "velocity": 40,  # m/s
        "elevation_angle": 30,  # degrees
        "azimuth_angle": 20,  # degrees
    }


def calculate_trajectory(velocity, elevation_angle, azimuth_angle, time):
    """Calculates ball's 3D position at a given time."""
    rad_elevation = math.radians(elevation_angle)
    rad_azimuth = math.radians(azimuth_angle)

    x = velocity * math.cos(rad_elevation) * math.cos(rad_azimuth) * time  # Horizontal forward
    z = velocity * math.cos(rad_elevation) * math.sin(rad_azimuth) * time  # Horizontal lateral
    y = (velocity * math.sin(rad_elevation) * time) - (0.5 * gravity * time**2)  # Vertical height

    return x, max(0, y), z  # y cannot be negative


def detect_hit(imu_data):
    """Detects if a hit occurred based on IMU data."""
    impact_threshold = 50  # Angular velocity threshold
    for data in imu_data:
        if any(abs(data[axis]) > impact_threshold for axis in ["gyroX", "gyroY", "gyroZ"]):
            return True
    return False


async def start_streaming():
    """Start BLE notifications and process incoming data."""
    global ble_client, latest_imu_data

    async def notification_handler(_, data):
        # Convert raw bytes to 6 floats
        imu_values = struct.unpack('<ffffff', data)
        latest_imu_data.append({
            "accX": imu_values[0],
            "accY": imu_values[1],
            "accZ": imu_values[2],
            "gyroX": imu_values[3],
            "gyroY": imu_values[4],
            "gyroZ": imu_values[5],
        })

    if ble_client is None or not ble_client.is_connected:
        devices = await BleakScanner.discover()
        target_device = next((d for d in devices if "IMU_Device" in d.name), None)
        if not target_device:
            raise ConnectionError("Target BLE device not found.")
        ble_client = BleakClient(target_device)

    if not ble_client.is_connected:
        await ble_client.connect()

    await ble_client.start_notify(CHAR_UUID, notification_handler)


async def stop_streaming():
    """Stop BLE notifications."""
    global ble_client
    if ble_client and ble_client.is_connected:
        await ble_client.stop_notify(CHAR_UUID)
        await ble_client.disconnect()
        ble_client = None


@app.route("/imu-data", methods=["POST"])
def stream_imu_data():
    global streaming_active

    if streaming_active:
        return jsonify({"error": "A pitch is already in progress. Wait until it finishes."}), 400

    # Extract stats from the request
    stats = request.json.get("stats", [])
    if not stats:
        return jsonify({"error": "Stats are required for pitch prediction."}), 400

    # Get pitch type and properties from the model
    pitch_type, pitch_props = get_pitch_from_model(stats)
    velocity = pitch_props["velocity"]
    elevation_angle = pitch_props["elevation_angle"]
    azimuth_angle = pitch_props["azimuth_angle"]
    pitch_time = pitch_distance / velocity

    app.logger.info(f"Generated pitch: {pitch_type}, Velocity={velocity} m/s, "
                    f"Elevation Angle={elevation_angle}°, Azimuth Angle={azimuth_angle}°, "
                    f"Time={pitch_time:.2f} s")

    async def imu_stream():
        global streaming_active
        try:
            streaming_active = True
            await start_streaming()
            start_time = time.time()

            while True:
                elapsed_time = time.time() - start_time

                # Stop streaming if pitch time elapsed or hit detected
                if elapsed_time >= pitch_time or detect_hit(latest_imu_data):
                    result = "hit" if detect_hit(latest_imu_data) else "miss"
                    yield jsonify({"result": result, "pitch_type": pitch_type}).data + b"\n"
                    break

                # Calculate trajectory
                x, y, z = calculate_trajectory(velocity, elevation_angle, azimuth_angle, elapsed_time)
                imu_data = latest_imu_data[:1] if latest_imu_data else {}

                # Stream trajectory and IMU data
                trajectory_json = jsonify({"trajectory": {"x": x, "y": y, "z": z}, "imu_data": imu_data})
                yield trajectory_json.data + b"\n"

                await asyncio.sleep(0.1)
        finally:
            streaming_active = False
            await stop_streaming()

    return Response(imu_stream(), mimetype="application/json")


@app.route("/")
def hello():
    return "<h1>Hello, World!</h1>"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
