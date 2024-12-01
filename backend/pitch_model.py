import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, mean_squared_error
import joblib

def generate_training_data(n_samples=1000):
    pitch_types = ["Changeup", "Knuckleball", "Fastball", "Slider", "Curveball"]
    pitch_difficulty = {"Changeup": 1, "Knuckleball": 1, "Fastball": 2, "Slider": 3, "Curveball": 3}

    data = []
    for _ in range(n_samples):
        # Random inputs
        bat_velocity = np.random.uniform(30, 100)  # mph
        exit_velocity = np.random.uniform(40, 120)  # mph
        launch_angle = np.random.uniform(-10, 50)  # degrees

        # Assign pitch type based on difficulty
        if launch_angle < 10:
            pitch_type = np.random.choice(["Changeup", "Knuckleball"])
        elif 10 <= launch_angle < 25:
            pitch_type = np.random.choice(["Fastball", "Slider"])
        else:
            pitch_type = "Curveball"

        # Determine velocity range
        if pitch_type == "Changeup":
            pitch_velocity = np.random.uniform(50, 75)
        elif pitch_type == "Knuckleball":
            pitch_velocity = np.random.uniform(45, 65)
        elif pitch_type == "Fastball":
            pitch_velocity = np.random.uniform(85, 100)
        elif pitch_type == "Slider":
            pitch_velocity = np.random.uniform(75, 90)
        elif pitch_type == "Curveball":
            pitch_velocity = np.random.uniform(65, 85)

        # Append data
        data.append([bat_velocity, exit_velocity, launch_angle, pitch_type, pitch_velocity, pitch_difficulty[pitch_type]])

    return pd.DataFrame(data, columns=["bat_velocity", "exit_velocity", "launch_angle", "pitch_type", "pitch_velocity", "difficulty"])

dataset = generate_training_data()

# Encode pitch type
encoder = LabelEncoder()
dataset["pitch_type_encoded"] = encoder.fit_transform(dataset["pitch_type"])

# Feature-target split
X = dataset[["bat_velocity", "exit_velocity", "launch_angle", "difficulty"]]
y_type = dataset["pitch_type_encoded"]
y_velocity = dataset["pitch_velocity"]

# Train-test split
X_train, X_test, y_type_train, y_type_test, y_vel_train, y_vel_test = train_test_split(X, y_type, y_velocity, test_size=0.2, random_state=42)

# Scale inputs
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# Train models
classifier = RandomForestClassifier()
regressor = RandomForestRegressor()

classifier.fit(X_train, y_type_train)
regressor.fit(X_train, y_vel_train)

# Save models and scaler for reuse
joblib.dump(classifier, "pitch_classifier.pkl")
joblib.dump(regressor, "pitch_regressor.pkl")
joblib.dump(scaler, "scaler.pkl")
joblib.dump(encoder, "pitch_encoder.pkl")

# Evaluate
# type_preds = classifier.predict(X_test)
# velocity_preds = regressor.predict(X_test)

# print(f"Classification Accuracy: {accuracy_score(y_type_test, type_preds)}")
# print(f"Regression MSE: {mean_squared_error(y_vel_test, velocity_preds)}")

def vector_magnitude(velocity_vector, include_z=False):
    """Calculate vector magnitude for given velocity vector."""
    if include_z:
        return np.sqrt(np.sum(np.array(velocity_vector)**2))
    return np.sqrt(velocity_vector[0]**2 + velocity_vector[1]**2)

def preprocess_vector_inputs(bat_velocity_vector, exit_velocity_vector):
    """Convert vector inputs to scalar representations."""
    bat_velocity = vector_magnitude(bat_velocity_vector, include_z=False)
    exit_velocity = vector_magnitude(exit_velocity_vector, include_z=True)
    return bat_velocity, exit_velocity

# Prediction function
def predict_pitch(bat_velocity_vector, exit_velocity_vector, launch_angle, pitch_type):
    # Load saved models
    classifier = joblib.load("pitch_classifier.pkl")
    regressor = joblib.load("pitch_regressor.pkl")
    scaler = joblib.load("scaler.pkl")
    encoder = joblib.load("pitch_encoder.pkl")

    pitch_difficulty = {"Changeup": 1, "Knuckleball": 1, "Fastball": 2, "Slider": 3, "Curveball": 3}
    difficulty = pitch_difficulty[pitch_type]

    bat_velocity, exit_velocity = preprocess_vector_inputs(bat_velocity_vector, exit_velocity_vector)

    spin_vector = {
        "Curveball": [0, np.random.uniform(-2530, -2430), 0],
        "Fastball": [0, np.random.uniform(1933, 2055), 0],
        "Knuckleball": [np.random.uniform(795, 989), 0, np.random.uniform(795, 989)],
        "Slider": [np.random.uniform(2036, 2086) / np.sqrt(2), 0, np.random.uniform(-2086, -2036) / np.sqrt(2)],
        "Changeup": [0, np.random.uniform(1167, 1629), 0]
    }

    # Prepare input
    input_data = np.array([[bat_velocity, exit_velocity, launch_angle, difficulty]])
    scaled_data = scaler.transform(input_data)

    # Make predictions
    pitch_type_encoded = classifier.predict(scaled_data)[0]
    pitch_velocity = regressor.predict(scaled_data)[0]
    pitch_type = encoder.inverse_transform([pitch_type_encoded])[0]

    return {
        "pitch_type": pitch_type,
        "pitch_velocity": round(float(pitch_velocity), 2),
        "spin_vector": spin_vector[pitch_type],
        "launch_angle": np.random.uniform(18, 22),
        "side_angle": 0
    }