import cv2
import numpy as np
import time
import os
from collections import deque
from ultralytics import YOLO

# Import exercise-specific modules
from exercises.squat import SquatState, SquatReferenceChecker, generate_squat_feedback
from exercises.arm_circle_stage_1 import ArmCircleState, generate_arm_circle_feedback

# Import arm circle for level 1

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

# Feedback settings
FEEDBACK_COOLDOWN = 2.0        # Seconds between vocal feedback messages (prevents spam)

# ========================================
# LOAD POSE DETECTION MODEL
# ========================================

# Load YOLOv8 Pose model (nano version = fastest, good for real-time)
# YOLOv8 detects 17 keypoints in COCO format:
#   0: nose, 1-2: eyes, 3-4: ears, 5-6: shoulders,
#   7-8: elbows, 9-10: wrists, 11-12: hips,
#   13-14: knees, 15-16: ankles

# Use existing model from ./models/yolov8n-pose.pt
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "yolov8n-pose.pt")
if not os.path.exists(MODEL_PATH):
    # Fallback to other common locations
    alt_path = os.path.join(os.path.dirname(__file__), "yolov8n-pose.pt")
    if os.path.exists(alt_path):
        MODEL_PATH = alt_path
    else:
        print(f"⚠️  Model not found at {MODEL_PATH}")
        print(f"   Please ensure yolov8n-pose.pt is in the models/ directory")

print(f"✓ Loading model from: {MODEL_PATH}")
yolo = YOLO(MODEL_PATH)  # lightweight pose model

# ========================================
# HELPER FUNCTIONS: Geometry & Smoothing
# ========================================

