# 🏥 AI Physio - Intelligent Physiotherapy Coach

An AI-powered web application for physiotherapy rehabilitation with real-time pose detection, automatic rep counting, and form feedback.

## ✨ Features

- 🎥 **Real-time Pose Detection** - YOLOv8-based skeleton tracking
- 🔢 **Automatic Rep Counting** - AI counts your reps automatically
- 💬 **Live Form Feedback** - Real-time guidance on posture and technique
- 📊 **Progress Tracking** - Session statistics and performance metrics
- 🎯 **Multi-Exercise Support** - Squats, arm circles, and more
- 🌐 **Beautiful Web Interface** - Modern, responsive UI
- 📱 **Camera-Focused Design** - Maximize screen space for exercise

## 🚀 Installation

### Prerequisites

- **Python 3.8 - 3.13** (Python 3.10-3.12 recommended)
- **pip** (Python package manager)
- **Webcam** (built-in or external)
- **Modern browser** (Chrome, Firefox, Safari, Edge)

### Step 1: Navigate to Project Directory

```bash
cd "DECO3000 AI Project"
cd Kinda_works_aiphysio
```

### Step 2: Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
# .venv\Scripts\activate
```

### Step 3: Install Python Dependencies

```bash
cd website/backend

# For Python 3.13 users, upgrade pip first:
pip3 install --upgrade pip setuptools wheel

# Install all dependencies:
pip3 install -r requirements.txt
```

**Dependencies installed:**
- `Flask==3.0.0` - Web framework
- `flask-socketio==5.3.5` - Real-time WebSocket communication
- `flask-cors==4.0.0` - Cross-origin resource sharing
- `python-socketio==5.10.0` - Socket.IO support
- `opencv-python==4.10.0.84` - Computer vision & camera access
- `numpy>=1.26.0` - Numerical operations (Python 3.13 compatible!)
- `ultralytics>=8.3.0` - YOLOv8 pose detection model

### Step 4: Verify Model File

The YOLOv8 pose detection model should be in `models/yolov8n-pose.pt`:

```bash
# Check if model exists
ls ../../models/yolov8n-pose.pt

# Should output: ../../models/yolov8n-pose.pt
```

If model is missing, it should already be in your project folder.

## 🎮 How to Run

### Option 1: Web Application (Recommended)

**1. Start the Flask Backend Server:**

```bash
cd website/backend
python3 server.py
```

Or if python3 doesn't work:
```bash
python server.py
```

You should see:
```
============================================================
🚀 AI PHYSIO BACKEND SERVER
============================================================
Frontend: http://localhost:5000
Stage 1:  http://localhost:5000/exercise_stage1.html
Stage 4:  http://localhost:5000/exercise_stage4.html
============================================================
```

**2. Open Your Browser:**

Navigate to: **http://localhost:5000**

**3. Use the Application:**

- Click "Start Today's Rehabilitation" → Stage 4 (Squats)
- OR scroll down and click "Stage 1" → Arm Circles (Recovery)
- Click **"Start Camera"** button
- **Allow camera access** when prompted
- Start exercising! The AI will count reps and give feedback

### Option 2: Standalone Python Script (Alternative)

For command-line testing without the web interface:

```bash
cd core
python realtime_detection.py
```

This opens an OpenCV window with pose detection. Use keyboard controls:
- **'q'** - Quit
- **'p'** - Pause/Resume
- **'c'** - Calibrate

## 🎯 Usage Guide

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


## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│  Frontend (HTML/CSS/JavaScript)                     │
│  - Beautiful web interface                          │
│  - WebSocket client for real-time communication     │
│  - Webcam capture & pose visualization              │
└─────────────────────────────────────────────────────┘
                        ⬇️ WebSocket
┌─────────────────────────────────────────────────────┐
│  Backend (Flask + Socket.IO)                        │
│  - REST API endpoints                               │
│  - WebSocket server                                 │
│  - Session management                               │
└─────────────────────────────────────────────────────┘
                        ⬇️
┌─────────────────────────────────────────────────────┐
│  AI Detection (YOLOv8 + Exercise Modules)           │
│  - Real-time pose estimation                        │
│  - Angle calculations                               │
│  - Rep counting logic                               │
│  - Form analysis & feedback                         │
└─────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
Kinda_works_aiphysio/
├── core/                           # AI Detection System
│   ├── exercises/
│   │   ├── squat.py               # Squat detection & feedback
│   │   └── arm_circle_stage_1.py  # Arm circle detection (Stage 1)
│   └── realtime_detection.py      # Standalone detection (optional)
│
├── website/                        # Web Application
│   ├── backend/
│   │   ├── server.py              # Flask backend server ⭐
│   │   └── requirements.txt       # Python dependencies
│   │
│   └── frontend/
│       ├── index.html             # Dashboard
│       ├── exercise_stage1.html   # Stage 1 (Arm Circles)
│       ├── exercise_stage4.html   # Stage 4 (Squats)
│       ├── style.css              # All styles
│       ├── script.js              # UI functions
│       └── camera-client.js       # WebSocket client
│
├── models/
│   └── yolov8n-pose.pt            # YOLOv8 pose detection model
│
└── data/
    └── reference/                  # Reference poses for form checking
```

## 🙏 Acknowledgments

- **YOLOv8** by Ultralytics
- **Flask** framework
- **Socket.IO** for real-time communication
- **OpenCV** for computer vision

---

Flask==3.0.0
flask-socketio==5.3.5
flask-cors==4.0.0
opencv-python==4.8.1.78
numpy==1.24.3
ultralytics==8.1.0
python-socketio==5.10.0
eventlet==0.33.3