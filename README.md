# AI Coach - Modular Architecture

## 📁 File Structure

```
core/
├── realtime_detection.py  ← ENTRY POINT - Main application
├── squat.py              ← Squat-specific logic
├── arm_circle.py         ← Arm circle-specific logic
└── voice_feedback.py     ← Text-to-speech and feedback system
```

---

## 🎯 Module Responsibilities

### **realtime_detection.py** (Entry Point)
**Purpose:** Main application that coordinates everything

**Contains:**
- ✅ Exercise selection menu
- ✅ Configuration parameters
- ✅ Pose detection model loading
- ✅ Helper functions (geometry & smoothing)
- ✅ Main video processing loop
- ✅ Camera initialization
- ✅ Keypoint extraction and processing

**Does NOT contain:** Exercise-specific logic (moved to modules)

---

### **squat.py** (Squat Module)
**Purpose:** All squat-specific functionality

**Contains:**
- ✅ `SQUAT_DOWN_ANGLE`, `SQUAT_UP_ANGLE` - Thresholds
- ✅ `SquatState` - State machine for rep counting
- ✅ `SquatReferenceChecker` - Compare against correct form
- ✅ `generate_squat_feedback()` - Feedback rules

**Exports:**
```python
from squat import SquatState, SquatReferenceChecker
```

---

### **arm_circle.py** (Arm Circle Module)
**Purpose:** All arm circle-specific functionality

**Contains:**
- ✅ `ARM_CIRCLE_ROTATION_TH` - Rotation threshold
- ✅ `ArmCircleState` - State machine for rep counting
- ✅ `generate_arm_circle_feedback()` - Feedback rules

**Exports:**
```python
from arm_circle import ArmCircleState
```

---

### **voice_feedback.py** (Voice & Feedback Module)
**Purpose:** Text-to-speech and general feedback system

**Contains:**
- ✅ TTS engine initialization
- ✅ Voice worker thread
- ✅ `speak()` - Non-blocking text-to-speech
- ✅ `stop_voice()` - Cleanup function
- ✅ `feedback_generator()` - Dispatches to exercise-specific feedback

**Exports:**
```python
from voice_feedback import speak, stop_voice, feedback_generator
```

---

## 🚀 How to Run

```bash
cd core/
python realtime_detection.py
```

**You'll see:**
```
============================================================
AI COACH - EXERCISE SELECTION
============================================================

Available exercises:
  [1] Squat
  [2] Arm Circle
  [3] Both (track both simultaneously)

Select exercise (1/2/3): 
```

---

## 🔧 How It Works

### Flow Diagram

```
1. User selects exercise
   ↓
2. realtime_detection.py imports required modules
   ↓
3. Initializes state machines (from squat.py / arm_circle.py)
   ↓
4. Starts camera loop
   ↓
5. For each frame:
   - Detect pose (YOLOv8)
   - Calculate angles
   - Update state machines
   - Generate feedback (via voice_feedback.py)
   - Display results
```

### Module Communication

```
realtime_detection.py (Main Loop)
    ├─→ squat.py (if squat selected)
    │   ├─→ SquatState.update(angle)
    │   └─→ generate_squat_feedback(metrics)
    │
    ├─→ arm_circle.py (if arm circle selected)
    │   ├─→ ArmCircleState.update(positions)
    │   └─→ generate_arm_circle_feedback(metrics)
    │
    └─→ voice_feedback.py
        ├─→ speak(message)
        └─→ feedback_generator() → dispatches to squat/arm_circle
```

---

## ✅ Benefits of This Structure

1. **Modularity** - Each exercise has its own file
2. **Maintainability** - Easy to find and update exercise-specific code
3. **Extensibility** - Add new exercises by creating new modules
4. **Testability** - Can test each module independently
5. **Clean separation** - Entry point stays clean and focused

---

## 🔮 Adding a New Exercise

To add a new exercise (e.g., "Push-up"):

1. **Create `pushup.py`:**
```python
class PushupState:
    def __init__(self):
        # Your state machine
        pass
    
    def update(self, angles):
        # Your logic
        pass

def generate_pushup_feedback(metrics, ...):
    # Your feedback rules
    pass
```

2. **Update `voice_feedback.py`:**
```python
from pushup import generate_pushup_feedback

def feedback_generator(...):
    # Add:
    elif exercise == "Push-up":
        return generate_pushup_feedback(...)
```

3. **Update `realtime_detection.py`:**
```python
from pushup import PushupState

# Add to selection menu
print("  [4] Push-up")

# Initialize if selected
if selected_exercise == "Push-up":
    pushup_state = PushupState()
```

Done! 🎉

---

## 📊 What Didn't Change

Everything that works stays the same:
- ✅ Pose detection logic
- ✅ Angle calculations
- ✅ Smoothing algorithms
- ✅ Rep counting mechanisms
- ✅ Visual overlays
- ✅ Keyboard controls

**The code is reorganized, not rewritten!**

