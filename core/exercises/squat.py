"""
SQUAT MODULE
============
Contains all squat-specific logic:
- Thresholds and constants
- State machine for rep counting
- Reference angle checker
- Feedback rules
"""

import json
import os
from typing import Dict

# ========================================
# SQUAT THRESHOLDS & CONSTANTS
# ========================================

# The reference angles (56° down, 166° up) are IDEAL form targets used by SquatReferenceChecker.
# Reps are counted when knees drop below 80° (vs ideal 56°) to allow for imperfect but valid squats.
SQUAT_DOWN_ANGLE = 80          # Below this angle = "down" position for rep counting
SQUAT_UP_ANGLE = 150           # Above this angle = "up" position for rep counting

# Rep counting
CONSECUTIVE_CONFIRM = 3        # Number of consecutive frames needed to confirm a phase change

# ========================================
# SQUAT STATE MACHINE
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

# ========================================
# SQUAT REFERENCE ANGLE CHECKER
# ========================================

class SquatReferenceChecker:
    """
    Checks squat form against reference angles from correct form images.
    """
    
    def __init__(self, reference_dir=None):
        """
        Initialize the reference checker.
        
        PARAMETERS:
            reference_dir: Path to directory containing reference JSON files
                          (defaults to ../data/reference/)
        """
        if reference_dir is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            reference_dir = os.path.join(script_dir, "..", "data", "reference")
        
        self.reference_dir = reference_dir
        self.references = {}
        
        # Load reference data
        self._load_references()
    
    def _load_references(self):
        """Load reference angles from JSON files."""
        try:
            # Load DOWN position reference
            down_path = os.path.join(self.reference_dir, "squat_down.json")
            with open(down_path, 'r') as f:
                self.references['down'] = json.load(f)
            
            # Load UP position reference
            up_path = os.path.join(self.reference_dir, "squat_up.json")
            with open(up_path, 'r') as f:
                self.references['up'] = json.load(f)
            
            print(f"✓ Loaded squat reference angles:")
            print(f"   DOWN: Avg knee = {self.references['down']['angles']['avg_knee']:.1f}°")
            print(f"   UP:   Avg knee = {self.references['up']['angles']['avg_knee']:.1f}°")
            
        except Exception as e:
            print(f"⚠️  Could not load squat references: {e}")
            print(f"   Using default fallback values")
            
            # Set default fallback values
            self.references = {
                'down': {'angles': {'avg_knee': 56.0, 'avg_hip': 52.0, 'torso_lean': 29.0}},
                'up': {'angles': {'avg_knee': 166.0, 'avg_hip': 175.0, 'torso_lean': 3.0}}
            }
    
    def check_form(self, current_angles: Dict[str, float], position: str = "down", 
                   tolerance: float = 15.0) -> Dict:
        """
        Check current form against reference angles.
        
        PARAMETERS:
            current_angles: Dictionary with current joint angles
                           e.g., {'left_knee': 60, 'right_knee': 58, 'torso': 85, ...}
            position: "down" or "up" - which reference to compare against
            tolerance: Acceptable deviation in degrees (default: 15°)
        
        RETURNS:
            Dictionary containing:
                - 'deviations': angles that deviate from reference
                - 'feedback': list of feedback messages
                - 'overall_score': 0-100 score (100 = perfect)
                - 'is_correct': True if within tolerance
        """
        if position not in self.references:
            position = "down"  # Default fallback
        
        ref_angles = self.references[position]['angles']
        deviations = {}
        feedback = []
        
        # Calculate average knee angle if not provided
        if 'avg_knee' not in current_angles and 'left_knee' in current_angles and 'right_knee' in current_angles:
            current_angles['avg_knee'] = (current_angles['left_knee'] + current_angles['right_knee']) / 2.0
        
        # CHECK KNEE ANGLE
        if 'avg_knee' in current_angles:
            ref_knee = ref_angles['avg_knee']
            curr_knee = current_angles['avg_knee']
            deviation = curr_knee - ref_knee
            deviations['knee'] = deviation
            
            if deviation > tolerance:
                if deviation > 0:
                    feedback.append(f"Go deeper! Your knees are {abs(deviation):.0f}° too straight. Target: {ref_knee:.0f}°")
                else:
                    feedback.append(f"Your squat is very deep ({curr_knee:.0f}°). Good depth!")
            else:
                feedback.append(f"✓ Perfect knee angle ({curr_knee:.0f}°)")
        
        # CHECK TORSO ANGLE (Shoulder-Hip angle for body straightness)
        if 'torso' in current_angles:
            curr_torso = current_angles['torso']
            # Ideal torso angle should be close to 180° (straight back)
            # Lower angles mean leaning forward
            if curr_torso < 160:
                feedback.append(f"⚠️ Keep your back straight! Torso: {curr_torso:.0f}° (lean forward)")
            elif curr_torso >= 160 and curr_torso <= 180:
                feedback.append(f"✓ Good posture! Back is straight ({curr_torso:.0f}°)")
            
            deviations['torso'] = 180 - curr_torso  # Deviation from perfectly straight
        
        # CHECK LEFT/RIGHT BALANCE
        if 'left_knee' in current_angles and 'right_knee' in current_angles:
            left_right_diff = abs(current_angles['left_knee'] - current_angles['right_knee'])
            deviations['balance'] = left_right_diff
            
            if left_right_diff > 10:
                feedback.append(f"⚠️ Uneven! L{current_angles['left_knee']:.0f}° vs R{current_angles['right_knee']:.0f}° - Balance your weight")
            else:
                feedback.append(f"✓ Good balance between legs")
        
        # CALCULATE OVERALL SCORE
        total_deviation = sum(abs(dev) for dev in deviations.values() if isinstance(dev, (int, float)))
        num_checks = len(deviations)
        
        if num_checks > 0:
            avg_deviation = total_deviation / num_checks
            score = max(0, min(100, 100 - (avg_deviation / 30.0 * 100)))
        else:
            score = 50
        
        is_correct = score >= 70
        
        return {
            'deviations': deviations,
            'feedback': feedback,
            'overall_score': round(score, 1),
            'is_correct': is_correct,
            'position': position,
            'reference_angles': ref_angles,
            'current_angles': current_angles
        }
    
    # def get_vocal_feedback(self, check_result: Dict) -> str:
    #     """Generate concise vocal feedback from check result."""
    #     score = check_result['overall_score']
        
    #     if score >= 90:
    #         return "Excellent form! Keep it up."
    #     elif score >= 70:
    #         return "Good squat. " + check_result['feedback'][0] if check_result['feedback'] else "Good squat."
    #     else:
    #         if check_result['feedback']:
    #             return check_result['feedback'][0]
    #         else:
    #             return "Check your form."
    
    def get_visual_feedback(self, check_result: Dict) -> str:
        """Generate multi-line visual feedback for screen display."""
        lines = []
        lines.append(f"Form Score: {check_result['overall_score']:.0f}/100")
        
        for msg in check_result['feedback'][:3]:
            lines.append(msg)
        
        return " | ".join(lines)

