# ai_coach_yolov8_pose.py
import cv2
import numpy as np
import time
import threading
import queue
import math
from collections import deque
from ultralytics import YOLO
import pyttsx3

# -----------------------------
# USER / SYSTEM PARAMETERS
VIDEO_SOURCE = 0
FRAME_SKIP = 1                 # process every N-th frame (increase for speed)
SMOOTH_ALPHA = 0.35            # smoothing factor (EWMA) for keypoints
MIN_VISIBLE_KEYPOINTS = 12     # require at least this many detected keypoints
SEQUENCE_LENGTH = 30           # buffer length for temporal features
CONSECUTIVE_CONFIRM = 3        # frames to confirm detected phase/rep
SQUAT_DOWN_ANGLE = 100         # knee angle threshold (deg) for "down"
SQUAT_UP_ANGLE = 160           # knee angle threshold (deg) for "up"
ARM_CIRCLE_ROTATION_TH = 300   # degrees accumulated to count one circle
FEEDBACK_COOLDOWN = 2.0        # seconds between same vocal feedback messages

# -----------------------------
# TTS queue & worker (thread-safe)
voice_q = queue.Queue()
engine = pyttsx3.init()
engine.setProperty("rate", 160)

def _voice_worker():
    while True:
        text = voice_q.get()
        if text is None:
            break
        engine.say(text)
        engine.runAndWait()
        voice_q.task_done()

threading.Thread(target=_voice_worker, daemon=True).start()

def speak(text):
    """Queue text to be spoken (non-blocking)."""
    if text:
        voice_q.put(text)

# -----------------------------
# Load YOLOv8 Pose (nano pose recommended)
# model file name assumes you have 'yolov8n-pose.pt' available (ultralytics will download if needed)
yolo = YOLO("yolov8n-pose.pt")  # lightweight pose model

# -----------------------------
# Helpers: geometry & smoothing
def safe_div(a, b, eps=1e-8):
    return a / (b + eps)

def compute_angle_deg(a, b, c):
    """Angle at b formed by points a-b-c in degrees"""
    a = np.array(a); b = np.array(b); c = np.array(c)
    ba = a - b
    bc = c - b
    denom = (np.linalg.norm(ba) * np.linalg.norm(bc)) + 1e-8
    cosang = np.dot(ba, bc) / denom
    cosang = np.clip(cosang, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosang)))

def wrap_angle_deg(a):
    """Normalize angle to [-180, 180]"""
    return ((a + 180) % 360) - 180

def signed_angle_between(v1, v2):
    """Signed angle (deg) from v1 to v2 in 2D using atan2"""
    ang1 = math.atan2(v1[1], v1[0])
    ang2 = math.atan2(v2[1], v2[0])
    return math.degrees(wrap_angle_deg(math.degrees(ang2 - ang1)))

def smooth_kp(prev, new, alpha=SMOOTH_ALPHA):
    """EWMA smoothing: prev may be None"""
    if prev is None:
        return new
    return alpha * new + (1 - alpha) * prev

# -----------------------------
# State machines / trackers
class SquatState:
    def __init__(self, down_th=SQUAT_DOWN_ANGLE, up_th=SQUAT_UP_ANGLE):
        self.state = "up"   # 'up' or 'down'
        self.down_th = down_th
        self.up_th = up_th
        self.counter = 0    # consecutive confirm frames

    def update(self, avg_knee_angle):
        # returns True when a rep is counted on transition down->up
        rep = False
        if avg_knee_angle is None:
            self.counter = 0
            return False
        if self.state == "up":
            if avg_knee_angle < self.down_th:
                self.counter += 1
                if self.counter >= CONSECUTIVE_CONFIRM:
                    self.state = "down"
                    self.counter = 0
            else:
                self.counter = 0
        elif self.state == "down":
            if avg_knee_angle > self.up_th:
                self.counter += 1
                if self.counter >= CONSECUTIVE_CONFIRM:
                    self.state = "up"
                    self.counter = 0
                    rep = True
            else:
                self.counter = 0
        return rep

class ArmCircleState:
    def __init__(self, rotation_th=ARM_CIRCLE_ROTATION_TH):
        self.cumulative = 0.0
        self.prev_angle = None
        self.rotation_th = rotation_th
        self.counter = 0

    def update(self, shoulder_center, wrist_center):
        """
        shoulder_center: (x,y) midpoint of shoulders
        wrist_center: (x,y) midpoint of wrists
        returns True when enough rotation accumulated -> a circle
        """
        if shoulder_center is None or wrist_center is None:
            self.prev_angle = None
            return False

        vec = wrist_center - shoulder_center
        ang = math.degrees(math.atan2(vec[1], vec[0]))
        if self.prev_angle is None:
            self.prev_angle = ang
            return False

        delta = wrap_angle_deg(ang - self.prev_angle)
        self.cumulative += abs(delta)
        self.prev_angle = ang

        if self.cumulative >= self.rotation_th:
            self.cumulative = 0.0
            return True
        return False

