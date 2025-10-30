"""
REAL-TIME EXERCISE DETECTION AND COACHING
==========================================
PURPOSE: This script provides real-time AI coaching for exercises using pose detection.
         It detects body poses via webcam, counts reps, and gives vocal/visual feedback.

INPUT:  Live webcam feed
OUTPUT: Real-time visual feedback + voice coaching + rep counting

RELATIONSHIP TO PIPELINE:
    - This is INDEPENDENT from the training pipeline (extract_keypoints → prepare_sequences → train_autoencoders)
    - This script uses YOLOv8 (not MoveNet) for REAL-TIME pose detection
    - It provides RULE-BASED feedback (not ML-based) using joint angles
    - Future integration: Could load trained autoencoder models to detect incorrect form

WHAT IT DOES:
    1. Captures live video from webcam
    2. Detects human pose using YOLOv8
    3. Calculates joint angles (knees, elbows)
    4. Tracks exercise state (squat up/down, arm rotation)
    5. Counts reps automatically
    6. Provides real-time vocal and visual coaching feedback

EXERCISES SUPPORTED:
    - Squats (tracks knee angle for depth)
    - Arm Circles (tracks rotation accumulation)
"""

import cv2
import numpy as np
import time
import threading
import queue
import math
from collections import deque
from ultralytics import YOLO
import pyttsx3
import json

# -----------------------------
# Load reference data
# -----------------------------
REFERENCE_JSON = "data/reference/squat_reference.json" 
ANGLE_TOLERANCE = 8.0  # ± degrees allowed deviation per joint

def load_reference_data(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)
    # compute average angles per squat phase
    phases = {"top": [], "mid": [], "bottom": []}
    for entry in data:
        a = entry["angles"]
        if "left_knee" in a and "right_knee" in a:
            avg_knee = (a["left_knee"] + a["right_knee"]) / 2
            if avg_knee > 160:
                phases["top"].append(a)
            elif avg_knee > 100:
                phases["mid"].append(a)
            else:
                phases["bottom"].append(a)
    # average each joint per phase
    ref_avg = {}
    for phase, lst in phases.items():
        if not lst:
            continue
        keys = lst[0].keys()
        ref_avg[phase] = {k: np.mean([d[k] for d in lst]) for k in keys}
    return ref_avg

reference_angles = load_reference_data(REFERENCE_JSON)
print(f"[INFO] Reference loaded: phases={list(reference_angles.keys())}")


# ========================================
# CONFIGURATION PARAMETERS
# ========================================

# Video input source (0 = default webcam, or path to video file)
VIDEO_SOURCE = 0

# Performance settings
FRAME_SKIP = 1                 # Process every N-th frame (increase to 2-3 for speed on slow computers)

# Pose detection settings
SMOOTH_ALPHA = 0.35            # Smoothing factor (EWMA) for keypoints (0=no smooth, 1=instant change)
MIN_VISIBLE_KEYPOINTS = 12     # Minimum keypoints needed to proceed with analysis

# Temporal analysis
SEQUENCE_LENGTH = 30           # Buffer length for temporal features (30 frames ≈ 1 second at 30 fps)

# Rep counting settings
CONSECUTIVE_CONFIRM = 3        # Number of consecutive frames needed to confirm a phase change

# Squat detection thresholds (knee angle in degrees)
SQUAT_DOWN_ANGLE = 100         # Below this angle = "down" position
SQUAT_UP_ANGLE = 160           # Above this angle = "up" position

# Arm circle detection
ARM_CIRCLE_ROTATION_TH = 300   # Total degrees of rotation to count as one complete circle

# Feedback settings
FEEDBACK_COOLDOWN = 2.0        # Seconds between vocal feedback messages (prevents spam)

# ========================================
# TEXT-TO-SPEECH SYSTEM (Thread-Safe)
# ========================================

# Create a queue for voice messages (allows non-blocking speech)
voice_q = queue.Queue()

# Initialize pyttsx3 text-to-speech engine
engine = pyttsx3.init()
engine.setProperty("rate", 160)  # Speech rate (words per minute)

