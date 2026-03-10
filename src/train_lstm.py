import pandas as pd
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from sklearn.preprocessing import MinMaxScaler
import joblib

# Load dataset
df = pd.read_csv("data/gps_data.csv")

# Use location data
data = df[["latitude","longitude","speed"]].values

# Normalize data
scaler = MinMaxScaler()
data_scaled = scaler.fit_transform(data)

# Create sequences
sequence_length = 10
X = []
y = []

for i in range(len(data_scaled) - sequence_length):
    X.append(data_scaled[i:i+sequence_length])
    y.append(data_scaled[i+sequence_length])

X = np.array(X)
y = np.array(y)

# Build LSTM model
model = Sequential()
model.add(LSTM(64, input_shape=(sequence_length,3)))
model.add(Dense(3))

model.compile(
    optimizer="adam",
    loss="mse"
)

# Train
model.fit(
    X,
    y,
    epochs=5,
    batch_size=32
)

# Save model
model.save("models/routine_model.h5")

joblib.dump(scaler,"models/scaler.pkl")

print("LSTM routine model trained")