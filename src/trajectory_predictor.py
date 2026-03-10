import pandas as pd
import numpy as np
from tensorflow.keras.models import load_model
import joblib

# Load trained model
model = load_model("models/routine_model.h5", compile=False)

# Load scaler
scaler = joblib.load("models/scaler.pkl")

# Load data
df = pd.read_csv("data/gps_data.csv")

data = df[["latitude", "longitude", "speed"]].values

data_scaled = scaler.transform(data)

sequence_length = 10

def predict_next_location(sequence):

    sequence = np.expand_dims(sequence, axis=0)

    prediction = model.predict(sequence, verbose=0)

    return prediction[0]


def detect_route_deviation(index):

    if index < sequence_length:
        return False

    sequence = data_scaled[index-sequence_length:index]

    predicted = predict_next_location(sequence)

    actual = data_scaled[index]

    error = np.linalg.norm(predicted - actual)

    if error > 0.3:
        return True
    else:
        return False