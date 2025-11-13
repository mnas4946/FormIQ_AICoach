// ===== EXERCISE PAGE FUNCTIONALITY =====

let currentReps = 0;
let targetReps = 10;
let isExerciseActive = false;
let isPaused = false;

// Start session - hides timeline and shows exercise view
function startSession() {
    const timelineOverlay = document.getElementById('timelineOverlay');
    const exerciseMain = document.getElementById('exerciseMain');
    
    if (timelineOverlay) {
        timelineOverlay.style.display = 'none';
    }
    
    if (exerciseMain) {
        exerciseMain.style.display = 'flex';
    }
}

// Feedback messages that rotate
const feedbackMessages = [
    "Keep your back straight and lower yourself slowly.",
    "Great form! Try to go a bit deeper.",
    "Excellent! Remember to breathe steadily.",
    "Nice work! Keep your core engaged.",
    "Perfect! Maintain that posture."
];

// Stage 1 (Arm Circles) specific feedback
const stage1FeedbackMessages = {
    initial: "Hold your arm straight to keep proper shoulder alignment.",
    rotating: [
        "Good form, remember to breathe steadily",
        "Excellent, maintain the form for 30 seconds",
        "Try to push your shoulder upwards",
        "Keep your arm straight"
    ]
};

let feedbackIndex = 0;
let feedbackTimer = null;
let exerciseStartTime = null;

// Start exercise / camera
function startExercise() {
    isExerciseActive = true;
    
    // Hide placeholder, show active state
    const placeholder = document.querySelector('.camera-placeholder');
    if (placeholder) {
        placeholder.style.display = 'none';
    }
    
    // Start simulated rep counting (in real app, this would be from pose detection)
    simulateExercise();
}

// Simulate exercise progress for demo purposes
function simulateExercise() {
    if (!isExerciseActive || isPaused) return;
    
    const interval = setInterval(() => {
        if (!isExerciseActive || isPaused || currentReps >= targetReps) {
            clearInterval(interval);
            if (currentReps >= targetReps) {
                showCompletion();
            }
            return;
        }
        
        // Simulate a rep every 3 seconds
        setTimeout(() => {
            if (isExerciseActive && !isPaused) {
                incrementRep();
                rotateFeedback();
            }
        }, 3000);
        
    }, 3000);
}

// Increment rep counter
function incrementRep() {
    if (currentReps < targetReps) {
        currentReps++;
        updateRepDisplay();
        updateProgress();
        updateSteps();
    }
    
    if (currentReps >= targetReps) {
        setTimeout(showCompletion, 1000);
    }
}

// Update rep display
function updateRepDisplay() {
    const repsElement = document.getElementById('currentReps');
    if (repsElement) {
        repsElement.textContent = currentReps;
        
        // Update circular progress
        const progressCircle = document.getElementById('progressCircle');
        if (progressCircle) {
            const circumference = 2 * Math.PI * 60; // radius is 60
            const progress = currentReps / targetReps;
            const offset = circumference - (progress * circumference);
            progressCircle.style.strokeDashoffset = offset;
        }
    }
}

// Update progress bar
function updateProgress() {
    const progress = (currentReps / targetReps) * 100;
    const progressFill = document.getElementById('progressFill');
    const progressPercent = document.getElementById('progressPercent');
    
    if (progressFill) {
        progressFill.style.width = progress + '%';
    }
    
    if (progressPercent) {
        progressPercent.textContent = Math.round(progress);
    }
}

// Update exercise steps
function updateSteps() {
    const steps = document.querySelectorAll('.step-item');
    
    // Simple logic: complete steps based on progress
    if (currentReps >= 3) {
        steps[0]?.classList.add('completed');
        steps[0]?.classList.remove('active');
    }
    
    if (currentReps >= 6) {
        steps[1]?.classList.add('completed');
        steps[1]?.classList.remove('active');
        steps[2]?.classList.add('active');
    }
    
    if (currentReps >= 10) {
        steps[2]?.classList.add('completed');
        steps[2]?.classList.remove('active');
    }
}

// Rotate feedback messages
function rotateFeedback() {
    const feedbackText = document.getElementById('feedbackText');
    if (feedbackText) {
        feedbackIndex = (feedbackIndex + 1) % feedbackMessages.length;
        feedbackText.textContent = feedbackMessages[feedbackIndex];
    }
}

