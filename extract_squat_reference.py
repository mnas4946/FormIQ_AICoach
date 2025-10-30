"""
SQUAT REFERENCE DATA EXTRACTION
===============================

PURPOSE:
    Extracts joint angles and keypoint data from a squat video for reference building.
    Designed for use with later real-time form comparison.

INPUT:
    - Pre-recorded squat video (single correct set)
OUTPUT:
    - JSON file with frame-by-frame joint angles and keypoint positions
"""

import cv2
import numpy as np
import json
from ultralytics import YOLO

# -----------------------------
# CONFIGURATION
# -----------------------------
VIDEO_PATH = "data/videos/squat_correct.mp4"   # input video file
OUTPUT_JSON = "data/reference/squat_reference.json"
FRAME_SKIP = 1                     # process every frame (set to 2+ to skip frames)
MIN_VISIBLE_KEYPOINTS = 12
SMOOTH_ALPHA = 0.35

# -----------------------------
# LOAD MODEL
# -----------------------------
yolo = YOLO("yolov8n-pose.pt")

# -----------------------------
# UTILITIES
# -----------------------------
def compute_angle_deg(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba, bc = a - b, c - b
    denom = (np.linalg.norm(ba) * np.linalg.norm(bc)) + 1e-8
    cosang = np.dot(ba, bc) / denom
    cosang = np.clip(cosang, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosang)))

def smooth_kp(prev, new, alpha):
    if prev is None:
        return new
    return alpha * new + (1 - alpha) * prev

# -----------------------------
# MAIN EXTRACTION LOOP
# -----------------------------
cap = cv2.VideoCapture(VIDEO_PATH)
kp_prev = None
frame_index = 0
data = []

print(f"[INFO] Processing video: {VIDEO_PATH}")

while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame_index += 1
    if frame_index % FRAME_SKIP != 0:
        continue

    results = yolo(frame)
    if not results or len(results[0].keypoints) == 0:
        continue

    kp_array = results[0].keypoints.xy[0].cpu().numpy()
    confs = results[0].keypoints.conf[0].cpu().numpy()

    visible_mask = confs > 0.2
    if np.sum(visible_mask) < MIN_VISIBLE_KEYPOINTS:
        continue

    keypoints = np.concatenate([kp_array, confs.reshape(-1,1)], axis=1)
    kp_smooth = smooth_kp(kp_prev, keypoints, SMOOTH_ALPHA)
    kp_prev = kp_smooth.copy()

    # -----------------------------
    # COMPUTE ANGLES
    # -----------------------------
    try:
        angles = {}

        # Knees
        angles["left_knee"] = compute_angle_deg(kp_smooth[11,:2], kp_smooth[13,:2], kp_smooth[15,:2])
        angles["right_knee"] = compute_angle_deg(kp_smooth[12,:2], kp_smooth[14,:2], kp_smooth[16,:2])

        # Hips (torso to thigh)
        angles["left_hip"] = compute_angle_deg(kp_smooth[5,:2], kp_smooth[11,:2], kp_smooth[13,:2])
        angles["right_hip"] = compute_angle_deg(kp_smooth[6,:2], kp_smooth[12,:2], kp_smooth[14,:2])

        # Back alignment (shoulder-hip-knee)
        angles["left_back"] = compute_angle_deg(kp_smooth[5,:2], kp_smooth[11,:2], kp_smooth[13,:2])
        angles["right_back"] = compute_angle_deg(kp_smooth[6,:2], kp_smooth[12,:2], kp_smooth[14,:2])

    except Exception as e:
        print(f"[WARN] Angle calc error at frame {frame_index}: {e}")
        continue

    # -----------------------------
    # STORE RESULTS
    # -----------------------------
    data.append({
        "frame": frame_index,
        "angles": angles,
        "keypoints": kp_smooth[:,:2].tolist()
    })

cap.release()
print(f"[INFO] Processed {len(data)} frames.")

# -----------------------------
# SAVE TO FILE
# -----------------------------
with open(OUTPUT_JSON, "w") as f:
    json.dump(data, f, indent=2)

print(f"[DONE] Saved reference data to {OUTPUT_JSON}")