# ========================================
# SQUAT FEEDBACK RULES
# ========================================

def generate_squat_feedback(metrics, last_feedback_time, feedback_cooldown=2.0):
    """
    Generate simple rule-based squat feedback.
    
    PARAMETERS:
        metrics: Dictionary of joint angles (left_knee, right_knee, torso)
        last_feedback_time: Timestamp of last feedback
        feedback_cooldown: Seconds between vocal feedback
    
    RETURNS:
        screen_text (string for display)
    """
    import time
    now = time.time()
    screen_text = []
    
    lk, rk = metrics.get("left_knee"), metrics.get("right_knee")
    torso = metrics.get("torso")
    
    if lk is None or rk is None:
        screen_text.append("Can't measure squat - reposition")
    else:
        avg_knee = (lk + rk) / 2.0
        screen_text.append(f"Knees: L{int(lk)}° R{int(rk)}°")
        
        # Check knee depth
        if avg_knee > 140:
            screen_text.append("Try going deeper")
        elif avg_knee < 75:
            screen_text.append("Nice depth!")
        else:
            screen_text.append("Good squat depth")
        
        # Check torso angle (body straightness)
        if torso is not None:
            screen_text.append(f"Torso: {int(torso)}°")
            if torso < 160:
                screen_text.append("⚠️ Keep back straight!")
            else:
                screen_text.append("✓ Good posture")
    
    return " | ".join(screen_text)