def safe_div(a, b, eps=1e-8):
    """Safe division that prevents division by zero."""
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
    Used for circular angle calculations (e.g., arm rotation tracking)
    """
    return ((a + 180) % 360) - 180

def smooth_kp(prev, new, alpha=SMOOTH_ALPHA):
    """
    Apply Exponential Weighted Moving Average (EWMA) smoothing to keypoints.
    
    WHY SMOOTHING:
        - Raw pose detection can be jittery frame-to-frame
        - Smoothing reduces noise and creates more stable measurements
        - Essential for accurate angle calculations
    """
    if prev is None:
        return new
    return alpha * new + (1 - alpha) * prev


# Add method to get current session from user input
def current_session():
    """
    Prompt user to select exercise type.
    
    RETURNS:
        String: "Squat", "Arm Circle", or "Both"
    """
    print("\n" + "="*60)
    print("SELECT EXERCISE")
    print("="*60)
    print("1. Squat")
    print("2. Arm Circle (Stage 1 - Recovery)")
    print("3. Both")
    print("="*60)
    
    while True:
        choice = input("Enter your choice (1-3): ").strip()
        
        if choice == "1":
            return "Squat"
        elif choice == "2":
            return "Arm Circle"
        elif choice == "3":
            return "Both"
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")

# ========================================
# MAIN EXECUTION
# ========================================

def main():
    """Main function to run the AI Coach."""
    
    # User selects exercise
    selected_exercise = current_session()
    
    # ========================================
    # MAIN REAL-TIME LOOP INITIALIZATION
    # ========================================
    
    # Open video capture (webcam or video file)
    cap = cv2.VideoCapture(VIDEO_SOURCE)
    
    # Create display window
    cv2.namedWindow("AI Coach", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("AI Coach", 1280, 720)
    
    # Initialize exercise state trackers based on selection
    squat_state = None
    arm_state = None
    squat_checker = None
    
    if selected_exercise in ["Squat", "Both"]:
        squat_state = SquatState()
        try:
            squat_checker = SquatReferenceChecker()
        except:
            print("⚠️  Could not load reference checker, using simple rules")
            squat_checker = None
    
    if selected_exercise in ["Arm Circle", "Both"]:
        arm_state = ArmCircleState()
    
    # Smoothing and buffering
    kp_smooth_prev = None
    seq_buffer = deque(maxlen=SEQUENCE_LENGTH)
    
    # Rep counting
    rep_counts = {"Squat": 0, "Arm Circle": 0}
    
    # # Feedback throttling
    # last_spoken_time = 0.0
    # last_spoken_message = ""
    
    # User controls
    print("\n" + "="*60)
    print("STARTING AI COACH")
    print("="*60)
    print(f"Exercise: {selected_exercise}")
    print("\nControls:")
    print("  'q' - Quit")
    print("  'p' - Pause/Resume")
    print("  'c' - Calibrate (capture scale)")
    print("="*60 + "\n")
    
    # State flags
    paused = False
    calibrated = False
    scale_calib = 1.0
    
    # ========================================
    # MAIN VIDEO PROCESSING LOOP
    # ========================================
    
    while True:
        # STEP 1: CAPTURE FRAME
        ret, frame = cap.read()
        if not ret:
            break
    
        # STEP 2: HANDLE KEYBOARD INPUT
        key = cv2.waitKey(1)
        
        if key == ord('q'):  # Quit
            break
        
        if key == ord('p'):  # Pause/Resume
            paused = not paused
        
        if key == ord('c'):  # Calibrate scale
            results = yolo(frame)
            if results and len(results[0].keypoints) > 0:
                kps = results[0].keypoints.xy[0].cpu().numpy()
                if kps.shape[0] >= 13:
                    left_sh = kps[5]
                    right_sh = kps[6]
                    scale_calib = np.linalg.norm(left_sh - right_sh)
                    calibrated = True
                    print(f"✓ Calibrated scale: {scale_calib:.2f}")
        
        # Handle pause state
        if paused:
            cv2.putText(frame, "PAUSED (press 'p' to resume)", (20,40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,200,255), 2)
            cv2.imshow("AI Coach", frame)
            continue
    
        # STEP 3: RUN POSE DETECTION
        results = yolo(frame)
        
        if not results or len(results[0].keypoints) == 0:
            cv2.putText(frame, "Person not detected", (20,70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 2)
            cv2.imshow("AI Coach", frame)
            continue
    
        # STEP 4: EXTRACT AND VALIDATE KEYPOINTS
        kp_array = results[0].keypoints.xy[0].cpu().numpy()
        confs = results[0].keypoints.conf[0].cpu().numpy()
        
        visible_mask = confs > 0.2
        
        if np.sum(visible_mask) < MIN_VISIBLE_KEYPOINTS:
            cv2.putText(frame, "Please fully enter the frame", (20,70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 2)
            cv2.imshow("AI Coach", frame)
            continue
    
        keypoints = np.concatenate([kp_array, confs.reshape(-1,1)], axis=1)
    
        # STEP 5: SMOOTH KEYPOINTS
        kp_smooth = smooth_kp(kp_smooth_prev, keypoints, alpha=SMOOTH_ALPHA)
        kp_smooth_prev = kp_smooth.copy()
    
        # STEP 6: NORMALIZATION
        visible_idxs = np.where(kp_smooth[:,2] > 0.2)[0]
        
        if len(visible_idxs) < MIN_VISIBLE_KEYPOINTS:
            cv2.putText(frame, "Keypoints incomplete - reposition", (20,70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 2)
            cv2.imshow("AI Coach", frame)
            continue
    
        center = np.mean(kp_smooth[visible_idxs, :2], axis=0)
        
        if calibrated and scale_calib > 0:
            scale = scale_calib
        else:
            try:
                scale = np.linalg.norm(kp_smooth[5,:2] - kp_smooth[6,:2])
                if scale < 1e-6: 
                    scale = 1.0
            except:
                scale = 1.0
    
        norm_xy = (kp_smooth[:,:2] - center) / (scale + 1e-8)
    
        # STEP 7: COMPUTE JOINT ANGLES
        angles = {}
        try:
            # KNEE ANGLES (for squat detection)
            angles["left_knee"] = compute_angle_deg(
                kp_smooth[11,:2],  # left hip
                kp_smooth[13,:2],  # left knee
                kp_smooth[15,:2]   # left ankle
            )
            
            angles["right_knee"] = compute_angle_deg(
                kp_smooth[12,:2],  # right hip
                kp_smooth[14,:2],  # right knee
                kp_smooth[16,:2]   # right ankle
            )
            
            # TORSO ANGLES (shoulder to hip - for body straightness in squats)
            # Calculate angle from average shoulder to average hip
            left_torso = compute_angle_deg(
                kp_smooth[5,:2],   # left shoulder
                kp_smooth[11,:2],  # left hip
                kp_smooth[13,:2]   # left knee (reference point)
            )
            
            right_torso = compute_angle_deg(
                kp_smooth[6,:2],   # right shoulder
                kp_smooth[12,:2],  # right hip
                kp_smooth[14,:2]   # right knee (reference point)
            )
            
            angles["torso"] = (left_torso + right_torso) / 2.0
            
            # ELBOW ANGLES (for arm circle feedback)
            angles["left_elbow"] = compute_angle_deg(
                kp_smooth[5,:2],   # left shoulder
                kp_smooth[7,:2],   # left elbow
                kp_smooth[9,:2]    # left wrist
            )
            
            angles["right_elbow"] = compute_angle_deg(
                kp_smooth[6,:2],   # right shoulder
                kp_smooth[8,:2],   # right elbow
                kp_smooth[10,:2]   # right wrist
            )
            
            # ARM ANGLES (for arm circle - angle from vertical when arms are raised)
            # Calculate angle of arm relative to torso/vertical
            # Using shoulder, elbow, hip as reference points
            angles["left_arm_angle"] = compute_angle_deg(
                kp_smooth[11,:2],  # left hip (vertical reference)
                kp_smooth[5,:2],   # left shoulder
                kp_smooth[9,:2]    # left wrist
            )
            
            angles["right_arm_angle"] = compute_angle_deg(
                kp_smooth[12,:2],  # right hip (vertical reference)
                kp_smooth[6,:2],   # right shoulder
                kp_smooth[10,:2]   # right wrist
            )
            
            # CENTER POINTS (for arm circle rotation tracking)
            shoulder_center = (kp_smooth[5,:2] + kp_smooth[6,:2]) / 2.0
            wrist_center = (kp_smooth[9,:2] + kp_smooth[10,:2]) / 2.0
            
        except Exception as e:
            print("Kinematics error:", e)
            continue
    
        # STEP 8: UPDATE STATE MACHINES & COUNT REPS
        squat_rep = False
        arm_rep = False
        
        # Update squat state machine
        if squat_state:
            avg_knee = (angles["left_knee"] + angles["right_knee"]) / 2.0
            squat_rep = squat_state.update(avg_knee)
            if squat_rep:
                rep_counts["Squat"] += 1
                print(f"✓ Squat rep completed! Total: {rep_counts['Squat']}")
        
        # Update arm circle state machine
        if arm_state:
            avg_arm_angle = (angles["left_arm_angle"] + angles["right_arm_angle"]) / 2.0
            arm_rep = arm_state.update(avg_arm_angle)
            if arm_rep:
                rep_counts["Arm Circle"] += 1
                print(f"✓ Arm circle rep completed! Total: {rep_counts['Arm Circle']}")
    
        # STEP 9: RENDER VISUAL OVERLAYS
        # Draw keypoints on frame
        for i, (x, y, c) in enumerate(kp_smooth):
            if c > 0.2:
                cv2.circle(frame, (int(x), int(y)), 4, (0,255,0), -1)
        
        # Display rep counts
        y_pos = 40
        if selected_exercise in ["Squat", "Both"]:
            cv2.putText(frame, f"Squat reps: {rep_counts['Squat']}", 
                       (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,0), 2)
            y_pos += 40
        
        if selected_exercise in ["Arm Circle", "Both"]:
            cv2.putText(frame, f"Arm reps: {rep_counts['Arm Circle']}", 
                       (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,0), 2)
            y_pos += 40
        
        # STEP 10: GENERATE AND DISPLAY FEEDBACK
        feedback_text = ""
        
        # Generate feedback based on selected exercise
        if selected_exercise == "Squat" and squat_state:
            feedback_text = generate_squat_feedback(angles, time.time())
        
        elif selected_exercise == "Arm Circle" and arm_state:
            feedback_text = generate_arm_circle_feedback(angles, time.time())
        
        elif selected_exercise == "Both":
            # Show feedback for both exercises (split display)
            squat_feedback = generate_squat_feedback(angles, time.time()) if squat_state else ""
            arm_feedback = generate_arm_circle_feedback(angles, time.time()) if arm_state else ""
            feedback_text = f"SQUAT: {squat_feedback}\nARM: {arm_feedback}"
        
        # Display feedback on screen
        if feedback_text:
            # Split multi-line feedback
            feedback_lines = feedback_text.split('\n')
            for i, line in enumerate(feedback_lines):
                cv2.putText(frame, line, 
                           (20, y_pos + (i * 35)), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,200,255), 2)
    
        # Show the frame
        cv2.imshow("AI Coach", frame)
    
    # ========================================
    # CLEANUP
    # ========================================
    
    cap.release()
    cv2.destroyAllWindows()
    
    print("\n" + "="*60)
    print("AI COACH SESSION ENDED")
    print("="*60)
    print(f"Final rep counts:")
    if selected_exercise in ["Squat", "Both"]:
        print(f"  Squats: {rep_counts['Squat']}")
    if selected_exercise in ["Arm Circle", "Both"]:
        print(f"  Arm Circles: {rep_counts['Arm Circle']}")
    print("="*60 + "\n")

# ========================================
# RUN
# ========================================

if __name__ == "__main__":
    main()
