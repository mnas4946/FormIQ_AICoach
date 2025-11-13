# FormIQ - Intelligent Physiotherapy Coach

An AI-powered web application for physiotherapy rehabilitation with real-time pose detection, automatic rep counting, and form feedback.

**Note:** While the system can run on Windows or Linux, the prototype performs best on macOS. The UI on the working prototype (not frontend demo) is smoother, webcam is faster, and text-to-speech feedback works reliably without glitches.

## ✨ Features

- **Real-Time Pose Detection**: Powered by YOLOv8 (Python backend) and MediaPipe Pose (Browser frontend)
- **Automatic Rep Counting**: Intelligent detection of exercise phases (up/down) with automatic counting
- **Text-to-Speech Feedback**: Voice guidance that reads feedback and announces rep counts with 5-second cooldown
- **Form Feedback**: Real-time analysis and feedback on:
  - Joint angles (knees, elbows, shoulders)
  - Body alignment and balance
  - Movement quality indicators
- **Multiple Exercise Support**:
  - Squats (Stage 4) with depth and form analysis
  - Arm Circles (Stage 1) with height and straightness tracking
- **Interactive Web Interface**: User-friendly frontend with live video feed and metrics
- **Browser-Based Pose Tracking**: Visual skeleton overlay with keypoint detection (no backend required)
- **Real-Time Communication**: WebSocket integration for seamless data streaming
- **Visual Feedback**: Color-coded indicators (green/yellow/red) for form quality
- **Smooth Animations**: Enhanced feedback overlay with 50% slower, smoother transitions
- **Calibration System**: Personalized baseline measurements for accurate feedback

## Installation

### Prerequisites

- Python 3.8 or higher
- Webcam/Camera access
- Modern web browser (Chrome, Firefox, Safari, or Edge)

### Installation Steps

1. **Clone the repository**
```bash
git clone <repository-url>
cd FormIQ_AICoach
```

2. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

Required packages:
- `ultralytics` - YOLOv8 pose detection model
- `opencv-python` - Computer vision and camera handling
- `flask` - Web framework
- `flask-socketio` - Real-time WebSocket communication
- `numpy` - Numerical computations
- `pyttsx3` - Text-to-speech for voice feedback

3. **Verify model files**
Ensure `yolov8n-pose.pt` is present in the `models/` directory.

### Running the Application

1. **Start the AI detection backend**
```bash
cd core
```
```bash
python3 realtime_detection.py
```

This opens an OpenCV window with pose detection. Use keyboard controls:
- **'q'** - Quit
- **'p'** - Pause/Resume
- **'c'** - Calibrate

**Voice Feedback:**
- The system will automatically speak:
  - "Rep counted" when you complete a repetition
  - Form feedback messages displayed on screen
- 5-second cooldown between voice announcements prevents audio spam

2. **Open the frontend**
Open `frontend_disconnected/index.html` in your web browser to access the user interface.


## Usage Guide for Realtime Detection Working Prototype

### For Squats (Stage 4)

1. **Position**: Stand 6-8 feet from camera
2. **Framing**: Ensure full body is visible (head to feet)
3. **Lighting**: Good lighting helps detection accuracy
4. **Exercise**: Perform squats with proper form
5. **Feedback**: Watch real-time feedback on screen:
   - Knee angles (depth)
   - Torso straightness
   - Left/right balance

**Rep Counting:**
- Down: Knees bend below 80°
- Up: Knees extend above 150°
- Rep = Complete down → up cycle

### For Arm Circles (Stage 1)

1. **Position**: Stand 6-8 feet from camera
2. **Framing**: Ensure upper body is clearly visible
3. **Exercise**: Raise arms to shoulder level
4. **Feedback**: Monitor:
   - Arm straightness (elbows > 160°)
   - Height (80-100° ideal)
   - Left/right balance

**Rep Counting:**
- Down: Arms at sides (< 20°)
- Up: Arms at shoulder level (> 80°)
- Rep = Complete down → up cycle

## Usage Guide for Frontend Demo

To get started, open `index.html` in your web browser.

### For Squats (Stage 4)
1. Click "Start Today's Session"
2. Select the Squats exercise option

### For Arm Circles (Stage 1)
1. Scroll down to "Access Previous Stage Exercises"
2. Click on "Stage 1 - Initial Recovery"
3. Select "Arm Raises (Basic Arm Circles)"

## Project Structure

```
FormIQ_AICoach/
├── core/
│   ├── exercises/
│   │   ├── arm_circle_stage_1.py      # Logic for arm circle exercise (stage 1)
│   │   └── squat.py                   # Logic for squat exercise (stage 4)
│   └── realtime_detection.py          # Main pose detection/rep counting engine
├── data/
│   ├── reference/                     # Reference pose keypoints for form validation
│   │   ├── squat_down.json            # Keypoints for squat "down" position
│   │   └── squat_up.json              # Keypoints for squat "up" position
│   ├── squat_pictures/                # Reference images for squats
│   └── extract_squat.py               # Utility: Extracts pose/keypoint data
├── frontend_disconnected/
│   ├── index.html                     # Web: Main landing/dashboard page
│   ├── exercise.html                  # Exercise selector UI
│   ├── exercise_stage1.html           # Arm circles with live pose tracking UI
│   ├── exercise_stage4.html           # Squats with live pose tracking UI
│   ├── script.js                      # Frontend logic and pose feedback
│   └── style.css                      # Styling & transitions for UI
├── models/
│   └── yolov8n-pose.pt                # Custom YOLOv8 model for pose detection
├── CAMERA_FEATURE_GUIDE.md            # Guide to webcam/pipeline features & setup
└── README.md
```
---