def _voice_worker():
    """
    Background thread worker that processes the voice queue.
    
    HOW IT WORKS:
        - Runs in a separate thread to prevent blocking the main video loop
        - Continuously checks the queue for messages to speak
        - None message = signal to stop the worker
    
    WHY THREADED:
        - Speaking text is slow (blocks for 1-2 seconds)
        - Without threading, video would freeze during speech
        - Thread allows smooth video + concurrent speech
    """
    while True:
        text = voice_q.get()  # Wait for a message
        if text is None:      # None = shutdown signal
            break
        engine.say(text)      # Synthesize speech
        engine.runAndWait()   # Play audio (blocking in this thread only)
        voice_q.task_done()   # Mark task as complete

# Start the voice worker thread (daemon = auto-closes when main program exits)
threading.Thread(target=_voice_worker, daemon=True).start()

def speak(text):
    """
    Queue text to be spoken (non-blocking).
    
    PARAMETERS:
        text: String to be spoken aloud
    
    USAGE:
        speak("Good squat!")  # Returns immediately, speaks in background
    """
    if text:
        voice_q.put(text)

# ========================================
# LOAD POSE DETECTION MODEL
# ========================================

# Load YOLOv8 Pose model (nano version = fastest, good for real-time)
# Model automatically downloads if not present
# YOLOv8 detects 17 keypoints in COCO format:
#   0: nose, 1-2: eyes, 3-4: ears, 5-6: shoulders,
#   7-8: elbows, 9-10: wrists, 11-12: hips,
#   13-14: knees, 15-16: ankles
yolo = YOLO("yolov8n-pose.pt")  # lightweight pose model

# ========================================
# HELPER FUNCTIONS: Geometry & Smoothing
# ========================================

def safe_div(a, b, eps=1e-8):
    """
    Safe division that prevents division by zero.
    
    PARAMETERS:
        a: numerator
        b: denominator
        eps: small epsilon value to prevent division by zero
    
    RETURNS:
        a / (b + eps)
    """
    return a / (b + eps)

def compute_angle_deg(a, b, c):
    """
    Calculate the angle at point b formed by three points a-b-c.
    
    PARAMETERS:
        a, b, c: Points as (x, y) tuples or arrays
    
    RETURNS:
        Angle in degrees (0-180)
    
    EXAMPLE:
        For knee angle: hip-knee-ankle
        - 180° = straight leg
        - 90° = deep squat
    
    HOW IT WORKS:
        1. Calculate vectors ba and bc
        2. Use dot product to find cosine of angle
        3. Convert to degrees using arccos
    """
    a = np.array(a); b = np.array(b); c = np.array(c)
    ba = a - b  # Vector from b to a
    bc = c - b  # Vector from b to c
    
    # Calculate cosine of angle using dot product formula
    denom = (np.linalg.norm(ba) * np.linalg.norm(bc)) + 1e-8
    cosang = np.dot(ba, bc) / denom
    cosang = np.clip(cosang, -1.0, 1.0)  # Clamp to valid range
    
    return float(np.degrees(np.arccos(cosang)))

def wrap_angle_deg(a):
    """
    Normalize angle to the range [-180, 180].
    
    PARAMETERS:
        a: Angle in degrees
    
    RETURNS:
        Normalized angle in [-180, 180]
    
    USAGE:
        Used for circular angle calculations (e.g., arm rotation tracking)
    """
    return ((a + 180) % 360) - 180

def signed_angle_between(v1, v2):
    """
    Calculate signed angle from vector v1 to v2 in 2D.
    
    PARAMETERS:
        v1, v2: 2D vectors as (x, y)
    
    RETURNS:
        Signed angle in degrees (-180 to 180)
        Positive = counterclockwise rotation
        Negative = clockwise rotation
    
    USAGE:
        Used for tracking arm rotation direction
    """
    ang1 = math.atan2(v1[1], v1[0])
    ang2 = math.atan2(v2[1], v2[0])
    return math.degrees(wrap_angle_deg(math.degrees(ang2 - ang1)))

