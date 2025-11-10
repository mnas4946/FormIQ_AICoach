# FormIQ - Intelligent Physiotherapy Coach

An AI-powered web application for physiotherapy rehabilitation with real-time pose detection, automatic rep counting, and form feedback.

## ✨ Features

- **Real-Time Pose Detection**: Powered by YOLOv8 for accurate body landmark tracking
- **Automatic Rep Counting**: Intelligent detection of exercise phases (up/down) with automatic counting
- **Form Feedback**: Real-time analysis and feedback on:
  - Joint angles (knees, elbows, shoulders)
  - Body alignment and balance
  - Movement quality indicators
- **Multiple Exercise Support**:
  - Squats (Stage 4) with depth and form analysis
  - Arm Circles (Stage 1) with height and straightness tracking
- **Interactive Web Interface**: User-friendly frontend with live video feed and metrics
- **Real-Time Communication**: WebSocket integration for seamless data streaming
- **Visual Feedback**: Color-coded indicators (green/yellow/red) for form quality
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
cd Kinda_works_aiphysio
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

3. **Verify model files**
Ensure `yolov8n-pose.pt` is present in the `models/` directory.

### Running the Application

1. **Start the AI detection backend**
```bash
python core/realtime_detection.py
```
This opens an OpenCV window with pose detection. Use keyboard controls:
- **'q'** - Quit
- **'p'** - Pause/Resume
- **'c'** - Calibrate

2. **Open the frontend**
Open `frontend_disconnected/index.html` in your web browser to access the user interface.


## Usage Guide

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


## Architecture

The application follows a client-server architecture with real-time communication:

```
Frontend (HTML/JS) <--[WebSocket]--> Backend (Python/Flask) <--> YOLOv8 <--> Webcam
```

**Data Flow:**
1. Webcam captures video frames
2. YOLOv8 processes frames for pose keypoints
3. Exercise modules analyze keypoints for form and reps
4. Results stream to frontend via WebSocket
5. Frontend displays feedback and metrics in real-time

## Project Structure

```
Kinda_works_aiphysio/
├── core/
│   ├── exercises/
│   │   ├── arm_circle_stage_1.py    # Arm circle exercise logic
│   │   └── squat.py                  # Squat exercise logic
│   └── realtime_detection.py         # Main pose detection engine
├── data/
│   ├── reference/                    # Reference pose data
│   │   ├── squat_down.json          # Squat down position keypoints
│   │   └── squat_up.json            # Squat up position keypoints
│   ├── squat_pictures/              # Visual references
│   └── extract_squat.py             # Data extraction utility
├── frontend_disconnected/
│   ├── index.html                   # Landing page
│   ├── exercise.html                # Exercise selection page
│   ├── exercise_stage1.html         # Arm circles interface
│   ├── exercise_stage4.html         # Squats interface
│   ├── script.js                    # Frontend logic
│   └── style.css                    # Styling
├── models/
│   └── yolov8n-pose.pt             # YOLOv8 pose detection model
└── README.md
```

**Key Components:**
- `core/realtime_detection.py`: Main entry point, handles camera and pose detection
- `core/exercises/`: Exercise-specific form analysis and rep counting logic
- `frontend_disconnected/`: Web interface for user interaction
- `data/reference/`: Calibration data and reference poses
- `models/`: Pre-trained YOLOv8 pose estimation model

## Acknowledgments

- **YOLOv8** by Ultralytics
- **Flask** framework
- **Socket.IO** for real-time communication
- **OpenCV** for computer vision

---

