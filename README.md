Where are the files :D

haha, they uploaded now


Current Code: track movements, and log whether exercise is completed
    - yolov8n: recognising movements, detecting object

# tracks body movements in real-time and provides feedback

1. extract_keypoints.py - Pose Extraction
    Uses MoveNet (Google's pose estimation model) to extract skeletal keypoints from video files:
    Processes videos frame-by-frame (with frame skipping for speed)
    Detects 17 body keypoints (shoulders, elbows, hips, knees, etc.)
    Saves keypoints as JSON files for later training
    Example: Processes squat and arm circle videos

2. prepare_sequences.py - Data Preprocessing
    Prepares extracted keypoints for machine learning:
    Loads JSON keypoint files
    Normalizes data: centers pose and scales by shoulder distance
    Slices long sequences into 30-frame windows (~1 second)
    Data augmentation: horizontal flips and random jitter for better model generalization

3. train_autoencoders.py - Model Training
    Trains LSTM autoencoder models to learn "normal" exercise patterns:
    Creates separate autoencoders for squats and arm circles
    Architecture: LSTM layers that compress sequences into a latent representation then reconstruct them
    Trained to minimize reconstruction error (MSE)
    Could be used for anomaly detection (abnormal movements would have high reconstruction error)

4. realtime_detection.py - Real-time AI Coach ⭐
The main application that provides live exercise feedback:
Key Features:
    Uses YOLOv8-pose for real-time pose detection from webcam
    Tracks two exercises: Squats and Arm Circles
    Counts repetitions automatically
    Provides real-time voice feedback using text-to-speech
    Shows angle measurements and form tips on screen
How it works:
    Squat Detection:
        Tracks knee angles (hip-knee-ankle)
        Detects "down" position (angle < 100°)
        Detects "up" position (angle > 160°)
        Counts a rep when transitioning from down→up
Arm Circle Detection:
    Tracks the angle between shoulder center and wrist center
    Accumulates rotation degrees
    Counts a circle when 300° of rotation is accumulated