# -----------------------------
# Natural-language feedback templates
def feedback_generator(metrics, exercise, last_feedback_time):
    """
    metrics: dict of angles and simple measures
    exercise: 'Squat' | 'Arm Circle' | None
    last_feedback_time: timestamp of last spoken feedback (to throttle)
    returns: (text_for_screen, text_to_speak_or_None)
    """
    now = time.time()
    speak_text = None
    screen_text = []

    if exercise == "Squat":
        lk, rk = metrics.get("left_knee"), metrics.get("right_knee")
        if lk is None or rk is None:
            screen_text.append("Can't measure squat - reposition")
        else:
            avg_knee = (lk + rk) / 2.0
            screen_text.append(f"Knees: L{int(lk)}° R{int(rk)}")
            if avg_knee > 140:
                screen_text.append("Try going deeper.")
                if now - last_feedback_time > FEEDBACK_COOLDOWN:
                    speak_text = "Try lowering a bit more to hit full depth."
            elif avg_knee < 75:
                screen_text.append("Nice depth, control the movement.")
                if now - last_feedback_time > FEEDBACK_COOLDOWN:
                    speak_text = "Good depth. Keep control on the way up."
            else:
                screen_text.append("Good squat depth.")
                if now - last_feedback_time > FEEDBACK_COOLDOWN:
                    speak_text = "Good squat. Keep your chest up."
    elif exercise == "Arm Circle":
        le, re = metrics.get("left_elbow"), metrics.get("right_elbow")
        if le is None or re is None:
            screen_text.append("Can't measure arms - reposition")
        else:
            screen_text.append(f"Elbows: L{int(le)}° R{int(re)}")
            # Encourage slight bend if arms fully straight
            if le > 170 and re > 170:
                screen_text.append("Soften your elbows a little.")
                if now - last_feedback_time > FEEDBACK_COOLDOWN:
                    speak_text = "Bend your elbows slightly so your shoulders aren't strained."
            else:
                screen_text.append("Nice arm circle.")
                if now - last_feedback_time > FEEDBACK_COOLDOWN:
                    speak_text = "Nice rotation, keep a smooth pace."
    else:
        screen_text.append("No exercise detected.")
    return " | ".join(screen_text), speak_text

# -----------------------------
# Main real-time loop
cap = cv2.VideoCapture(VIDEO_SOURCE)
cv2.namedWindow("AI Coach", cv2.WINDOW_NORMAL)
cv2.resizeWindow("AI Coach", 1280, 720)

squat_state = SquatState()
arm_state = ArmCircleState()
kp_smooth_prev = None
seq_buffer = deque(maxlen=SEQUENCE_LENGTH)

rep_counts = {"Squat":0, "Arm Circle":0}
last_spoken_time = 0.0
last_spoken_message = ""

print("Starting AI Coach. Press 'q' to quit, 'c' to recalibrate (capture scale), 'p' to toggle pause.")