def smooth_kp(prev, new, alpha=SMOOTH_ALPHA):
    """
    Apply Exponential Weighted Moving Average (EWMA) smoothing to keypoints.
    
    PARAMETERS:
        prev: Previous keypoint array (or None for first frame)
        new: New keypoint array
        alpha: Smoothing factor (0-1)
               - 0 = keep old value (max smoothing)
               - 1 = use new value (no smoothing)
    
    RETURNS:
        Smoothed keypoint array
    
    WHY SMOOTHING:
        - Raw pose detection can be jittery frame-to-frame
        - Smoothing reduces noise and creates more stable measurements
        - Essential for accurate angle calculations
    """
    if prev is None:
        return new
    return alpha * new + (1 - alpha) * prev

# ========================================
# STATE MACHINES FOR EXERCISE TRACKING
# ========================================

class SquatState:
    """
    State machine for tracking squat repetitions.
    
    STATES:
        - "up": Standing position (knees extended)
        - "down": Squat position (knees bent)
    
    REP COUNTING:
        - One rep = complete cycle of up → down → up
        - Uses consecutive frame confirmation to prevent false triggers
    
    HOW IT WORKS:
        1. Start in "up" state
        2. When knee angle drops below down_th for CONSECUTIVE_CONFIRM frames → transition to "down"
        3. When knee angle rises above up_th for CONSECUTIVE_CONFIRM frames → transition to "up" + COUNT REP
        4. Hysteresis prevents rapid state switching
    """
    
    def __init__(self, down_th=SQUAT_DOWN_ANGLE, up_th=SQUAT_UP_ANGLE):
        """
        Initialize squat tracker.
        
        PARAMETERS:
            down_th: Knee angle threshold for "down" position (degrees)
            up_th: Knee angle threshold for "up" position (degrees)
        """
        self.state = "up"       # Current state: 'up' or 'down'
        self.down_th = down_th  # Threshold for detecting squat down
        self.up_th = up_th      # Threshold for detecting squat up
        self.counter = 0        # Consecutive frames in new state

    def update(self, avg_knee_angle):
        """
        Update state based on current knee angle.
        
        PARAMETERS:
            avg_knee_angle: Average of left and right knee angles (degrees)
        
        RETURNS:
            True if a rep was just completed, False otherwise
        
        STATE TRANSITIONS:
            up → down: When angle < down_th for CONSECUTIVE_CONFIRM frames
            down → up: When angle > up_th for CONSECUTIVE_CONFIRM frames (REP!)
        """
        rep = False
        
        if avg_knee_angle is None:
            self.counter = 0
            return False
        
        # State: UP (standing) - waiting to go down
        if self.state == "up":
            if avg_knee_angle < self.down_th:
                self.counter += 1
                if self.counter >= CONSECUTIVE_CONFIRM:
                    self.state = "down"  # Transition to down
                    self.counter = 0
            else:
                self.counter = 0  # Reset if angle goes back up
        
        # State: DOWN (squatting) - waiting to come up
        elif self.state == "down":
            if avg_knee_angle > self.up_th:
                self.counter += 1
                if self.counter >= CONSECUTIVE_CONFIRM:
                    self.state = "up"    # Transition to up
                    self.counter = 0
                    rep = True           # REP COMPLETED!
            else:
                self.counter = 0  # Reset if angle goes back down
        
        return rep

