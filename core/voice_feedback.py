"""
VOICE FEEDBACK MODULE
=====================
Contains text-to-speech system and general feedback generation logic.
"""

import threading
import queue
import pyttsx3

# ========================================
# TEXT-TO-SPEECH SYSTEM (Thread-Safe)
# ========================================

# Create a queue for voice messages (allows non-blocking speech)
voice_q = queue.Queue()

# Initialize pyttsx3 text-to-speech engine
engine = pyttsx3.init()
engine.setProperty("rate", 160)  # Speech rate (words per minute)

def _voice_worker():
    """
    Background thread worker that processes the voice queue.
    
    HOW IT WORKS:
        - Runs in a separate thread to prevent blocking the main video loop
        - Continuously checks the queue for messages to speak
        - None message = signal to stop the worker
    
    WHY THREADED:
        - Speaking text is slow (blocks for 1-2 seconds)
        - Without threading, video would freeze during speech
        - Thread allows smooth video + concurrent speech
    """
    while True:
        text = voice_q.get()  # Wait for a message
        if text is None:      # None = shutdown signal
            break
        engine.say(text)      # Synthesize speech
        engine.runAndWait()   # Play audio (blocking in this thread only)
        voice_q.task_done()   # Mark task as complete

# Start the voice worker thread (daemon = auto-closes when main program exits)
threading.Thread(target=_voice_worker, daemon=True).start()

def speak(text):
    """
    Queue text to be spoken (non-blocking).
    
    PARAMETERS:
        text: String to be spoken aloud
    
    USAGE:
        speak("Good squat!")  # Returns immediately, speaks in background
    """
    if text:
        voice_q.put(text)

def stop_voice():
    """Stop the voice worker thread."""
    voice_q.put(None)

# ========================================
# GENERAL FEEDBACK GENERATION
# ========================================

def feedback_generator(metrics, exercise, last_feedback_time, feedback_cooldown=2.0):
    """
    Generate natural-language coaching feedback based on exercise metrics.
    
    This is a dispatcher that calls exercise-specific feedback functions.
    
    PARAMETERS:
        metrics: Dictionary of joint angles (e.g., {"left_knee": 120, "right_knee": 115})
        exercise: String indicating current exercise ('Squat', 'Arm Circle', or None)
        last_feedback_time: Timestamp of last spoken feedback (for throttling)
        feedback_cooldown: Seconds between vocal feedback messages
    
    RETURNS:
        (screen_text, speak_text):
            - screen_text: String to display on screen (always provided)
            - speak_text: String to speak aloud (None if no speech needed)
    
    THROTTLING:
        - Vocal feedback only given if feedback_cooldown seconds have passed
        - Prevents annoying repetition
        - Screen text updates every frame
    """
    # Import exercise-specific feedback functions
    from squat import generate_squat_feedback
    from arm_circle import generate_arm_circle_feedback
    
    if exercise == "Squat":
        return generate_squat_feedback(metrics, last_feedback_time, feedback_cooldown)
    elif exercise == "Arm Circle":
        return generate_arm_circle_feedback(metrics, last_feedback_time, feedback_cooldown)
    else:
        return "No exercise detected.", None