// Toggle pause
function togglePause() {
    isPaused = !isPaused;
    const pauseBtn = document.querySelector('.pause-btn');
    
    if (pauseBtn) {
        if (isPaused) {
            // Stop feedback timer when paused
            stopFeedbackTimer();
            
            pauseBtn.innerHTML = `
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M5 3L19 12L5 21V3Z" fill="currentColor"/>
                </svg>
                Resume
            `;
        } else {
            // Resume feedback timer
            const stage = getExerciseStage();
            if (stage === 'stage1') {
                startStage1Feedback();
            } else if (stage === 'stage4') {
                startStage4Feedback();
            }
            
            pauseBtn.innerHTML = `
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M10 4H6V20H10V4Z" fill="currentColor"/>
                    <path d="M18 4H14V20H18V4Z" fill="currentColor"/>
                </svg>
                Pause
            `;
            simulateExercise();
        }
    }
}

// Restart exercise
function restartExercise() {
    currentReps = 0;
    isExerciseActive = false;
    isPaused = false;
    
    // Stop feedback timer
    stopFeedbackTimer();
    
    // Stop camera and pose detection
    if (videoElement && videoElement.srcObject) {
        videoElement.srcObject.getTracks().forEach(track => track.stop());
    }
    if (camera) {
        camera.stop();
    }
    if (videoElement) videoElement.remove();
    if (canvasElement) canvasElement.remove();
    
    videoElement = null;
    canvasElement = null;
    canvasCtx = null;
    pose = null;
    camera = null;
    
    updateRepDisplay();
    updateProgress();
    
    // Reset steps
    const steps = document.querySelectorAll('.step-item');
    steps.forEach(step => {
        step.classList.remove('completed', 'active');
    });
    steps[0]?.classList.add('active');
    
    // Hide completion overlay
    const overlay = document.getElementById('completionOverlay');
    if (overlay) {
        overlay.classList.remove('active');
    }
    
    // Hide feedback overlay
    const feedbackOverlay = document.getElementById('feedbackOverlay');
    if (feedbackOverlay) {
        feedbackOverlay.style.display = 'none';
    }
    
    // Show placeholder again
    const placeholder = document.querySelector('.camera-placeholder');
    if (placeholder) {
        placeholder.style.display = 'flex';
    }
}

// Show completion overlay
function showCompletion() {
    const overlay = document.getElementById('completionOverlay');
    if (overlay) {
        overlay.classList.add('active');
    }
    isExerciseActive = false;
    
    // Stop feedback timer when exercise completes
    stopFeedbackTimer();
}

// Cancel session and return to dashboard
function cancelSession() {
    if (confirm('Are you sure you want to cancel this session? Your progress will not be saved.')) {
        window.location.href = 'index.html';
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Check if we're on the exercise page
    if (document.getElementById('currentReps')) {
        updateRepDisplay();
        updateProgress();
    }
});

// Add smooth scroll behavior
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth'
            });
        }
    });
});

// ===== NEW EXERCISE PAGE FUNCTIONS =====

// Toggle tracking panel
function togglePanel() {
    const panel = document.getElementById('trackingPanel');
    const btnText = document.getElementById('panelBtnText');
    const toggleIcon = document.getElementById('toggleIcon');
    
    if (panel) {
        panel.classList.toggle('hidden');
        
        if (panel.classList.contains('hidden')) {
            btnText.textContent = 'Show Panel';
            toggleIcon.setAttribute('d', 'M13 10L10 13L7 10M13 6L10 9L7 6');
        } else {
            btnText.textContent = 'Hide Panel';
            toggleIcon.setAttribute('d', 'M7 10L10 7L13 10M7 14L10 11L13 14');
        }
    }
}

// ===== WEBCAM & POSE DETECTION =====

let videoElement = null;
let canvasElement = null;
let canvasCtx = null;
let pose = null;
let camera = null;

// Detect which exercise stage we're on
function getExerciseStage() {
    const title = document.title.toLowerCase();
    if (title.includes('stage 1')) {
        return 'stage1';
    } else if (title.includes('stage 4')) {
        return 'stage4';
    }
    return 'unknown';
}

