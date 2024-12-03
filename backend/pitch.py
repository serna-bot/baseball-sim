import numpy as np
from scipy.integrate import solve_ivp

def magnus_force(velocity, omega, rho=1.225, radius=0.037):
    """
    Compute the Magnus force vector.
    """
    velocity_norm = np.linalg.norm(velocity)
    if velocity_norm == 0:
        return np.array([0.0, 0.0, 0.0])  # Avoid division by zero
    
    # Cross product to determine lift direction
    lift_direction = np.cross(omega, velocity / velocity_norm)
    
    # Lift coefficient approximation (dependent on spin ratio)
    spin_ratio = radius * np.linalg.norm(omega) / velocity_norm
    C_L = 1.0 / (2.0 + 1.0 / spin_ratio) if spin_ratio > 0 else 0.0  # Empirical approximation
    
    # Magnus force magnitude
    area = np.pi * radius**2  # Cross-sectional area
    magnus_magnitude = 0.5 * rho * C_L * area * velocity_norm**2
    
    return magnus_magnitude * lift_direction

def drag_force(velocity, rho=1.225, radius=0.037, Cd=0.47):
    """
    Compute the drag force vector.
    """
    velocity_norm = np.linalg.norm(velocity)
    if velocity_norm == 0:
        return np.array([0.0, 0.0, 0.0])  # Avoid division by zero
    
    area = np.pi * radius**2  # Cross-sectional area
    drag_magnitude = 0.5 * rho * Cd * area * velocity_norm**2
    
    return -drag_magnitude * (velocity / velocity_norm)

def baseball_dynamics(t, state, mass, omega, rho, radius):
    """
    Compute the state derivatives for the baseball.
    """
    x, y, z, vx, vy, vz = state
    velocity = np.array([vx, vy, vz])
    
    # Forces
    F_magnus = magnus_force(velocity, omega, rho, radius)
    F_drag = drag_force(velocity, rho, radius)
    F_gravity = np.array([0.0, 0.0, -mass * 9.81])  # Gravity
    
    # Total force
    F_total = F_magnus + F_drag + F_gravity
    
    # Acceleration
    acceleration = F_total / mass
    
    # Derivatives
    dxdt = vx
    dydt = vy
    dzdt = vz
    dvxdt, dvydt, dvzdt = acceleration
    
    return [dxdt, dydt, dzdt, dvxdt, dvydt, dvzdt]

def simulate_pitch(V0, omega_rpm, launch_angle_deg, side_angle_deg, time_max=2.0, dt=0.01):
    """
    Simulate the baseball pitch in 3D.
    """
    # Constants
    mass = 0.145  # Baseball mass in kg
    radius = 0.037  # Baseball radius in m
    rho = 1.225  # Air density in kg/m^3
    
    # Convert angles and spin to radians and rad/s
    launch_angle_rad = np.radians(launch_angle_deg)
    side_angle_rad = np.radians(side_angle_deg)
    omega = np.array(omega_rpm) * 2 * np.pi / 60  # Convert to rad/s
    
    # Initial state
    V0x = V0 * np.cos(launch_angle_rad) * np.cos(side_angle_rad)
    V0y = V0 * np.cos(launch_angle_rad) * np.sin(side_angle_rad)
    V0z = V0 * np.sin(launch_angle_rad)
    state_0 = [0.0, 0.0, 1.0, V0x, V0y, V0z]  # Initial position (z = 1 m) and velocity
    
    # Time vector
    t_span = (0, time_max)
    t_eval = np.arange(0, time_max, dt)
    
    # Solve ODEs
    solution = solve_ivp(
        baseball_dynamics, 
        t_span, 
        state_0, 
        t_eval=t_eval, 
        args=(mass, omega, rho, radius),
        method='RK45'
    )
    
    # Extract results
    x, y, z, vx, vy, vz = solution.y
    time = solution.t
    
    return time.tolist(), x.tolist(), y.tolist(), z.tolist(), vx.tolist(), vy.tolist(), vz.tolist()

def get_time_at_plate(time, y):
    array = np.asarray(y)
    idx = (np.abs(array - 18.4404)).argmin()
    return time[idx], idx

# # Example usage
time, x, y, z, vx, vy, vz = simulate_pitch(
    V0=40,  # Initial velocity in m/s
    omega_rpm=[0, 2000, 0],  # Spin rate vector (backspin for lift)
    launch_angle_deg=5,  # Vertical launch angle
    side_angle_deg=0,  # Horizontal angle
    time_max=2.0,
    dt=0.01
)

# # Final position and velocity
# final_position = [x[-1], y[-1], z[-1]]
# final_velocity = [vx[-1], vy[-1], vz[-1]]
# print(f"Final position: {final_position}")
# print(f"Final velocity: {final_velocity}")
print(x)
print(y)
print(z)
