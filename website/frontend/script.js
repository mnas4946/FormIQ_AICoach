// ===== EXERCISE PAGE FUNCTIONALITY =====

let currentReps = 0;
let targetReps = 10;
let isExerciseActive = false;
let isPaused = false;

// ===== BACKEND CONNECTION =====
let socket = null;
let videoStream = null;
let videoElement = null;
let canvas = null;
let ctx = null;
const BACKEND_URL = 'http://localhost:5000';
const FRAME_RATE = 10; // Send 10 frames per second to backend

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

let feedbackIndex = 0;

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
            pauseBtn.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M5 3L15 10L5 17V3Z" fill="currentColor"/>
                </svg>
                Resume
            `;
        } else {
            pauseBtn.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M8 4H6V16H8V4Z" fill="currentColor"/>
                    <path d="M14 4H12V16H14V4Z" fill="currentColor"/>
                </svg>
                Pause
            `;
            
            // Resume frame processing if camera is active
            if (isExerciseActive && socket && socket.connected) {
                startFrameProcessing();
            }
        }
    }
}

// Restart exercise
function restartExercise() {
    currentReps = 0;
    isExerciseActive = false;
    isPaused = false;
    
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
    
    // Stop video stream
    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
    }
    
    // Disconnect socket
    if (socket && socket.connected) {
        socket.emit('end_session');
        socket.disconnect();
    }
    
    // Update final stats
    const finalReps = document.getElementById('finalReps');
    if (finalReps) {
        finalReps.textContent = currentReps;
    }
}

