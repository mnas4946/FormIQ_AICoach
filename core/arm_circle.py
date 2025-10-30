"""
ARM CIRCLE MODULE
=================
Contains all arm circle-specific logic:
- Thresholds and constants
- State machine for rep counting
- Feedback rules
"""

import math

# ========================================
# ARM CIRCLE THRESHOLDS & CONSTANTS
# ========================================

# Arm circle detection
ARM_CIRCLE_ROTATION_TH = 300   # Total degrees of rotation to count as one complete circle

# ========================================
# ARM CIRCLE STATE MACHINE
# ========================================

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

    def update(self, shoulder_center, wrist_center, wrap_angle_deg_func):
        """
        Update state based on current arm position.
        
        PARAMETERS:
            shoulder_center: (x, y) midpoint of left and right shoulders
            wrist_center: (x, y) midpoint of left and right wrists
            wrap_angle_deg_func: Function to normalize angles to [-180, 180]
        
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
        delta = wrap_angle_deg_func(ang - self.prev_angle)
        
        # Accumulate absolute rotation (handles both clockwise and counterclockwise)
        self.cumulative += abs(delta)
        self.prev_angle = ang

        # Check if full circle completed
        if self.cumulative >= self.rotation_th:
            self.cumulative = 0.0  # Reset for next circle
            return True            # REP COMPLETED!
        
        return False

# ========================================
# ARM CIRCLE FEEDBACK RULES
# ========================================

def generate_arm_circle_feedback(metrics, last_feedback_time, feedback_cooldown=2.0):
    """
    Generate rule-based arm circle feedback.
    
    PARAMETERS:
        metrics: Dictionary of joint angles
        last_feedback_time: Timestamp of last feedback
        feedback_cooldown: Seconds between vocal feedback
    
    RETURNS:
        (screen_text, speak_text)
    
    FEEDBACK RULES:
        - both elbows > 170°: Too straight → "Soften elbows"
        - Otherwise: Good form → "Nice rotation"
    """
    import time
    now = time.time()
    speak_text = None
    screen_text = []
    
    le, re = metrics.get("left_elbow"), metrics.get("right_elbow")
    
    if le is None or re is None:
        screen_text.append("Can't measure arms - reposition")
    else:
        screen_text.append(f"Elbows: L{int(le)}° R{int(re)}")
        
        if le > 170 and re > 170:
            screen_text.append("Soften your elbows a little.")
            if now - last_feedback_time > feedback_cooldown:
                speak_text = "Bend your elbows slightly so your shoulders aren't strained."
        else:
            screen_text.append("Nice arm circle.")
            if now - last_feedback_time > feedback_cooldown:
                speak_text = "Nice rotation, keep a smooth pace."
    
    return " | ".join(screen_text), speak_text
