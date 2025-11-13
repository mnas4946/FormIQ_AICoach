"""
PURPOSE: Extract reference angles from images showing correct squat form.
         These reference angles can be used to compare against real-time performance.

INPUT:  Images of correct squat form (up and down positions)
OUTPUT: JSON files with reference angles for each position

HOW IT WORKS:
    1. Load images from squat_pictures/ folder
    2. Detect pose using YOLOv8
    3. Calculate all relevant joint angles
    4. Save reference data to reference/ folder
"""

import cv2
import numpy as np
from ultralytics import YOLO
import json
import os

# CONFIGURATION

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(SCRIPT_DIR, "squat_pictures")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "reference")

# Image paths
DOWN_IMAGE = os.path.join(IMAGE_DIR, "down.png")
UP_IMAGE = os.path.join(IMAGE_DIR, "up.png")

# Output paths
DOWN_JSON = os.path.join(OUTPUT_DIR, "squat_down.json")
UP_JSON = os.path.join(OUTPUT_DIR, "squat_up.json")

# Load YOLOv8 Pose model
MODEL_PATH = os.path.join(SCRIPT_DIR, "..", "yolov8n-pose.pt")
yolo = YOLO(MODEL_PATH)


# HELPER FUNCTIONS

def compute_angle_deg(a, b, c):
    """
    Calculate angle at point b formed by three points a-b-c.
    
    PARAMETERS:
        a, b, c: Points as (x, y) tuples or arrays
    
    RETURNS:
        Angle in degrees (0-180)
    """
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    
    ba = a - b  # Vector from b to a
    bc = c - b  # Vector from b to c
    
    # Calculate cosine of angle
    denom = (np.linalg.norm(ba) * np.linalg.norm(bc)) + 1e-8
    cosang = np.dot(ba, bc) / denom
    cosang = np.clip(cosang, -1.0, 1.0)
    
    return float(np.degrees(np.arccos(cosang)))

def compute_torso_angle(shoulder, hip, vertical_reference=None):
    """
    Calculate torso lean angle relative to vertical.
    
    PARAMETERS:
        shoulder: (x, y) shoulder midpoint
        hip: (x, y) hip midpoint
        vertical_reference: Optional reference point for vertical (defaults to straight down)
    
    RETURNS:
        Angle in degrees (0 = perfectly vertical, 90 = horizontal)
    """
    # Vector from hip to shoulder
    torso_vec = np.array(shoulder) - np.array(hip)
    
    # Vertical reference (pointing up)
    vertical_vec = np.array([0, -1])  # (0, -1) because y-axis points down in images
    
    # Calculate angle
    dot_product = np.dot(torso_vec, vertical_vec)
    mag_product = np.linalg.norm(torso_vec) * np.linalg.norm(vertical_vec)
    cosang = dot_product / (mag_product + 1e-8)
    cosang = np.clip(cosang, -1.0, 1.0)
    
    return float(np.degrees(np.arccos(cosang)))

# ========================================
# MAIN EXTRACTION FUNCTION
# ========================================

