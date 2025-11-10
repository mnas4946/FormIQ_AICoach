"""
ARM CIRCLE MODULE (STAGE 1 - Recovery Exercise)
============
Contains all arm circle-specific logic for patients in early recovery:
- Thresholds and constants
- State machine for rep counting
- Feedback rules
"""

import json
import numpy as np
from typing import Dict

# ========================================
# ARM CIRCLE THRESHOLDS & CONSTANTS
# ========================================

# Reps are counted when ARM MOVES UP TO 90 DEGREES (shoulder level)
ARM_DOWN_ANGLE = 20       # Below this angle = "down" position (arms at sides)
ARM_UP_ANGLE = 80         # Above this angle = "up" position (arms at shoulder level ~90°)

# Arm straightness check
MIN_ELBOW_ANGLE = 160     # Minimum angle for "straight" arm

# Rep counting
CONSECUTIVE_CONFIRM = 3   # Number of consecutive frames needed to confirm a phase change

# ========================================
# ARM CIRCLE STATE MACHINE
# ========================================

class ArmCircleState:
    """
    State machine for tracking arm circle repetitions.
    
    STATES:
        - "down": Arms at sides (starting position)
        - "up": Arms raised to shoulder level (90° position)
    
    REP COUNTING:
        - One rep = complete cycle of down → up → down
        - Uses consecutive frame confirmation to prevent false triggers
        - Monitors arm angle from shoulder to wrist
    
    HOW IT WORKS:
        1. Start in "down" state (arms at sides)
        2. When arm angle rises above up_th for CONSECUTIVE_CONFIRM frames → transition to "up"
        3. When arm angle drops below down_th for CONSECUTIVE_CONFIRM frames → transition to "down" + COUNT REP
        4. Hysteresis prevents rapid state switching
    """
    
    def __init__(self, down_th=ARM_DOWN_ANGLE, up_th=ARM_UP_ANGLE):
        """
        Initialize arm circle tracker.
        
        PARAMETERS:
            down_th: Arm angle threshold for "down" position (degrees)
            up_th: Arm angle threshold for "up" position (degrees)
        """
        self.state = "down"     # Current state: 'down' or 'up'
        self.down_th = down_th  # Threshold for detecting arms down
        self.up_th = up_th      # Threshold for detecting arms up
        self.counter = 0        # Consecutive frames in new state

    def update(self, avg_arm_angle):
        """
        Update state based on current arm angle.
        
        PARAMETERS:
            avg_arm_angle: Average angle of arms from vertical (degrees)
                          Calculated from shoulder-elbow-wrist angle relative to vertical
        
        RETURNS:
            True if a rep was just completed, False otherwise
        
        STATE TRANSITIONS:
            down → up: When angle > up_th for CONSECUTIVE_CONFIRM frames
            up → down: When angle < down_th for CONSECUTIVE_CONFIRM frames (REP!)
        """
        rep = False
        
        if avg_arm_angle is None:
            self.counter = 0
            return False
        
        # State: DOWN (arms at sides) - waiting to raise arms
        if self.state == "down":
            if avg_arm_angle > self.up_th:
                self.counter += 1
                if self.counter >= CONSECUTIVE_CONFIRM:
                    self.state = "up"  # Transition to up
                    self.counter = 0
            else:
                self.counter = 0  # Reset if angle goes back down
        
        # State: UP (arms raised) - waiting to lower arms
        elif self.state == "up":
            if avg_arm_angle < self.down_th:
                self.counter += 1
                if self.counter >= CONSECUTIVE_CONFIRM:
                    self.state = "down"  # Transition to down
                    self.counter = 0
                    rep = True           # REP COMPLETED!
            else:
                self.counter = 0  # Reset if angle goes back up
        
        return rep


# ========================================
# ARM CIRCLE FEEDBACK RULES
# ========================================

def generate_arm_circle_feedback(metrics, last_feedback_time, feedback_cooldown=2.0):
    """
    Generate feedback for arm circle exercise (Stage 1 - Recovery).
    
    FEEDBACK FOCUSES ON:
        1. Keeping arms straight (shoulder-elbow-wrist alignment)
        2. Reaching 90° (shoulder level) without going too high
        3. Controlled movement to prevent injury
    
    PARAMETERS:
        metrics: Dictionary of joint angles
                 Expected keys: 'left_elbow', 'right_elbow', 'left_arm_angle', 'right_arm_angle'
        last_feedback_time: Timestamp of last feedback
        feedback_cooldown: Seconds between vocal feedback
    
    RETURNS:
        screen_text (string for display)
    """
    import time
    now = time.time()
    screen_text = []
    
    le, re = metrics.get("left_elbow"), metrics.get("right_elbow")
    left_arm = metrics.get("left_arm_angle")
    right_arm = metrics.get("right_arm_angle")
    
    # Check if we have the necessary measurements
    if le is None or re is None or left_arm is None or right_arm is None:
        screen_text.append("Can't measure arms - reposition")
        return " | ".join(screen_text)
    
    avg_elbow = (le + re) / 2.0
    avg_arm_angle = (left_arm + right_arm) / 2.0
    
    # Display current angles
    screen_text.append(f"Arms: L{int(left_arm)}° R{int(right_arm)}°")
    
    # CHECK ARM STRAIGHTNESS (elbow angle should be close to 180°)
    if avg_elbow < MIN_ELBOW_ANGLE:
        screen_text.append(f"⚠️ Keep arms straight! (Elbows: {int(avg_elbow)}°)")
    else:
        screen_text.append("✓ Arms straight")
    
    # CHECK ARM HEIGHT
    if avg_arm_angle < 70:
        screen_text.append("Raise arms higher to shoulder level")
    elif avg_arm_angle > 100:
        screen_text.append("⚠️ Don't raise too high! Risk of injury")
    elif 80 <= avg_arm_angle <= 100:
        screen_text.append("✓ Perfect height (shoulder level)")
    else:
        screen_text.append("Good movement")
    
    # CHECK BALANCE (left vs right symmetry)
    arm_diff = abs(left_arm - right_arm)
    if arm_diff > 15:
        screen_text.append(f"⚠️ Uneven arms! Keep them level")
    else:
        screen_text.append("✓ Good balance")
    
    return " | ".join(screen_text)
