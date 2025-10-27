import numpy as np
import json
import os
import random

SEQUENCE_LENGTH = 30  # ~1 second if 30 fps
AUGMENT = True  # set False to disable augmentation

def load_and_slice(folder):
    sequences = []
    for file in os.listdir(folder):
        if not file.endswith(".json"):
            continue
        with open(os.path.join(folder, file)) as f:
            data = np.array(json.load(f))[:, :, :2]  # drop confidence

        # normalise per frame
        center = np.mean(data, axis=1, keepdims=True)  # (frames,1,2)
        scale = np.linalg.norm(data[:, 11] - data[:, 12], axis=1, keepdims=True)  # shoulder distance
        scale = scale[..., np.newaxis]  # (frames,1,1) for broadcasting
        data = (data - center) / (scale + 1e-6)

        # slice into sequences
        for i in range(0, len(data) - SEQUENCE_LENGTH, 5):  # step=5 for overlap
            seq = data[i:i+SEQUENCE_LENGTH]

            # optional augmentation
            if AUGMENT:
                if random.random() < 0.5:
                    seq[:, :, 0] *= -1  # horizontal flip
                if random.random() < 0.3:
                    seq += np.random.normal(0, 0.02, seq.shape)  # jitter

            sequences.append(seq)

    return np.array(sequences)

# --------------------------
# Example usage:

squat_sequences = load_and_slice("poses/squats/")
arm_sequences = load_and_slice("poses/armcircles/")

print("Squat sequences:", squat_sequences.shape)
print("Arm circle sequences:", arm_sequences.shape)
