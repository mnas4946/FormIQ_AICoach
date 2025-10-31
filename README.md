# AI Coach - Modular Architecture

## Setting Up
### Dependencies
opencv-python>=4.12.0
numpy>=2.2.6
ultralytics>=8.3.222
pyttsx3>=2.99

### Installation
pip3 install opencv-python numpy ultralytics pyttsx3

## 📁 File Structure

```
core/
├── realtime_detection.py  ← ENTRY POINT - Main application
├── squat.py              ← Squat-specific logic
├── arm_circle.py         ← Arm circle-specific logic
└── voice_feedback.py     ← Text-to-speech and feedback system
```

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