class ArmCircleState:
    """
    State machine for tracking arm circle repetitions.
    
    METHOD:
        - Tracks the angle of the arm vector relative to shoulder
        - Accumulates total rotation (in degrees) over time
        - Counts a rep when cumulative rotation exceeds threshold
    
    HOW IT WORKS:
        1. Calculate vector from shoulder center to wrist center
        2. Find angle of this vector (using atan2)
        3. Track change in angle from previous frame
        4. Accumulate absolute rotation
        5. When accumulated rotation > threshold (e.g., 300°) → COUNT REP
    
    WHY 300° AND NOT 360°:
        - Accounts for imperfect circles and measurement noise
        - Still captures full rotation without being too strict
    """
    
    def __init__(self, rotation_th=ARM_CIRCLE_ROTATION_TH):
        """
        Initialize arm circle tracker.
        
        PARAMETERS:
            rotation_th: Total degrees of rotation to count as one circle
        """
        self.cumulative = 0.0       # Total accumulated rotation (degrees)
        self.prev_angle = None      # Previous frame's arm angle
        self.rotation_th = rotation_th  # Threshold for one complete circle
        self.counter = 0            # Unused, kept for consistency

    def update(self, shoulder_center, wrist_center):
        """
        Update state based on current arm position.
        
        PARAMETERS:
            shoulder_center: (x, y) midpoint of left and right shoulders
            wrist_center: (x, y) midpoint of left and right wrists
        
        RETURNS:
            True if a complete circle was just detected, False otherwise
        
        TRACKING METHOD:
            1. Calculate arm vector (shoulder to wrist)
            2. Find angle using atan2
            3. Compare with previous angle
            4. Accumulate rotation
            5. Reset and count when threshold reached
        """
        if shoulder_center is None or wrist_center is None:
            self.prev_angle = None
            return False

        # Calculate vector from shoulders to wrists
        vec = wrist_center - shoulder_center
        
        # Calculate angle of this vector (in degrees)
        ang = math.degrees(math.atan2(vec[1], vec[0]))
        
        # First frame: just store the angle
        if self.prev_angle is None:
            self.prev_angle = ang
            return False

        # Calculate change in angle from previous frame
        delta = wrap_angle_deg(ang - self.prev_angle)
        
        # Accumulate absolute rotation (handles both clockwise and counterclockwise)
        self.cumulative += abs(delta)
        self.prev_angle = ang

        # Check if full circle completed
        if self.cumulative >= self.rotation_th:
            self.cumulative = 0.0  # Reset for next circle
            return True            # REP COMPLETED!
        
        return False

# ========================================
# FEEDBACK GENERATION SYSTEM
# ========================================

def feedback_generator(metrics, exercise, last_feedback_time):
    """
    Generate natural-language coaching feedback based on exercise metrics.
    
    PARAMETERS:
        metrics: Dictionary of joint angles (e.g., {"left_knee": 120, "right_knee": 115})
        exercise: String indicating current exercise ('Squat', 'Arm Circle', or None)
        last_feedback_time: Timestamp of last spoken feedback (for throttling)
    
    RETURNS:
        (screen_text, speak_text):
            - screen_text: String to display on screen (always provided)
            - speak_text: String to speak aloud (None if no speech needed)
    
    FEEDBACK RULES:
        
        SQUATS:
            - avg_knee > 140°: Too shallow → "Try going deeper"
            - avg_knee < 75°: Very deep → "Nice depth, control"
            - 75° ≤ avg_knee ≤ 140°: Good depth → "Good squat"
        
        ARM CIRCLES:
            - both elbows > 170°: Too straight → "Soften elbows"
            - Otherwise: Good form → "Nice rotation"
    
    THROTTLING:
        - Vocal feedback only given if FEEDBACK_COOLDOWN seconds have passed
        - Prevents annoying repetition
        - Screen text updates every frame
    """
    now = time.time()
    speak_text = None
    screen_text = []

    # ========================================
    # SQUAT FEEDBACK
    # ========================================
    if exercise == "Squat":
        lk, rk = metrics.get("left_knee"), metrics.get("right_knee")
        
        # Check if we can measure knees
        if lk is None or rk is None:
            screen_text.append("Can't measure squat - reposition")
        else:
            avg_knee = (lk + rk) / 2.0
            
            # Display current knee angles
            screen_text.append(f"Knees: L{int(lk)}° R{int(rk)}")
            
            # Feedback based on squat depth
            if avg_knee > 140:
                # Too shallow
                screen_text.append("Try going deeper.")
                if now - last_feedback_time > FEEDBACK_COOLDOWN:
                    speak_text = "Try lowering a bit more to hit full depth."
            
            elif avg_knee < 75:
                # Very deep squat
                screen_text.append("Nice depth, control the movement.")
                if now - last_feedback_time > FEEDBACK_COOLDOWN:
                    speak_text = "Good depth. Keep control on the way up."
            
            else:
                # Good depth (75-140°)
                screen_text.append("Good squat depth.")
                if now - last_feedback_time > FEEDBACK_COOLDOWN:
                    speak_text = "Good squat. Keep your chest up."
    
    # ========================================
    # ARM CIRCLE FEEDBACK
    # ========================================
    elif exercise == "Arm Circle":
        le, re = metrics.get("left_elbow"), metrics.get("right_elbow")
        
        # Check if we can measure elbows
        if le is None or re is None:
            screen_text.append("Can't measure arms - reposition")
        else:
            # Display current elbow angles
            screen_text.append(f"Elbows: L{int(le)}° R{int(re)}")
            
            # Encourage slight bend if arms fully straight (prevents shoulder strain)
            if le > 170 and re > 170:
                screen_text.append("Soften your elbows a little.")
                if now - last_feedback_time > FEEDBACK_COOLDOWN:
                    speak_text = "Bend your elbows slightly so your shoulders aren't strained."
            else:
                screen_text.append("Nice arm circle.")
                if now - last_feedback_time > FEEDBACK_COOLDOWN:
                    speak_text = "Nice rotation, keep a smooth pace."
    
    # ========================================
    # NO EXERCISE DETECTED
    # ========================================
    else:
        screen_text.append("No exercise detected.")
    
    return " | ".join(screen_text), speak_text