paused = False
calibrated = False
scale_calib = 1.0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    key = cv2.waitKey(1)
    if key == ord('q'):  # quit
        break
    if key == ord('p'):
        paused = not paused
    if key == ord('c'):
        # calibration - user stand in frame, capture shoulder distance as scale proxy
        results = yolo(frame)
        if results and len(results[0].keypoints) > 0:
            kps = results[0].keypoints.xy[0].cpu().numpy()
            if kps.shape[0] >= 13:
                # shoulder points indices in yolov8-pose may differ, we try approximate indexes (left/right shoulder)
                # ultralytics uses COCO keypoint ordering; adapt if needed
                left_sh = kps[5]; right_sh = kps[6]
                scale_calib = np.linalg.norm(left_sh - right_sh)
                calibrated = True
                print(f"Calibrated scale {scale_calib:.2f}")
    if paused:
        cv2.putText(frame, "PAUSED (press 'p' to resume)", (20,40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,200,255), 2)
        cv2.imshow("AI Coach", frame)
        continue

    # speed control: skip frames if needed
    # we still show the video every loop, but only process detection every FRAME_SKIP frames
    # if FRAME_SKIP > 1, we can still show intermediate frames without pose updates.
    # For simplicity we process every loop but user can set FRAME_SKIP higher to reduce CPU usage.

    # run YOLOv8-pose on the frame
    results = yolo(frame)
    if not results or len(results[0].keypoints) == 0:
        cv2.putText(frame, "Person not detected", (20,70), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 2)
        cv2.imshow("AI Coach", frame)
        continue

    # choose largest detected person (if multiple)
    kp_array = results[0].keypoints.xy[0].cpu().numpy()  # shape (N_kp, 2)
    confs = results[0].keypoints.conf[0].cpu().numpy()    # confidences
    # filter by confidence
    visible_mask = confs > 0.2
    if np.sum(visible_mask) < MIN_VISIBLE_KEYPOINTS:
        cv2.putText(frame, "Please fully enter the frame", (20,70), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 2)
        cv2.imshow("AI Coach", frame)
        continue

    # build a 17x3 array similar to MoveNet expectation: (x,y,conf)
    # ultralytics yields in COCO order: (x,y) per keypoint
    kps_xy = kp_array  # check ordering for your model - adjust indices as needed
    kps_conf = confs
    # Combine into K x 3
    keypoints = np.concatenate([kps_xy, kps_conf.reshape(-1,1)], axis=1)  # shape (K,3)

    # smoothing
    kp_smooth = smooth_kp(kp_smooth_prev, keypoints, alpha=SMOOTH_ALPHA)
    kp_smooth_prev = kp_smooth.copy()

    # normalize relative to visible center & scale (use shoulder width or calibration)
    visible_idxs = np.where(kp_smooth[:,2] > 0.2)[0]
    if len(visible_idxs) < MIN_VISIBLE_KEYPOINTS:
        cv2.putText(frame, "Keypoints incomplete - reposition", (20,70), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 2)
        cv2.imshow("AI Coach", frame)
        continue

    center = np.mean(kp_smooth[visible_idxs, :2], axis=0)
    if calibrated and scale_calib > 0:
        scale = scale_calib
    else:
        # shoulder distance (approx indices 5 and 6 for COCO) fallback
        try:
            scale = np.linalg.norm(kp_smooth[5,:2] - kp_smooth[6,:2])
            if scale < 1e-6: scale = 1.0
        except:
            scale = 1.0

    # Normalised XY for downstream use (not strictly necessary here but useful)
    norm_xy = (kp_smooth[:,:2] - center) / (scale + 1e-8)

    # compute angles & kinematic metrics (using raw smooth keypoints)
    angles = {}
    try:
        # COCO indexes: 11 left_hip, 12 right_hip, 13 left_knee, 14 right_knee, 15 left_ankle, 16 right_ankle
        # shoulders: 5 left_sh, 6 right_sh; elbows: 7,8; wrists 9,10
        angles["left_knee"] = compute_angle_deg(kp_smooth[11,:2], kp_smooth[13,:2], kp_smooth[15,:2])
        angles["right_knee"] = compute_angle_deg(kp_smooth[12,:2], kp_smooth[14,:2], kp_smooth[16,:2])
        angles["left_elbow"] = compute_angle_deg(kp_smooth[5,:2], kp_smooth[7,:2], kp_smooth[9,:2])
        angles["right_elbow"] = compute_angle_deg(kp_smooth[6,:2], kp_smooth[8,:2], kp_smooth[10,:2])
        # shoulder center & wrist center for arm circle detection
        shoulder_center = (kp_smooth[5,:2] + kp_smooth[6,:2]) / 2.0
        wrist_center = (kp_smooth[9,:2] + kp_smooth[10,:2]) / 2.0
    except Exception as e:
        # if keypoint indexing isn't matching your pose model, print and skip
        print("Kinematics error:", e)
        continue

    # update states & count reps
    avg_knee = (angles["left_knee"] + angles["right_knee"]) / 2.0
    squat_rep = squat_state.update(avg_knee)
    arm_rep = arm_state.update(shoulder_center, wrist_center)

    if squat_rep:
        rep_counts["Squat"] += 1
        speak("Nice squat. Rep counted.")
        last_spoken_time = time.time()
    if arm_rep:
        rep_counts["Arm Circle"] += 1
        speak("Nice circle. Rep counted.")
        last_spoken_time = time.time()

    # craft feedback (screen + optional speech)
    # throttle speech to avoid spam
    screen_msg, suggested_speak = feedback_generator(angles, 
                                                     "Squat" if avg_knee < 120 else "Arm Circle" if arm_state.cumulative>0 else None, 
                                                     last_spoken_time)
    # speak suggested if exists and not repeated
    if suggested_speak and (time.time() - last_spoken_time) > FEEDBACK_COOLDOWN:
        speak(suggested_speak)
        last_spoken_time = time.time()

    # overlay visuals
    # draw keypoints on frame (optional)
    for i, (x,y,c) in enumerate(kp_smooth):
        if c > 0.2:
            cv2.circle(frame, (int(x), int(y)), 4, (0,255,0), -1)
    # textual overlays
    cv2.putText(frame, f"Squat reps: {rep_counts['Squat']}", (20,40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,0), 2)
    cv2.putText(frame, f"Arm reps: {rep_counts['Arm Circle']}", (20,80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,0), 2)
    cv2.putText(frame, f"{screen_msg}", (20,120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,0), 2)

    cv2.imshow("AI Coach", frame)

# cleanup
cap.release()
cv2.destroyAllWindows()
voice_q.put(None)  # stop tts worker