def extract_angles_from_image(image_path, position_name):
    """
    Extract all relevant angles from a squat image.
    
    PARAMETERS:
        image_path: Path to the image file
        position_name: Name of position ("up" or "down")
    
    RETURNS:
        Dictionary containing all reference angles and keypoint positions
    """
    print(f"\n{'='*60}")
    print(f"Processing: {position_name.upper()} position")
    print(f"Image: {image_path}")
    print(f"{'='*60}")
    
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not load image: {image_path}")
    
    print(f"✓ Image loaded: {img.shape[1]}x{img.shape[0]} pixels")
    
    # Run YOLOv8 pose detection
    results = yolo(img)
    
    # Check if person detected
    if not results or len(results[0].keypoints) == 0:
        raise ValueError(f"No person detected in {image_path}")
    
    # Extract keypoints
    kp_array = results[0].keypoints.xy[0].cpu().numpy()  # (17, 2)
    confs = results[0].keypoints.conf[0].cpu().numpy()    # (17,)
    
    print(f"✓ Keypoints detected: {len(kp_array)}")
    
    # COCO keypoint indices
    # 0: nose, 5-6: shoulders, 7-8: elbows, 9-10: wrists
    # 11-12: hips, 13-14: knees, 15-16: ankles
    
    keypoints = {
        'nose': kp_array[0].tolist(),
        'left_shoulder': kp_array[5].tolist(),
        'right_shoulder': kp_array[6].tolist(),
        'left_elbow': kp_array[7].tolist(),
        'right_elbow': kp_array[8].tolist(),
        'left_wrist': kp_array[9].tolist(),
        'right_wrist': kp_array[10].tolist(),
        'left_hip': kp_array[11].tolist(),
        'right_hip': kp_array[12].tolist(),
        'left_knee': kp_array[13].tolist(),
        'right_knee': kp_array[14].tolist(),
        'left_ankle': kp_array[15].tolist(),
        'right_ankle': kp_array[16].tolist(),
    }
    
    # Calculate center points
    shoulder_center = (kp_array[5] + kp_array[6]) / 2.0
    hip_center = (kp_array[11] + kp_array[12]) / 2.0
    
    # ========================================
    # CALCULATE ALL RELEVANT ANGLES
    # ========================================
    
    angles = {}
    
    # KNEE ANGLES (most important for squat depth)
    angles['left_knee'] = compute_angle_deg(
        kp_array[11],  # left hip
        kp_array[13],  # left knee
        kp_array[15]   # left ankle
    )
    
    angles['right_knee'] = compute_angle_deg(
        kp_array[12],  # right hip
        kp_array[14],  # right knee
        kp_array[16]   # right ankle
    )
    
    angles['avg_knee'] = (angles['left_knee'] + angles['right_knee']) / 2.0
    
    # HIP ANGLES (back-knee-hip angle)
    angles['left_hip'] = compute_angle_deg(
        kp_array[5],   # left shoulder
        kp_array[11],  # left hip
        kp_array[13]   # left knee
    )
    
    angles['right_hip'] = compute_angle_deg(
        kp_array[6],   # right shoulder
        kp_array[12],  # right hip
        kp_array[14]   # right knee
    )
    
    angles['avg_hip'] = (angles['left_hip'] + angles['right_hip']) / 2.0
    
    # ANKLE ANGLES
    angles['left_ankle'] = compute_angle_deg(
        kp_array[13],  # left knee
        kp_array[15],  # left ankle
        [kp_array[15][0], kp_array[15][1] + 50]  # point below ankle (for floor reference)
    )
    
    angles['right_ankle'] = compute_angle_deg(
        kp_array[14],  # right knee
        kp_array[16],  # right ankle
        [kp_array[16][0], kp_array[16][1] + 50]  # point below ankle
    )
    
    # BACK ANGLE (shoulder-hip-knee)
    angles['left_back'] = compute_angle_deg(
        kp_array[5],   # left shoulder
        kp_array[11],  # left hip
        kp_array[13]   # left knee
    )
    
    angles['right_back'] = compute_angle_deg(
        kp_array[6],   # right shoulder
        kp_array[12],  # right hip
        kp_array[14]   # right knee
    )
    
    # TORSO LEAN (angle from vertical)
    angles['torso_lean'] = compute_torso_angle(shoulder_center, hip_center)
    
    # ========================================
    # PRINT SUMMARY
    # ========================================
    
    print(f"\n📐 Extracted Angles:")
    print(f"   Knees:  L={angles['left_knee']:.1f}°  R={angles['right_knee']:.1f}°  Avg={angles['avg_knee']:.1f}°")
    print(f"   Hips:   L={angles['left_hip']:.1f}°  R={angles['right_hip']:.1f}°  Avg={angles['avg_hip']:.1f}°")
    print(f"   Ankles: L={angles['left_ankle']:.1f}°  R={angles['right_ankle']:.1f}°")
    print(f"   Torso Lean: {angles['torso_lean']:.1f}° from vertical")
    
    # ========================================
    # CREATE OUTPUT DICTIONARY
    # ========================================
    
    reference_data = {
        'position': position_name,
        'image_path': image_path,
        'angles': angles,
        'keypoints': keypoints,
        'metadata': {
            'image_width': img.shape[1],
            'image_height': img.shape[0],
            'detection_confidence': float(confs.mean()),
        }
    }
    
    return reference_data

