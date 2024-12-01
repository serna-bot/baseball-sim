import numpy as np

class VelocityBattingEstimator:
    def __init__(self, g=9.81):
        """
        Initialize the real-time estimator.

        Parameters:
        - g: Gravitational acceleration (default: 9.81 m/s^2)
        """
        self.g = g  # Gravitational constant
        self.euler_params = None  # To store euler parameters
        self.velocity = np.array([0.0, 0.0, 0.0])  # Initialize velocity vector
        self.cosine_matrix = None

    def initialize_euler_parameters_cosine_matrix(self, ax, ay, az):
        """
        Initialize Euler parameters based on initial accelerometer readings.
        """
        theta1 = np.arcsin(-ax / self.g)  # θ1 = arcsin(-ax/g)
        theta2 = np.arctan2(ay, az)  # θ2 = arctan(ay/az)

        # Precompute values
        cos_theta1 = np.cos(theta1)
        sin_theta1 = np.sin(theta1)
        cos_theta2 = np.cos(theta2)
        sin_theta2 = np.sin(theta2)

        # Denominator for normalization
        denominator = np.sqrt(1 + cos_theta1 + cos_theta2 + cos_theta1 * cos_theta2) / 2

        # Compute Euler parameters
        e1 = sin_theta2 * (1 + cos_theta1) / (4 * denominator)
        e2 = sin_theta1 * (1 + cos_theta2) / (4 * denominator)
        e3 = -sin_theta1 * sin_theta2 / (4 * denominator)
        e4 = denominator

        self.euler_params = np.array([e1, e2, e3, e4])
        self.cosine_matrix = np.array([
            [cos_theta1, 0, -sin_theta1],
            [sin_theta1 * sin_theta2, cos_theta2, cos_theta1 * sin_theta2],
            [sin_theta1 * cos_theta2, -sin_theta2, cos_theta1 * cos_theta2]
        ])
    
    def update_orientation(self, omega_x, omega_y, omega_z):
        """
        Update Euler parameters using gyroscope data.
        """
        e1, e2, e3, e4 = self.euler_params
        omega = np.array([omega_x, omega_y, omega_z])  # Angular velocity vector

        # Compute quaternion derivatives
        q_dot = np.dot(np.array([
            [e4, -e3, e2],
            [e3, e4, -e1],
            [-e2, e1, e4],
            [-e1, -e2, -e3]
        ]), omega)

        # Integrate to update Euler parameters
        self.euler_params += q_dot
        self.euler_params /= np.linalg.norm(self.euler_params)  # Normalize

    def calculate_acceleration(self, ax, ay, az):
        """
        Compute linear acceleration in body-fixed frame.
        """
        # Compute the direction cosine matrix C from Euler parameters
        e1, e2, e3, e4 = self.euler_params
        C = self.cosine_matrix
        if C is None:
            self.cosine_matrix = None
        else:
            C = np.array([
                [e1**2 - e2**2 - e3**2 + e4**2, 2 * (e1 * e2 - e3 * e4), 2 * (e1 * e3 + e2 * e4)],
                [2 * (e1 * e2 - e3 * e4), e2**2 - e1**2 - e3**2 + e4**2, 2 * (e2 * e3 + e1 * e4)],
                [2 * (e1 * e3 + e2 * e4), 2 * (e2 * e3 - e1 * e4), e3**2 - e1**2 - e2**2 + e4**2],
            ])

        # Transform accelerometer readings from world frame to body-fixed frame
        accel_world = np.array([ax, ay, az])
        accel_body = np.dot(C.T, accel_world)  # A_a(t) = C^T * a(t)
        # print(f"Accel World: {accel_world}")
        # Debugging: print the body accelerations after gravity subtraction
        # print(f"Accel Body: {accel_body}")

        return accel_body

    def update_velocity(self, ax, ay, az, gx, gy, gz, delta_t):
        """
        Update the velocity vector based on accelerometer readings.

        Parameters:
        - ax, ay, az: Real-time accelerometer readings
        - current_time: The current timestamp in seconds
        """

        self.update_orientation(gx, gy, gz)

        # Calculate acceleration in body-fixed frame
        acceleration = self.calculate_acceleration(ax, ay, az)

        # Integrate acceleration to get velocity
        self.velocity += acceleration * delta_t

        return self.velocity