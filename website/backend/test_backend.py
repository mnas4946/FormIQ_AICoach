"""
Test script to verify backend functionality
Run this to check if the backend is set up correctly
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def test_imports():
    """Test if all required modules can be imported"""
    print("Testing imports...")
    
    try:
        import flask
        print("✓ Flask installed")
    except ImportError:
        print("✗ Flask not installed. Run: pip install flask")
        return False
    
    try:
        import flask_socketio
        print("✓ Flask-SocketIO installed")
    except ImportError:
        print("✗ Flask-SocketIO not installed. Run: pip install flask-socketio")
        return False
    
    try:
        import flask_cors
        print("✓ Flask-CORS installed")
    except ImportError:
        print("✗ Flask-CORS not installed. Run: pip install flask-cors")
        return False
    
    try:
        import cv2
        print("✓ OpenCV installed")
    except ImportError:
        print("✗ OpenCV not installed. Run: pip install opencv-python")
        return False
    
    try:
        import numpy
        print("✓ NumPy installed")
    except ImportError:
        print("✗ NumPy not installed. Run: pip install numpy")
        return False
    
    try:
        from ultralytics import YOLO
        print("✓ Ultralytics installed")
    except ImportError:
        print("✗ Ultralytics not installed. Run: pip install ultralytics")
        return False
    
    return True

def test_model():
    """Test if YOLOv8 model exists"""
    print("\nTesting model files...")
    
    model_path = os.path.join(os.path.dirname(__file__), '..', '..', 'models', 'yolov8n-pose.pt')
    
    if os.path.exists(model_path):
        print(f"✓ Model found at: {model_path}")
        return True
    else:
        print(f"⚠ Model not found at: {model_path}")
        print("  The model will be downloaded automatically on first run.")
        return True  # Not a critical error

def test_exercise_modules():
    """Test if exercise modules can be imported"""
    print("\nTesting exercise modules...")
    
    try:
        from core.exercises.squat import SquatState, generate_squat_feedback
        print("✓ Squat module loaded")
    except ImportError as e:
        print(f"✗ Cannot import squat module: {e}")
        return False
    
    try:
        from core.exercises.arm_circle_stage_1 import ArmCircleState, generate_arm_circle_feedback
        print("✓ Arm circle module loaded")
    except ImportError as e:
        print(f"✗ Cannot import arm circle module: {e}")
        return False
    
    return True

def test_realtime_detection():
    """Test if realtime detection module works"""
    print("\nTesting realtime detection module...")
    
    try:
        from core.realtime_detection import current_session, compute_angle_deg
        print("✓ Realtime detection module loaded")
        
        # Test current_session function with parameters
        result = current_session(webpage="exercise_stage1.html")
        if result == "Arm Circle":
            print("✓ current_session returns correct exercise for stage1")
        else:
            print(f"✗ current_session returned '{result}', expected 'Arm Circle'")
            return False
        
        result = current_session(webpage="exercise_stage4.html")
        if result == "Squat":
            print("✓ current_session returns correct exercise for stage4")
        else:
            print(f"✗ current_session returned '{result}', expected 'Squat'")
            return False
        
        return True
        
    except ImportError as e:
        print(f"✗ Cannot import realtime detection module: {e}")
        return False
    except Exception as e:
        print(f"✗ Error testing realtime detection: {e}")
        return False

def test_backend_structure():
    """Test if backend files exist"""
    print("\nTesting backend structure...")
    
    backend_dir = os.path.dirname(__file__)
    
    files_to_check = [
        ('app.py', 'Backend server'),
        ('requirements.txt', 'Requirements file'),
        ('README.md', 'Documentation')
    ]
    
    all_exist = True
    for filename, description in files_to_check:
        filepath = os.path.join(backend_dir, filename)
        if os.path.exists(filepath):
            print(f"✓ {description} exists: {filename}")
        else:
            print(f"✗ {description} missing: {filename}")
            all_exist = False
    
    return all_exist

def main():
    """Run all tests"""
    print("="*60)
    print("AI PHYSIO BACKEND - SYSTEM TEST")
    print("="*60)
    print()
    
    all_passed = True
    
    # Run tests
    all_passed &= test_imports()
    all_passed &= test_model()
    all_passed &= test_exercise_modules()
    all_passed &= test_realtime_detection()
    all_passed &= test_backend_structure()
    
    print()
    print("="*60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
        print("="*60)
        print()
        print("Your backend is ready to run!")
        print("Start the server with: python app.py")
        print()
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        print("="*60)
        print()
        print("Please fix the issues above before running the backend.")
        print()
        return 1

if __name__ == "__main__":
    sys.exit(main())