// Stage 1 specific feedback loop
function startStage1Feedback() {
    const feedbackText = document.getElementById('feedbackText');
    if (!feedbackText) return;
    
    exerciseStartTime = Date.now();
    let rotatingIndex = 0;
    
    // Show initial message for 30 seconds
    feedbackText.textContent = stage1FeedbackMessages.initial;
    
    // After 30 seconds, start rotating messages every 10 seconds
    feedbackTimer = setTimeout(() => {
        // Function to rotate through messages
        const rotateMessages = () => {
            feedbackText.textContent = stage1FeedbackMessages.rotating[rotatingIndex];
            rotatingIndex = (rotatingIndex + 1) % stage1FeedbackMessages.rotating.length;
        };
        
        // Show first rotating message immediately
        rotateMessages();
        
        // Then continue every 10 seconds
        feedbackTimer = setInterval(rotateMessages, 10000);
    }, 30000); // Wait 30 seconds before starting rotation
}

// Stage 4 feedback loop (original behavior)
function startStage4Feedback() {
    const feedbackText = document.getElementById('feedbackText');
    if (!feedbackText) return;
    
    exerciseStartTime = Date.now();
    feedbackIndex = 0;
    
    // Show first message
    feedbackText.textContent = feedbackMessages[feedbackIndex];
    
    // Rotate every 3 seconds
    feedbackTimer = setInterval(() => {
        feedbackIndex = (feedbackIndex + 1) % feedbackMessages.length;
        feedbackText.textContent = feedbackMessages[feedbackIndex];
    }, 3000);
}

// Stop feedback timer
function stopFeedbackTimer() {
    if (feedbackTimer) {
        clearTimeout(feedbackTimer);
        clearInterval(feedbackTimer);
        feedbackTimer = null;
    }
    exerciseStartTime = null;
}

// Start camera with real webcam and pose detection
async function startCamera() {
    const placeholder = document.querySelector('.camera-placeholder');
    const cameraView = document.querySelector('.camera-view-new');
    const feedbackOverlay = document.getElementById('feedbackOverlay');
    
    if (!placeholder || !cameraView) return;
    
    // Hide placeholder
    placeholder.style.display = 'none';
    
    // Create video element for webcam
    videoElement = document.createElement('video');
    videoElement.style.position = 'absolute';
    videoElement.style.width = '100%';
    videoElement.style.height = '100%';
    videoElement.style.objectFit = 'cover';
    videoElement.autoplay = true;
    videoElement.playsInline = true;
    
    // Create canvas for drawing keypoints
    canvasElement = document.createElement('canvas');
    canvasElement.style.position = 'absolute';
    canvasElement.style.width = '100%';
    canvasElement.style.height = '100%';
    canvasElement.style.top = '0';
    canvasElement.style.left = '0';
    canvasElement.style.zIndex = '10';
    
    // Add elements to camera view
    cameraView.appendChild(videoElement);
    cameraView.appendChild(canvasElement);
    
    canvasCtx = canvasElement.getContext('2d');
    
    try {
        // Request webcam access
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 1280 },
                height: { ideal: 720 }
            },
            audio: false
        });
        
        videoElement.srcObject = stream;
        
        // Wait for video metadata to load
        await new Promise((resolve) => {
            videoElement.onloadedmetadata = () => {
                videoElement.play();
                resolve();
            };
        });
        
        // Set canvas size to match video
        canvasElement.width = videoElement.videoWidth;
        canvasElement.height = videoElement.videoHeight;
        
        // Show feedback overlay with initial message
        if (feedbackOverlay) {
            feedbackOverlay.style.display = 'block';
            feedbackOverlay.style.opacity = '1';
            feedbackOverlay.style.zIndex = '100';
        }
        
        // Start stage-specific feedback
        const stage = getExerciseStage();
        if (stage === 'stage1') {
            startStage1Feedback();
        } else if (stage === 'stage4') {
            startStage4Feedback();
        } else {
            // Fallback for unknown stages
            const feedbackText = document.getElementById('feedbackText');
            if (feedbackText) {
                feedbackText.textContent = feedbackMessages[0];
            }
        }
        
        // Initialize MediaPipe Pose
        if (typeof Pose !== 'undefined') {
            initializePoseDetection();
        } else {
            console.log('MediaPipe Pose not loaded, showing camera only');
        }
        
        // Start demo rep counting
        isExerciseActive = true;
        simulateDemoExercise();
        
    } catch (error) {
        console.error('Error accessing webcam:', error);
        placeholder.style.display = 'flex';
        placeholder.innerHTML = `
            <p class="camera-text" style="color: #EF4444;">Camera access denied or unavailable</p>
            <p class="camera-text" style="font-size: 14px;">Please allow camera permissions and try again</p>
            <button class="start-camera-btn" onclick="startCamera()">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M6 4L15 10L6 16V4Z" fill="currentColor"/>
                </svg>
                Retry
            </button>
        `;
    }
}

