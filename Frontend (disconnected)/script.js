// ===== EXERCISE PAGE FUNCTIONALITY =====

let currentReps = 0;
let targetReps = 10;
let isExerciseActive = false;
let isPaused = false;

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
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M5 3L19 12L5 21V3Z" fill="currentColor"/>
                </svg>
                Resume
            `;
        } else {
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

