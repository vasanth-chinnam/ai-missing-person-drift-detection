import pandas as pd
import numpy as np
from tensorflow.keras.models import load_model
import joblib

# Load models
model = load_model("models/routine_model.h5", compile=False)
scaler = joblib.load("models/scaler.pkl")

df = pd.read_csv("data/gps_data.csv")

data = df[["latitude","longitude","speed"]].values

data_scaled = scaler.transform(data)

sequence_length = 10

for i in range(len(data_scaled) - sequence_length):

    sequence = data_scaled[i:i+sequence_length]
    sequence = np.expand_dims(sequence,axis=0)

    prediction = model.predict(sequence,verbose=0)

    actual = data_scaled[i+sequence_length]

    error = np.linalg.norm(prediction - actual)

    if error > 0.25:
        print("⚠ Drift detected at index:", i)