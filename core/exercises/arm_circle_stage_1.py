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

def generate_arm_circle_feedback_clean(metrics, last_feedback_time, feedback_cooldown=2.0):
    """
    Subtitle-style arm circle feedback: encouragement and corrections only.
    
    PARAMETERS:
        metrics: Dictionary of joint angles
                 Expected keys: 'left_elbow', 'right_elbow', 'left_arm_angle', 'right_arm_angle'
        last_feedback_time: Timestamp of last feedback
        feedback_cooldown: Minimum seconds between messages
    
    RETURNS:
        screen_text: Concatenated string for display as subtitles
    """
    import time
    now = time.time()
    if (now - last_feedback_time) < feedback_cooldown:
        return ""  # cooldown period
    
    screen_text = []
    
    le, re = metrics.get("left_elbow"), metrics.get("right_elbow")
    left_arm, right_arm = metrics.get("left_arm_angle"), metrics.get("right_arm_angle")
    
    if None in [le, re, left_arm, right_arm]:
        return "Can't detect arms - reposition"
    
    # Arm straightness
    if (le + re)/2.0 < 160:
        screen_text.append("Keep your arms straight")
    else:
        screen_text.append("✓ Arms straight")
    
    # Arm height
    avg_arm = (left_arm + right_arm)/2.0
    if avg_arm < 70:
        screen_text.append("Raise arms a bit higher")
    elif avg_arm > 100:
        screen_text.append("Don't raise too high")
    else:
        screen_text.append("Good arm height")
    
    # Symmetry
    if abs(left_arm - right_arm) > 15:
        screen_text.append("Keep both arms level")
    else:
        screen_text.append("✓ Smooth and balanced")
    
    return " | ".join(screen_text)