// Initialize MediaPipe Pose Detection
function initializePoseDetection() {
    if (typeof Pose === 'undefined') {
        console.log('MediaPipe Pose library not available');
        return;
    }
    
    pose = new Pose({
        locateFile: (file) => {
            return `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`;
        }
    });
    
    pose.setOptions({
        modelComplexity: 1,
        smoothLandmarks: true,
        enableSegmentation: false,
        smoothSegmentation: false,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
    });
    
    pose.onResults(onPoseResults);
    
    // Start processing video frames
    if (videoElement) {
        camera = new Camera(videoElement, {
            onFrame: async () => {
                if (pose && videoElement) {
                    await pose.send({ image: videoElement });
                }
            },
            width: 1280,
            height: 720
        });
        camera.start();
    }
}

// Handle pose detection results
function onPoseResults(results) {
    if (!canvasElement || !canvasCtx) return;
    
    // Clear canvas
    canvasCtx.save();
    canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
    
    // Draw pose landmarks if detected
    if (results.poseLandmarks) {
        drawPoseLandmarks(results.poseLandmarks);
    }
    
    canvasCtx.restore();
}

// Draw pose keypoints and connections (matching realtime_detection.py style)
function drawPoseLandmarks(landmarks) {
    if (!canvasCtx || !landmarks) return;
    
    const width = canvasElement.width;
    const height = canvasElement.height;
    
    // Define connections (same as COCO format used in YOLOv8)
    const connections = [
        [0, 1], [0, 2], [1, 3], [2, 4],  // Face
        [5, 6],  // Shoulders
        [5, 7], [7, 9],  // Left arm
        [6, 8], [8, 10],  // Right arm
        [5, 11], [6, 12],  // Torso
        [11, 12],  // Hips
        [11, 13], [13, 15],  // Left leg
        [12, 14], [14, 16]   // Right leg
    ];
    
    // Draw connections (bones)
    canvasCtx.strokeStyle = '#00FF00';
    canvasCtx.lineWidth = 3;
    
    connections.forEach(([startIdx, endIdx]) => {
        const start = landmarks[startIdx];
        const end = landmarks[endIdx];
        
        if (start && end && start.visibility > 0.5 && end.visibility > 0.5) {
            canvasCtx.beginPath();
            canvasCtx.moveTo(start.x * width, start.y * height);
            canvasCtx.lineTo(end.x * width, end.y * height);
            canvasCtx.stroke();
        }
    });
    
    // Draw keypoints (circles)
    landmarks.forEach((landmark, index) => {
        if (landmark && landmark.visibility > 0.5) {
            const x = landmark.x * width;
            const y = landmark.y * height;
            
            // Draw keypoint circle
            canvasCtx.beginPath();
            canvasCtx.arc(x, y, 5, 0, 2 * Math.PI);
            canvasCtx.fillStyle = '#00FF00';
            canvasCtx.fill();
            canvasCtx.strokeStyle = '#FFFFFF';
            canvasCtx.lineWidth = 1;
            canvasCtx.stroke();
        }
    });
}

// Simulate exercise for demo (no backend)
function simulateDemoExercise() {
    if (!isExerciseActive || isPaused) return;
    
    // Simulate a rep every 3 seconds
    const interval = setInterval(() => {
        if (!isExerciseActive || isPaused || currentReps >= targetReps) {
            clearInterval(interval);
            if (currentReps >= targetReps) {
                setTimeout(showCompletion, 1000);
            }
            return;
        }
        
        currentReps++;
        updateFloatingReps();
        updateProgressRing();
        // Note: Feedback is now handled by stage-specific timers
        
    }, 3000);
}

// Update floating rep counter
function updateFloatingReps() {
    const floatingReps = document.getElementById('floatingReps');
    if (floatingReps) {
        floatingReps.textContent = `${currentReps}/${targetReps}`;
    }
}

// Update progress ring
function updateProgressRing() {
    const progress = (currentReps / targetReps) * 100;
    const progressPercent = document.getElementById('progressPercent');
    const progressCircle = document.getElementById('progressCircle');
    
    if (progressPercent) {
        progressPercent.textContent = Math.round(progress);
    }
    
    if (progressCircle) {
        const circumference = 327; // 2 * π * 52
        const offset = circumference - (progress / 100) * circumference;
        progressCircle.style.strokeDashoffset = offset;
    }
}

