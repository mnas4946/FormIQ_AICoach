"""
Flask Backend Server for AI Physio
Handles real-time pose detection and exercise feedback via WebSocket
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import cv2
import numpy as np
import base64
import os
import sys

# Add parent directory to path to import core modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.realtime_detection import (
    yolo, smooth_kp, compute_angle_deg,
    SMOOTH_ALPHA, MIN_VISIBLE_KEYPOINTS
)
from core.exercises.squat import SquatState, generate_squat_feedback
from core.exercises.arm_circle_stage_1 import ArmCircleState, generate_arm_circle_feedback

# Initialize Flask app
app = Flask(__name__, 
            static_folder='../frontend',
            template_folder='../frontend')
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Enable CORS for frontend communication
CORS(app)

# Initialize SocketIO with CORS support
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Store active sessions (session_id -> exercise_state)
active_sessions = {}

class ExerciseSession:
    """Manages state for an active exercise session"""
    
    def __init__(self, exercise_type):
        self.exercise_type = exercise_type
        self.rep_count = 0
        self.kp_smooth_prev = None
        
        # Initialize exercise-specific state
        if exercise_type == "arm_circle":
            self.state = ArmCircleState()
        elif exercise_type == "squat":
            self.state = SquatState()
        else:
            self.state = None
    
    def process_frame(self, frame):
        """
        Process a single frame and return feedback
        
        Args:
            frame: OpenCV image (BGR format)
            
        Returns:
            dict with rep_count, feedback, and angles
        """
        # Run pose detection
        results = yolo(frame)
        
        if not results or len(results[0].keypoints) == 0:
            return {
                'success': False,
                'error': 'No person detected',
                'rep_count': self.rep_count
            }
        
        # Extract keypoints
        kp_array = results[0].keypoints.xy[0].cpu().numpy()
        confs = results[0].keypoints.conf[0].cpu().numpy()
        
        visible_mask = confs > 0.2
        
        if np.sum(visible_mask) < MIN_VISIBLE_KEYPOINTS:
            return {
                'success': False,
                'error': 'Please fully enter the frame',
                'rep_count': self.rep_count
            }
        
        keypoints = np.concatenate([kp_array, confs.reshape(-1,1)], axis=1)
        
        # Smooth keypoints
        kp_smooth = smooth_kp(self.kp_smooth_prev, keypoints, alpha=SMOOTH_ALPHA)
        self.kp_smooth_prev = kp_smooth.copy()
        
        # Normalize keypoints
        visible_idxs = np.where(kp_smooth[:,2] > 0.2)[0]
        
        if len(visible_idxs) < MIN_VISIBLE_KEYPOINTS:
            return {
                'success': False,
                'error': 'Keypoints incomplete - reposition',
                'rep_count': self.rep_count
            }
        
        center = np.mean(kp_smooth[visible_idxs, :2], axis=0)
        
        try:
            scale = np.linalg.norm(kp_smooth[5,:2] - kp_smooth[6,:2])
            if scale < 1e-6: 
                scale = 1.0
        except:
            scale = 1.0
        
        # Compute angles
        angles = self._compute_angles(kp_smooth)
        
        # Update state machine and count reps
        rep_completed = False
        
        if self.exercise_type == "squat":
            avg_knee = (angles["left_knee"] + angles["right_knee"]) / 2.0
            rep_completed = self.state.update(avg_knee)
        elif self.exercise_type == "arm_circle":
            avg_arm_angle = (angles["left_arm_angle"] + angles["right_arm_angle"]) / 2.0
            rep_completed = self.state.update(avg_arm_angle)
        
        if rep_completed:
            self.rep_count += 1
        
        # Generate feedback
        feedback = self._generate_feedback(angles)
        
        # Draw keypoints on frame for visualization
        annotated_frame = self._draw_keypoints(frame, kp_smooth)
        
        return {
            'success': True,
            'rep_count': self.rep_count,
            'rep_completed': rep_completed,
            'feedback': feedback,
            'angles': angles,
            'annotated_frame': annotated_frame
        }
    
    def _compute_angles(self, kp_smooth):
        """Compute all relevant joint angles"""
        angles = {}
        
        try:
            # Knee angles
            angles["left_knee"] = compute_angle_deg(
                kp_smooth[11,:2], kp_smooth[13,:2], kp_smooth[15,:2]
            )
            angles["right_knee"] = compute_angle_deg(
                kp_smooth[12,:2], kp_smooth[14,:2], kp_smooth[16,:2]
            )
            
            # Torso angles
            left_torso = compute_angle_deg(
                kp_smooth[5,:2], kp_smooth[11,:2], kp_smooth[13,:2]
            )
            right_torso = compute_angle_deg(
                kp_smooth[6,:2], kp_smooth[12,:2], kp_smooth[14,:2]
            )
            angles["torso"] = (left_torso + right_torso) / 2.0
            
            # Elbow angles
            angles["left_elbow"] = compute_angle_deg(
                kp_smooth[5,:2], kp_smooth[7,:2], kp_smooth[9,:2]
            )
            angles["right_elbow"] = compute_angle_deg(
                kp_smooth[6,:2], kp_smooth[8,:2], kp_smooth[10,:2]
            )
            
            # Arm angles (for arm circles)
            angles["left_arm_angle"] = compute_angle_deg(
                kp_smooth[11,:2], kp_smooth[5,:2], kp_smooth[9,:2]
            )
            angles["right_arm_angle"] = compute_angle_deg(
                kp_smooth[12,:2], kp_smooth[6,:2], kp_smooth[10,:2]
            )
            
        except Exception as e:
            print(f"Error computing angles: {e}")
        
        return angles
    
    def _generate_feedback(self, angles):
        """Generate exercise-specific feedback"""
        import time
        
        if self.exercise_type == "squat":
            return generate_squat_feedback(angles, time.time())
        elif self.exercise_type == "arm_circle":
            return generate_arm_circle_feedback(angles, time.time())
        
        return ""
    
    def _draw_keypoints(self, frame, kp_smooth):
        """Draw keypoints on frame for visualization"""
        annotated = frame.copy()
        
        for i, (x, y, c) in enumerate(kp_smooth):
            if c > 0.2:
                cv2.circle(annotated, (int(x), int(y)), 4, (0,255,0), -1)
        
        return annotated


# ========================================
# REST API ENDPOINTS
# ========================================

@app.route('/')
def index():
    """Serve the main index page"""
    return render_template('index.html')

@app.route('/exercise/stage1')
def exercise_stage1():
    """Serve the stage 1 exercise page"""
    return render_template('exercise_stage1.html')

@app.route('/exercise/stage4')
def exercise_stage4():
    """Serve the stage 4 exercise page"""
    return render_template('exercise_stage4.html')

@app.route('/style.css')
def serve_css():
    """Serve CSS file"""
    return send_from_directory(app.static_folder, 'style.css', mimetype='text/css')

@app.route('/script.js')
def serve_js():
    """Serve JavaScript file"""
    return send_from_directory(app.static_folder, 'script.js', mimetype='application/javascript')

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'active_sessions': len(active_sessions)})


# ========================================
# WEBSOCKET EVENTS
# ========================================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to AI Physio backend'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"Client disconnected: {request.sid}")
    
    # Clean up session if exists
    if request.sid in active_sessions:
        del active_sessions[request.sid]

@socketio.on('start_session')
def handle_start_session(data):
    """
    Initialize a new exercise session
    
    Expected data:
        {
            'exercise_type': 'squat' or 'arm_circle'
        }
    """
    exercise_type = data.get('exercise_type', 'squat')
    
    print(f"Starting session for {request.sid}: {exercise_type}")
    
    # Create new session
    session = ExerciseSession(exercise_type)
    active_sessions[request.sid] = session
    
    emit('session_started', {
        'exercise_type': exercise_type,
        'message': f'Session started for {exercise_type}'
    })

@socketio.on('process_frame')
def handle_process_frame(data):
    """
    Process a video frame from the client
    
    Expected data:
        {
            'frame': base64 encoded image string
        }
    """
    if request.sid not in active_sessions:
        emit('error', {'message': 'No active session. Please start a session first.'})
        return
    
    session = active_sessions[request.sid]
    
    try:
        # Decode base64 image
        img_data = base64.b64decode(data['frame'].split(',')[1])
        nparr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Process frame
        result = session.process_frame(frame)
        
        # Encode annotated frame back to base64
        if result.get('success') and 'annotated_frame' in result:
            _, buffer = cv2.imencode('.jpg', result['annotated_frame'])
            annotated_b64 = base64.b64encode(buffer).decode('utf-8')
            result['annotated_frame'] = f"data:image/jpeg;base64,{annotated_b64}"
        
        # Send result back to client
        emit('frame_result', result)
        
    except Exception as e:
        print(f"Error processing frame: {e}")
        emit('error', {'message': f'Error processing frame: {str(e)}'})

@socketio.on('end_session')
def handle_end_session():
    """End the current exercise session"""
    if request.sid in active_sessions:
        session = active_sessions[request.sid]
        final_reps = session.rep_count
        
        del active_sessions[request.sid]
        
        emit('session_ended', {
            'final_reps': final_reps,
            'message': 'Session ended successfully'
        })
        
        print(f"Session ended for {request.sid}. Final reps: {final_reps}")
    else:
        emit('error', {'message': 'No active session to end'})


# ========================================
# RUN SERVER
# ========================================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("AI PHYSIO BACKEND SERVER")
    print("="*60)
    print("Server starting on http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

