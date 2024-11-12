import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import pickle

# Example dataset (replace with actual data)
# Columns: [pitch_speed, hit_distance, player_avg, player_slugging, pitch_type]
data = np.array([
    [85, 120, 0.275, 0.450, 0],  # fastball
    [78, 95, 0.280, 0.460, 1],   # curveball
    [92, 130, 0.300, 0.500, 0],  # fastball
    [75, 80, 0.290, 0.470, 1],   # curveball
    [88, 140, 0.310, 0.490, 0],  # fastball
    [82, 110, 0.265, 0.455, 2],  # slider
    # ... add more rows
])

# Features: [pitch_speed, hit_distance, player_avg, player_slugging]
X = data[:, :4]

# Labels: pitch_type (0 = fastball, 1 = curveball, 2 = slider, etc.)
y = data[:, 4]

# Split into training and test sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train a Random Forest Classifier
model = RandomForestClassifier(n_estimators=10, random_state=42)
model.fit(X_train, y_train)

# Evaluate the model
y_pred = model.predict(X_test)
print("Accuracy:", accuracy_score(y_test, y_pred))

# Save the trained model to a file
with open("pitch_recommendation_model.pkl", "wb") as f:
    pickle.dump(model, f)
