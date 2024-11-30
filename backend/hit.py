import numpy as np

def calculate_exit_velocity(v_b, v_bat, e=0.502):
    v_b = np.array(v_b)
    v_bat = np.array(v_bat)
    # Line of impact approximation using bat's velocity
    n = v_bat / np.linalg.norm(v_bat)

    # Relative velocity before collision
    v_rel_before = np.dot(v_b - v_bat, n)

    # Update the baseball's velocity components
    v_b_parallel = np.dot(v_b, n) * n  # Parallel to line of impact
    v_b_perpendicular = v_b - v_b_parallel  # Perpendicular to line of impact

    # Final parallel component (with COR)
    v_b_parallel_final = v_b_parallel - (1 + e) * v_rel_before * n

    # Final velocity
    v_b_final = v_b_parallel_final + v_b_perpendicular
    return v_b_final



# # Example Usage
# v_b = np.array([10, -5, 0])        # Initial velocity of baseball (m/s)
# v_bat = np.array([0, 20, 0])       # Velocity of bat (m/s)
# e = 0.75                           # Coefficient of restitution

# v_b_after = calculate_exit_velocity(v_b, v_bat, e)
# print("Final velocity of baseball:", v_b_after)


def calculate_launch_angle(v_b_final):
    v_b_final = np.array(v_b_final)
    # Decompose velocity vector
    v_x, v_y, v_z = v_b_final

    # Horizontal velocity magnitude
    v_horizontal = np.sqrt(v_x**2 + v_y**2)

    # Launch angle in radians
    theta = np.arctan2(v_z, v_horizontal)

    # Convert to degrees (optional)
    theta_degrees = np.degrees(theta)

    return theta, theta_degrees

# # Example usage
# v_b_final = np.array([15, 10, 20])  # Final velocity vector of baseball (m/s)
# theta_rad, theta_deg = calculate_launch_angle(v_b_final)

# print(f"Launch Angle: {theta_rad:.2f} radians ({theta_deg:.2f} degrees)")
