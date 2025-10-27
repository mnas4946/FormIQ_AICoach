import tensorflow as tf
import tensorflow_hub as hub
import cv2
import os
import json

# Load MoveNet Lightning (faster)
movenet = hub.load("https://tfhub.dev/google/movenet/singlepose/lightning/4")
input_size = 192
frame_skip = 2  # process every 2nd frame

def detect_pose(frame):
    img = tf.image.resize_with_pad(tf.expand_dims(frame, axis=0), input_size, input_size)
    input_img = tf.cast(img, dtype=tf.int32)
    outputs = movenet.signatures['serving_default'](input_img)
    keypoints = outputs['output_0'].numpy()[0][0]  # shape: (17,3)
    return keypoints.tolist()

def process_video(video_path, output_json):
    cap = cv2.VideoCapture(video_path)
    all_keypoints = []
    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
        if frame_count % frame_skip != 0:
            continue  # skip frames to speed up

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        keypoints = detect_pose(frame_rgb)
        all_keypoints.append(keypoints)

        if frame_count % 10 == 0:
            print(f"Processed {frame_count} frames for {video_path}")

    cap.release()

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_json), exist_ok=True)

    with open(output_json, 'w') as f:
        json.dump(all_keypoints, f)

    print(f"Saved keypoints to {output_json}")

# Example usage
process_video("data/squats/squat.mp4", "poses/squats/squat.json")
process_video("data/armcircles/armcircle.mp4", "poses/armcircles/armcircle.json")
