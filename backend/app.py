from flask import Flask, jsonify, Response, stream_with_context, render_template
from bleak import BleakScanner, BleakClient
import logging
import asyncio
import struct
from threading import Thread
from velocity import VelocityBattingEstimator
from pitch import simulate_pitch
from hit import calculate_exit_velocity, calculate_launch_angle
from pitch_model import predict_pitch

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
initialize_flag = True
time_to_plate = 0 #s
v_bat = None
v_ball = None
pitch_type = None
delta_t = 0.00962 #s sampling rate of IMU
latest_imu_data = []
game_stats = []
ble_task = None  # Track BLE task to prevent multiple connections
game_task = None
calculation_task = None

def iter_over_async(ait, loop):
    ait = ait.__aiter__()
    async def get_next():
        try: obj = await ait.__anext__(); return False, obj
        except StopAsyncIteration: return True, None
    while True:
        done, obj = loop.run_until_complete(get_next())
        if done: break
        yield obj

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
            global time_to_plate, v_bat, v_ball, game_stats, initialize_flag
            if client.is_connected:
                app.logger.info("Connected to Arduino")
                yield f"data: Connected\n\n"
                start_time = asyncio.get_event_loop().time()

                await asyncio.sleep(5)  # 2-second delay, adjust as needed

                # Adjust start_time to account for the delay
                start_time += 5

                def notification_handler(sender, data):
                    global delta_t, initialize_flag, v_bat
                    imu_values = struct.unpack("f" * 6, data)  # Assuming 6 floats
                    ax, ay, az, gx, gy, gz = imu_values[0], imu_values[1], imu_values[2], imu_values[3], imu_values[4], imu_values[5]
                    if (initialize_flag):
                        estimator.initialize_euler_parameters_cosine_matrix(ax, ay, az)
                        initialize_flag = False
                    else:
                        v_bat = estimator.update_velocity(ax, ay, az, gx, gy, gz, delta_t)
                        # app.logger.info(f"Current velocity: {v_bat}")
                        
                await client.start_notify(CHAR_UUID, notification_handler)
                yield f"data: Reading\n\n"

                # Keep the connection alive
                while client.is_connected:
                    if (not initialize_flag):
                        elapsed_time = asyncio.get_event_loop().time() - start_time
                        if (elapsed_time >= time_to_plate):
                            app.logger.info(f"vbat: {v_bat} vball: {v_ball}")
                            v_exit = calculate_exit_velocity(v_ball, v_bat)
                            theta_launch = calculate_launch_angle(v_exit)
                            app.logger.info(f"vball: {v_ball} \nvbat: {v_bat} vexit: {v_exit} theta_launch: {theta_launch[1]}")
                            game_stats.append({"exit_velocity": v_exit, "launch_angle": theta_launch[1], "bat_velocity": v_bat})
                            yield f"data: {{'v_bat':{v_bat}, 'v_exit':{v_exit}, 'theta_launch':{theta_launch[1]}}}\n\n"
                            break
                    await asyncio.sleep(1)

    except Exception as e:
        app.logger.error(f"Error in BLE connection: {e}")

@app.route("/get-pitch", methods=["GET"])
def generate_pitch():
    global game_stats, time_to_plate, v_ball, pitch_type
    #spin and velocity
   
    if not game_stats:
        time, x, y, z, vx, vy, vz = simulate_pitch(
            V0=40,  # Initial velocity in m/s
            omega_rpm=[0, 1200, 0],  # Spin rate vector (side spin)
            launch_angle_deg=18,  # Vertical launch angle
            side_angle_deg=0,  # Horizontal angle
            time_max=2.0,
            dt=0.01
        )
        pitch_type="Changeup"
    else:
        app.logger.info(f"stats: {game_stats}")
        pitch_data = predict_pitch(game_stats[-1]["bat_velocity"], game_stats[-1]["exit_velocity"], game_stats[-1]["launch_angle"], pitch_type)
        pitch_type = pitch_data["pitch_type"]
        time, x, y, z, vx, vy, vz = simulate_pitch(
            V0=pitch_data["pitch_velocity"],  # Initial velocity in m/s
            omega_rpm=pitch_data["spin_vector"],  # Spin rate vector (side spin)
            launch_angle_deg=pitch_data["launch_angle"],  # Vertical launch angle
            side_angle_deg=pitch_data["side_angle"],  # Horizontal angle
            time_max=2.0,
            dt=0.01
        )
    app.logger.info(f"Pitch type: {pitch_type}")
    time_to_plate = time[-1]
    v_ball = [vx[-1], vy[-1], vz[-1]]

    return jsonify({
        "time": time,
        "x": x,
        "y": y,
        "z": z,
        "vx": vx,
        "vy": vy,
        "vz": vz})


@app.route("/imu-data", methods=["GET"])
def get_imu_data():
    return jsonify(latest_imu_data)


@app.route("/start-pitch", methods=["GET"])
def start_ble():
    global ble_task, initialize_flag, estimator

    initialize_flag = True
    estimator = VelocityBattingEstimator()

    if ble_task and not ble_task.done():
        return jsonify({"message": "BLE connection is already active"}), 400

    # Create a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    iter = iter_over_async(connect_and_read(), loop)
    ctx = stream_with_context(iter)

    response = Response(ctx, content_type='text/event-stream')
    response.headers['Transfer-Encoding'] = 'chunked'
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'
    response.headers['Accept'] = '*/*'
    
    return response

@app.route('/')
def index():
    return render_template('/index.html')  


if __name__ == "__main__":
    app.logger.info("Starting Flask server...")
    app.run(host="0.0.0.0", port=5000)