def compare_to_reference(current_angles, reference_angles, avg_knee):
    """
    Compare current angles to phase-matched reference and return deviation feedback.
    """
    # Determine current phase
    if avg_knee > 160:
        phase = "top"
    elif avg_knee > 100:
        phase = "mid"
    else:
        phase = "bottom"

    if phase not in reference_angles:
        return f"No reference for {phase} phase", None

    ref = reference_angles[phase]
    messages = []
    for joint, cur_val in current_angles.items():
        if joint in ref:
            diff = cur_val - ref[joint]
            if abs(diff) > ANGLE_TOLERANCE:
                direction = "higher" if diff > 0 else "lower"
                messages.append(f"{joint.replace('_', ' ').title()} {direction} by {abs(int(diff))}°")
    
    if not messages:
        return f"Good {phase} position!", "Good form, match reference."
    else:
        return " | ".join(messages), None


# ========================================
# MAIN REAL-TIME LOOP INITIALIZATION
# ========================================

# Open video capture (webcam or video file)
cap = cv2.VideoCapture(VIDEO_SOURCE)

# Create display window
cv2.namedWindow("AI Coach", cv2.WINDOW_NORMAL)
cv2.resizeWindow("AI Coach", 1280, 720)

# Initialize exercise state trackers
squat_state = SquatState()       # Tracks squat up/down state and counts reps
arm_state = ArmCircleState()     # Tracks arm rotation and counts circles

# Smoothing and buffering
kp_smooth_prev = None            # Previous frame's keypoints for smoothing
seq_buffer = deque(maxlen=SEQUENCE_LENGTH)  # Buffer for temporal features (future ML use)

# Rep counting
rep_counts = {"Squat": 0, "Arm Circle": 0}

# Feedback throttling
last_spoken_time = 0.0           # Timestamp of last vocal feedback
last_spoken_message = ""         # Last message spoken (to avoid repeats)

# User controls
print("Starting AI Coach. Press 'q' to quit, 'c' to recalibrate (capture scale), 'p' to toggle pause.")

# State flags
paused = False                   # Pause/resume video processing
calibrated = False               # Whether scale has been calibrated
scale_calib = 1.0                # Calibrated scale factor (shoulder width)

# ========================================
# MAIN VIDEO PROCESSING LOOP
# ========================================

