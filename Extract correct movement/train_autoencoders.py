import numpy as np
import tensorflow as tf
from keras import layers, models  # Updated import path for newer TensorFlow versions
from prepare_sequences import load_and_slice  # make sure this function is in prepare_sequences.py
import os

SEQUENCE_LENGTH = 30

# ---------------------------
# Load sequences
squat_sequences = load_and_slice("poses/squats/")
arm_sequences = load_and_slice("poses/armcircles/")

print("Squat sequences:", squat_sequences.shape)
print("Arm circle sequences:", arm_sequences.shape)

# ---------------------------
# Helper: reshape for LSTM autoencoder
def reshape_sequences(sequences):
    n_samples, t, k, c = sequences.shape
    return sequences.reshape(n_samples, t, k*c)

# ---------------------------
# Create autoencoder
def create_autoencoder(input_shape):
    model = models.Sequential([
        layers.Input(shape=input_shape),
        layers.LSTM(64, return_sequences=True),
        layers.LSTM(32, return_sequences=False),
        layers.RepeatVector(input_shape[0]),
        layers.LSTM(32, return_sequences=True),
        layers.LSTM(64, return_sequences=True),
        layers.TimeDistributed(layers.Dense(input_shape[1]))
    ])
    model.compile(optimizer='adam', loss='mse')
    return model

# ---------------------------
# Ensure models folder exists
os.makedirs("models", exist_ok=True)

# ---------------------------
# Train squat autoencoder
X_squat = reshape_sequences(squat_sequences)
squat_model = create_autoencoder(X_squat.shape[1:])
print("Training Squat Autoencoder...")
squat_model.fit(X_squat, X_squat, epochs=25, batch_size=16, validation_split=0.1, shuffle=True)
squat_model.save("models/squat_autoencoder.keras")
print("Squat model saved to models/squat_autoencoder.keras")

# ---------------------------
# Train arm circle autoencoder
X_arm = reshape_sequences(arm_sequences)
arm_model = create_autoencoder(X_arm.shape[1:])
print("Training Arm Circle Autoencoder...")
arm_model.fit(X_arm, X_arm, epochs=25, batch_size=16, validation_split=0.1, shuffle=True)
arm_model.save("models/armcircle_autoencoder.keras")
print("Arm Circle model saved to models/armcircle_autoencoder.keras")

print("All models trained and saved successfully!")
