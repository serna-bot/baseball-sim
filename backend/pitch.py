import numpy as np

def calculate_pitch_data():
    # Constants
    rho = 1.225  # Air density in kg/m^3
    G_rpm = 2000  # Spin rate in rpm
    G_rad = G_rpm * 2 * np.pi / 60  # Convert to rad/s
    b = 0.037  # Radius of the baseball in m
    mass_kg = 0.145  # Mass of the baseball in kg
    V0 = 40.2336  # Initial velocity in m/s
    distance_m = 18.44  # Distance to home plate in meters

    # Magnus force
    F = (rho * G_rad * V0 * b * np.pi) / 2  # Force in N
    a_magnus = F / mass_kg  # Acceleration due to Magnus force

    # Radius of curvature
    R = V0**2 / a_magnus  # Radius of the curved path

    # Time to reach home plate
    time = distance_m / V0  # Simplified time assuming constant velocity

    # Deflection at home plate
    Yd = R - np.sqrt(R**2 - (distance_m**2 / 4))  # Deflection assuming circular arc

    # Velocity reduction due to drag
    Cd = 0.47  # Drag coefficient
    area_ball = np.pi * b**2  # Cross-sectional area
    drag_force = 0.5 * Cd * rho * area_ball * V0**2
    a_drag = drag_force / mass_kg
    Vf = V0 - a_drag * time  # Final velocity after drag deceleration

    # Results
    print(f"Magnus Force (F): {F:.3f} N")
    print(f"Magnus Acceleration (a): {a_magnus:.3f} m/s^2")
    print(f"Radius of Curvature (R): {R:.3f} m")
    print(f"Time to Home Plate: {time:.3f} s")
    print(f"Deflection (Yd): {Yd:.3f} m")
    print(f"Final Velocity at Home Plate (Vf): {Vf:.3f} m/s")