while True:
    # ----------------------------------------
    # STEP 1: CAPTURE FRAME
    # ----------------------------------------
    ret, frame = cap.read()
    if not ret:
        break  # End of video or camera disconnected

    # ----------------------------------------
    # STEP 2: HANDLE KEYBOARD INPUT
    # ----------------------------------------
    key = cv2.waitKey(1)
    
    if key == ord('q'):  # Quit
        break
    
    if key == ord('p'):  # Pause/Resume
        paused = not paused
    
    if key == ord('c'):  # Calibrate scale
        """
        Calibration captures the shoulder width to use as a reference scale.
        This makes measurements more accurate for different body sizes.
        
        HOW TO USE:
            1. Stand fully in frame
            2. Press 'c'
            3. System captures your shoulder width as reference
        """
        results = yolo(frame)
        if results and len(results[0].keypoints) > 0:
            kps = results[0].keypoints.xy[0].cpu().numpy()
            if kps.shape[0] >= 13:
                # COCO keypoints: 5=left shoulder, 6=right shoulder
                left_sh = kps[5]
                right_sh = kps[6]
                scale_calib = np.linalg.norm(left_sh - right_sh)
                calibrated = True
                print(f"Calibrated scale {scale_calib:.2f}")
    
    # Handle pause state
    if paused:
        cv2.putText(frame, "PAUSED (press 'p' to resume)", (20,40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,200,255), 2)
        cv2.imshow("AI Coach", frame)
        continue

    # ----------------------------------------
    # STEP 3: RUN POSE DETECTION
    # ----------------------------------------
    
    # Run YOLOv8 pose detection on the frame
    # Returns keypoints + confidence scores
    results = yolo(frame)
    
    # Check if person detected
    if not results or len(results[0].keypoints) == 0:
        cv2.putText(frame, "Person not detected", (20,70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 2)
        cv2.imshow("AI Coach", frame)
        continue

    # ----------------------------------------
    # STEP 4: EXTRACT AND VALIDATE KEYPOINTS
    # ----------------------------------------
    
    # Extract keypoints for first detected person
    kp_array = results[0].keypoints.xy[0].cpu().numpy()   # shape (17, 2) - x,y coordinates
    confs = results[0].keypoints.conf[0].cpu().numpy()     # shape (17,) - confidence scores
    
    # Filter by confidence threshold (0.2 = 20% confidence minimum)
    visible_mask = confs > 0.2
    
    # Check if enough keypoints are visible
    if np.sum(visible_mask) < MIN_VISIBLE_KEYPOINTS:
        cv2.putText(frame, "Please fully enter the frame", (20,70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 2)
        cv2.imshow("AI Coach", frame)
        continue

    # Build a 17x3 array: (x, y, confidence)
    # Similar to MoveNet format for consistency
    kps_xy = kp_array
    kps_conf = confs
    keypoints = np.concatenate([kps_xy, kps_conf.reshape(-1,1)], axis=1)  # shape (17, 3)

    # ----------------------------------------
    # STEP 5: SMOOTH KEYPOINTS
    # ----------------------------------------
    
    # Apply EWMA smoothing to reduce jitter
    kp_smooth = smooth_kp(kp_smooth_prev, keypoints, alpha=SMOOTH_ALPHA)
    kp_smooth_prev = kp_smooth.copy()

    # ----------------------------------------
    # STEP 6: NORMALIZATION (Position & Scale Invariant)
    # ----------------------------------------
    
    # Get indices of visible keypoints
    visible_idxs = np.where(kp_smooth[:,2] > 0.2)[0]
    
    if len(visible_idxs) < MIN_VISIBLE_KEYPOINTS:
        cv2.putText(frame, "Keypoints incomplete - reposition", (20,70), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 2)
        cv2.imshow("AI Coach", frame)
        continue

    # Calculate center point (for position invariance)
    center = np.mean(kp_smooth[visible_idxs, :2], axis=0)
    
    # Calculate scale factor (for size invariance)
    if calibrated and scale_calib > 0:
        # Use calibrated scale if available
        scale = scale_calib
    else:
        # Fallback: use shoulder distance as scale
        # COCO indices: 5=left shoulder, 6=right shoulder
        try:
            scale = np.linalg.norm(kp_smooth[5,:2] - kp_smooth[6,:2])
            if scale < 1e-6: 
                scale = 1.0
        except:
            scale = 1.0

    # Normalize coordinates (centered and scaled)
    # Not strictly necessary for angle-based feedback, but useful for future ML integration
    norm_xy = (kp_smooth[:,:2] - center) / (scale + 1e-8)

    # ----------------------------------------
    # STEP 7: COMPUTE JOINT ANGLES
    # ----------------------------------------
    
    """
    Calculate angles for key joints using smoothed keypoints.
    
    COCO KEYPOINT INDICES (YOLOv8-Pose):
        5: left shoulder    6: right shoulder
        7: left elbow       8: right elbow
        9: left wrist      10: right wrist
       11: left hip        12: right hip
       13: left knee       14: right knee
       15: left ankle      16: right ankle
    """
    
    angles = {}
    try:
        # KNEE ANGLES (for squat detection)
        # Left knee: hip -> knee -> ankle
        angles["left_knee"] = compute_angle_deg(
            kp_smooth[11,:2],  # left hip
            kp_smooth[13,:2],  # left knee
            kp_smooth[15,:2]   # left ankle
        )
        
        # Right knee: hip -> knee -> ankle
        angles["right_knee"] = compute_angle_deg(
            kp_smooth[12,:2],  # right hip
            kp_smooth[14,:2],  # right knee
            kp_smooth[16,:2]   # right ankle
        )
        
        # ELBOW ANGLES (for arm circle feedback)
        # Left elbow: shoulder -> elbow -> wrist
        angles["left_elbow"] = compute_angle_deg(
            kp_smooth[5,:2],   # left shoulder
            kp_smooth[7,:2],   # left elbow
            kp_smooth[9,:2]    # left wrist
        )
        
        # Right elbow: shoulder -> elbow -> wrist
        angles["right_elbow"] = compute_angle_deg(
            kp_smooth[6,:2],   # right shoulder
            kp_smooth[8,:2],   # right elbow
            kp_smooth[10,:2]   # right wrist
        )
        
        # CENTER POINTS (for arm circle rotation tracking)
        shoulder_center = (kp_smooth[5,:2] + kp_smooth[6,:2]) / 2.0
        wrist_center = (kp_smooth[9,:2] + kp_smooth[10,:2]) / 2.0
        
    except Exception as e:
        # If keypoint indexing fails, skip this frame
        print("Kinematics error:", e)
        continue

    # ----------------------------------------
    # STEP 8: UPDATE STATE MACHINES & COUNT REPS
    # ----------------------------------------
    
    # Calculate average knee angle for squat detection
    avg_knee = (angles["left_knee"] + angles["right_knee"]) / 2.0
    
    # Update squat state machine
    squat_rep = squat_state.update(avg_knee)
    
    # Update arm circle state machine
    arm_rep = arm_state.update(shoulder_center, wrist_center)

    # Handle rep completion
    if squat_rep:
        rep_counts["Squat"] += 1
        speak("Nice squat. Rep counted.")
        last_spoken_time = time.time()
    
    if arm_rep:
        rep_counts["Arm Circle"] += 1
        speak("Nice circle. Rep counted.")
        last_spoken_time = time.time()

    # ----------------------------------------
    # STEP 9: GENERATE FEEDBACK
    # ----------------------------------------
    
    # Determine which exercise is being performed
    # Simple heuristic: if avg knee < 120°, assume squatting
    # If arm rotation accumulating, assume arm circles
    current_exercise = None
    if avg_knee < 120:
        current_exercise = "Squat"
    elif arm_state.cumulative > 0:
        current_exercise = "Arm Circle"
    
    # Generate feedback (screen text + optional speech)
    screen_msg, suggested_speak = feedback_generator(
        angles, 
        current_exercise, 
        last_spoken_time
    )
    
    # Speak suggested feedback if available and not recently spoken
    if suggested_speak and (time.time() - last_spoken_time) > FEEDBACK_COOLDOWN:
        speak(suggested_speak)
        last_spoken_time = time.time()

    # ----------------------------------------
    # STEP 10: RENDER VISUAL OVERLAYS
    # ----------------------------------------
    
    # Draw keypoints on frame
    for i, (x, y, c) in enumerate(kp_smooth):
        if c > 0.2:  # Only draw visible keypoints
            cv2.circle(frame, (int(x), int(y)), 4, (0,255,0), -1)
    
    # Display rep counts
    cv2.putText(frame, f"Squat reps: {rep_counts['Squat']}", 
               (20,40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,0), 2)
    cv2.putText(frame, f"Arm reps: {rep_counts['Arm Circle']}", 
               (20,80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,0), 2)
    
    # Display feedback message
    cv2.putText(frame, f"{screen_msg}", 
               (20,120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,0), 2)

    # Show the frame
    cv2.imshow("AI Coach", frame)

# ========================================
# CLEANUP
# ========================================

# Release video capture
cap.release()

# Close all OpenCV windows
cv2.destroyAllWindows()

# Stop the voice worker thread
voice_q.put(None)

print("\nAI Coach session ended.")
print(f"Final rep counts: Squats={rep_counts['Squat']}, Arm Circles={rep_counts['Arm Circle']}")