# ========================================
# VISUALIZATION (Optional)
# ========================================

def visualize_angles(image_path, reference_data, output_path=None):
    """
    Draw keypoints and angles on the image for visualization.
    
    PARAMETERS:
        image_path: Path to original image
        reference_data: Dictionary with keypoints and angles
        output_path: Optional path to save annotated image
    """
    img = cv2.imread(image_path)
    keypoints = reference_data['keypoints']
    angles = reference_data['angles']
    
    # Draw keypoints
    for name, (x, y) in keypoints.items():
        cv2.circle(img, (int(x), int(y)), 5, (0, 255, 0), -1)
        cv2.putText(img, name.split('_')[0][0].upper(), (int(x)+10, int(y)), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
    # Draw skeleton connections
    connections = [
        ('left_shoulder', 'left_elbow'), ('left_elbow', 'left_wrist'),
        ('right_shoulder', 'right_elbow'), ('right_elbow', 'right_wrist'),
        ('left_shoulder', 'right_shoulder'),
        ('left_shoulder', 'left_hip'), ('right_shoulder', 'right_hip'),
        ('left_hip', 'right_hip'),
        ('left_hip', 'left_knee'), ('left_knee', 'left_ankle'),
        ('right_hip', 'right_knee'), ('right_knee', 'right_ankle'),
    ]
    
    for start, end in connections:
        x1, y1 = keypoints[start]
        x2, y2 = keypoints[end]
        cv2.line(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 200, 255), 2)
    
    # Add angle annotations
    y_offset = 30
    annotations = [
        f"Avg Knee: {angles['avg_knee']:.1f}°",
        f"Avg Hip: {angles['avg_hip']:.1f}°",
        f"Torso Lean: {angles['torso_lean']:.1f}°",
    ]
    
    for i, text in enumerate(annotations):
        cv2.putText(img, text, (10, y_offset + i*30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    
    if output_path:
        cv2.imwrite(output_path, img)
        print(f"✓ Visualization saved to: {output_path}")
    
    return img

# ========================================
# MAIN EXECUTION
# ========================================

def main():
    """
    Main function to extract reference angles from both squat positions.
    """
    print("\n" + "="*60)
    print("SQUAT REFERENCE ANGLE EXTRACTION")
    print("="*60)
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    try:
        # Extract DOWN position
        down_data = extract_angles_from_image(DOWN_IMAGE, "down")
        
        # Save to JSON
        with open(DOWN_JSON, 'w') as f:
            json.dump(down_data, f, indent=2)
        print(f"\n✓ Reference saved to: {DOWN_JSON}")
        
        # Visualize (optional)
        vis_down = visualize_angles(DOWN_IMAGE, down_data, 
                                     os.path.join(OUTPUT_DIR, "squat_down_annotated.png"))
        
    except Exception as e:
        print(f"\n❌ Error processing DOWN position: {e}")
    
    try:
        # Extract UP position
        up_data = extract_angles_from_image(UP_IMAGE, "up")
        
        # Save to JSON
        with open(UP_JSON, 'w') as f:
            json.dump(up_data, f, indent=2)
        print(f"\n✓ Reference saved to: {UP_JSON}")
        
        # Visualize (optional)
        vis_up = visualize_angles(UP_IMAGE, up_data,
                                   os.path.join(OUTPUT_DIR, "squat_up_annotated.png"))
        
    except Exception as e:
        print(f"\n❌ Error processing UP position: {e}")
    
    print("\n" + "="*60)
    print("✓ EXTRACTION COMPLETE")
    print("="*60)
    print(f"\nReference files saved to: {OUTPUT_DIR}/")
    print("  - squat_down.json")
    print("  - squat_up.json")
    print("  - squat_down_annotated.png (visualization)")
    print("  - squat_up_annotated.png (visualization)")
    print("\nThese reference angles can now be used in realtime_detection.py")
    print("to compare user form against correct technique!")

if __name__ == "__main__":
    main()
