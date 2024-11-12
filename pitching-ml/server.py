# Import necessary libraries
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pickle
import numpy as np

# Define data schema for incoming requests
class PitchRequest(BaseModel):
    pitch_equation: str  # Equation or identifier of the current pitch
    speed: float         # Speed of the pitch
    hit_data: list       # List of data on previous hits, angles, etc.
    player_stats: dict   # Additional player stats or relevant data

# Load the pre-trained model
with open("pitch_recommendation_model.pkl", "rb") as f:
    model = pickle.load(f)

# Initialize FastAPI app
app = FastAPI()

@app.post("/predict_next_pitch")
async def predict_next_pitch(data: PitchRequest):
    try:
        # Preprocess the input data for the model
        features = [data.speed] + data.hit_data + list(data.player_stats.values())
        features = np.array(features).reshape(1, -1)

        # Make a prediction using the model
        recommended_pitch = model.predict(features)
        
        return {"recommended_pitch": recommended_pitch[0]}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