// Next exercise
function nextExercise() {
    alert('Next exercise would load here');
}

// ============================================
// Test Camera Page Functions
// ============================================

let testVideo = null;
let testCanvas = null;
let testPose = null;
let testCamera = null;

async function startQuickTest() {
    const demoArea = document.getElementById('demoArea');
    const placeholder = document.getElementById('placeholderText');
    const feedbackOverlay = document.getElementById('testFeedbackOverlay');
    
    if (placeholder) placeholder.style.display = 'none';
    
    // Create video element
    testVideo = document.createElement('video');
    testVideo.autoplay = true;
    testVideo.playsInline = true;
    
    // Create canvas for keypoints
    testCanvas = document.createElement('canvas');
    testCanvas.width = 640;
    testCanvas.height = 480;
    
    demoArea.appendChild(testVideo);
    demoArea.appendChild(testCanvas);
    
    const ctx = testCanvas.getContext('2d');
    
    try {
        // Get webcam stream
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480 },
            audio: false
        });
        
        testVideo.srcObject = stream;
        
        // Show feedback overlay
        if (feedbackOverlay) {
            feedbackOverlay.style.display = 'block';
            feedbackOverlay.style.opacity = '1';
            feedbackOverlay.style.zIndex = '100';
        }
        
        // Initialize MediaPipe Pose
        testPose = new Pose({
            locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`
        });
        
        testPose.setOptions({
            modelComplexity: 1,
            smoothLandmarks: true,
            minDetectionConfidence: 0.5,
            minTrackingConfidence: 0.5
        });
        
        testPose.onResults((results) => {
            ctx.clearRect(0, 0, testCanvas.width, testCanvas.height);
            
            if (results.poseLandmarks) {
                // Draw connections
                const connections = [
                    [0, 1], [0, 2], [1, 3], [2, 4],
                    [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],
                    [5, 11], [6, 12], [11, 12],
                    [11, 13], [13, 15], [12, 14], [14, 16]
                ];
                
                ctx.strokeStyle = '#00FF00';
                ctx.lineWidth = 3;
                
                connections.forEach(([start, end]) => {
                    const s = results.poseLandmarks[start];
                    const e = results.poseLandmarks[end];
                    if (s && e && s.visibility > 0.5 && e.visibility > 0.5) {
                        ctx.beginPath();
                        ctx.moveTo(s.x * testCanvas.width, s.y * testCanvas.height);
                        ctx.lineTo(e.x * testCanvas.width, e.y * testCanvas.height);
                        ctx.stroke();
                    }
                });
                
                // Draw keypoints
                results.poseLandmarks.forEach(landmark => {
                    if (landmark.visibility > 0.5) {
                        ctx.beginPath();
                        ctx.arc(landmark.x * testCanvas.width, landmark.y * testCanvas.height, 5, 0, 2 * Math.PI);
                        ctx.fillStyle = '#00FF00';
                        ctx.fill();
                        ctx.strokeStyle = '#FFFFFF';
                        ctx.lineWidth = 1;
                        ctx.stroke();
                    }
                });
            }
        });
        
        // Start camera
        testCamera = new Camera(testVideo, {
            onFrame: async () => {
                await testPose.send({ image: testVideo });
            },
            width: 640,
            height: 480
        });
        testCamera.start();
        
    } catch (error) {
        console.error('Error:', error);
        alert('Camera access denied or unavailable. Please allow camera permissions and try again.');
        stopQuickTest();
    }
}

function stopQuickTest() {
    const demoArea = document.getElementById('demoArea');
    const placeholder = document.getElementById('placeholderText');
    const feedbackOverlay = document.getElementById('testFeedbackOverlay');
    
    if (testVideo && testVideo.srcObject) {
        testVideo.srcObject.getTracks().forEach(track => track.stop());
    }
    
    if (testCamera) {
        testCamera.stop();
    }
    
    if (testVideo) testVideo.remove();
    if (testCanvas) testCanvas.remove();
    
    testVideo = null;
    testCanvas = null;
    testPose = null;
    testCamera = null;
    
    if (placeholder) placeholder.style.display = 'block';
    if (feedbackOverlay) feedbackOverlay.style.display = 'none';
}