// Cancel session and return to dashboard
function cancelSession() {
    if (confirm('Are you sure you want to cancel this session? Your progress will not be saved.')) {
        // Stop video stream
        if (videoStream) {
            videoStream.getTracks().forEach(track => track.stop());
        }
        
        // Disconnect socket
        if (socket && socket.connected) {
            socket.emit('end_session');
            socket.disconnect();
        }
        
        // Stop exercise
        isExerciseActive = false;
        
        window.location.href = '/';
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

// Initialize WebSocket connection
function initializeWebSocket() {
    // Load Socket.IO from CDN if not already loaded
    if (typeof io === 'undefined') {
        console.error('Socket.IO not loaded. Please add Socket.IO script to HTML.');
        return;
    }
    
    socket = io(BACKEND_URL);
    
    socket.on('connect', () => {
        console.log('Connected to backend');
        
        // Determine exercise type based on current page
        const exerciseType = getExerciseType();
        
        // Start session
        socket.emit('start_session', { exercise_type: exerciseType });
    });
    
    socket.on('session_started', (data) => {
        console.log('Session started:', data);
    });
    
    socket.on('frame_result', (result) => {
        if (result.success) {
            // Update rep count
            if (result.rep_completed) {
                currentReps = result.rep_count;
                updateFloatingReps();
                updateProgressRing();
                
                // Play sound or animation for rep completion
                console.log(`Rep completed! Total: ${currentReps}`);
            }
            
            // Update feedback
            if (result.feedback) {
                updateFeedback(result.feedback);
            }
            
            // Update form indicators if available
            if (result.angles) {
                updateFormIndicators(result.angles);
            }
            
            // Display annotated frame
            if (result.annotated_frame && videoElement) {
                videoElement.src = result.annotated_frame;
            }
        } else {
            // Handle errors (e.g., person not detected)
            if (result.error) {
                updateFeedback(result.error);
            }
        }
    });
    
    socket.on('error', (error) => {
        console.error('Socket error:', error);
        updateFeedback(error.message);
    });
    
    socket.on('disconnect', () => {
        console.log('Disconnected from backend');
    });
}

// Get exercise type based on current page
function getExerciseType() {
    const path = window.location.pathname;
    
    if (path.includes('stage1')) {
        return 'arm_circle';
    } else if (path.includes('stage4')) {
        return 'squat';
    }
    
    return 'squat'; // default
}

// Start camera and connect to backend
async function startCamera() {
    const placeholder = document.querySelector('.camera-placeholder');
    const feedbackOverlay = document.getElementById('feedbackOverlay');
    const cameraView = document.querySelector('.camera-view-new');
    
    try {
        // Request camera access
        videoStream = await navigator.mediaDevices.getUserMedia({ 
            video: { 
                width: { ideal: 1280 },
                height: { ideal: 720 }
            } 
        });
        
        // Create video element if not exists
        if (!videoElement) {
            videoElement = document.createElement('video');
            videoElement.autoplay = true;
            videoElement.playsInline = true;
            videoElement.style.width = '100%';
            videoElement.style.height = '100%';
            videoElement.style.objectFit = 'cover';
        }
        
        videoElement.srcObject = videoStream;
        
        // Create canvas for frame capture
        if (!canvas) {
            canvas = document.createElement('canvas');
            canvas.width = 640;
            canvas.height = 480;
            ctx = canvas.getContext('2d');
        }
        
        // Replace placeholder with video
        if (placeholder) {
            placeholder.style.display = 'none';
        }
        
        if (cameraView) {
            // Add video element to camera view
            const existingVideo = cameraView.querySelector('video');
            if (existingVideo) {
                existingVideo.remove();
            }
            cameraView.insertBefore(videoElement, cameraView.firstChild);
        }
        
        // Show feedback overlay
        if (feedbackOverlay) {
            feedbackOverlay.style.display = 'block';
        }
        
        // Initialize WebSocket connection
        initializeWebSocket();
        
        // Start sending frames to backend
        isExerciseActive = true;
        startFrameProcessing();
        
        console.log('Camera started successfully');
        
    } catch (error) {
        console.error('Error starting camera:', error);
        
        if (placeholder) {
            placeholder.innerHTML = `
                <p class="camera-text" style="color: #EF4444;">❌ Camera Access Denied</p>
                <p class="camera-text" style="font-size: 14px;">Please allow camera access and try again</p>
                <button class="start-camera-btn" onclick="startCamera()">
                    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M6 4L15 10L6 16V4Z" fill="currentColor"/>
                    </svg>
                    Retry
                </button>
            `;
        }
    }
}

// Process and send frames to backend
function startFrameProcessing() {
    if (!isExerciseActive || isPaused || !socket || !socket.connected) {
        // Retry after 1 second if not connected yet
        if (isExerciseActive && !isPaused && socket && !socket.connected) {
            setTimeout(startFrameProcessing, 1000);
        }
        return;
    }
    
    const processFrame = () => {
        if (!isExerciseActive || isPaused) {
            return;
        }
        
        // Capture frame from video
        if (videoElement && videoElement.readyState === videoElement.HAVE_ENOUGH_DATA) {
            // Draw video frame to canvas
            ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
            
            // Convert canvas to base64 image
            const frameData = canvas.toDataURL('image/jpeg', 0.8);
            
            // Send frame to backend
            socket.emit('process_frame', { frame: frameData });
        }
        
        // Process next frame
        setTimeout(processFrame, 1000 / FRAME_RATE);
    };
    
    processFrame();
}

// Update feedback text on screen
function updateFeedback(feedbackText) {
    const feedbackElement = document.getElementById('feedbackText');
    if (feedbackElement) {
        feedbackElement.textContent = feedbackText;
    }
}

// Update form indicators based on angles
function updateFormIndicators(angles) {
    const formStatus = document.getElementById('formStatus');
    if (!formStatus) return;
    
    // Get exercise type
    const exerciseType = getExerciseType();
    
    // Clear existing indicators
    formStatus.innerHTML = '';
    
    if (exerciseType === 'squat') {
        // Knee depth indicator
        const avgKnee = (angles.left_knee + angles.right_knee) / 2;
        const kneeStatus = avgKnee < 120 ? 'good' : 'warning';
        const kneeText = avgKnee < 90 ? 'Deep' : avgKnee < 120 ? 'Good' : 'Too shallow';
        
        formStatus.innerHTML += `
            <div class="form-indicator ${kneeStatus}">
                <div class="indicator-dot"></div>
                <span>Knee depth: ${kneeText}</span>
            </div>
        `;
        
        // Torso indicator
        const torsoStatus = angles.torso > 150 ? 'good' : 'warning';
        const torsoText = angles.torso > 150 ? 'Straight' : 'Leaning forward';
        
        formStatus.innerHTML += `
            <div class="form-indicator ${torsoStatus}">
                <div class="indicator-dot"></div>
                <span>Torso: ${torsoText}</span>
            </div>
        `;
        
    } else if (exerciseType === 'arm_circle') {
        // Arm straightness
        const avgElbow = (angles.left_elbow + angles.right_elbow) / 2;
        const elbowStatus = avgElbow > 160 ? 'good' : 'warning';
        const elbowText = avgElbow > 160 ? 'Good' : 'Bend less';
        
        formStatus.innerHTML += `
            <div class="form-indicator ${elbowStatus}">
                <div class="indicator-dot"></div>
                <span>Arm straightness: ${elbowText}</span>
            </div>
        `;
        
        // Arm height
        const avgArmAngle = (angles.left_arm_angle + angles.right_arm_angle) / 2;
        const heightStatus = avgArmAngle > 70 ? 'good' : 'warning';
        const heightText = avgArmAngle > 80 ? 'Perfect' : avgArmAngle > 70 ? 'Good' : 'Raise higher';
        
        formStatus.innerHTML += `
            <div class="form-indicator ${heightStatus}">
                <div class="indicator-dot"></div>
                <span>Height: ${heightText}</span>
            </div>
        `;
    }
    
    // Balance indicator (always good for now)
    formStatus.innerHTML += `
        <div class="form-indicator good">
            <div class="indicator-dot"></div>
            <span>Balance: Even</span>
        </div>
    `;
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
        rotateFeedback();
        
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

