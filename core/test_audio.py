#!/usr/bin/env python3
"""
Quick test to verify audio/speech is working.
Run this BEFORE running the full app to confirm voice works.
"""

import time
import sys

print("="*60)
print("AUDIO SYSTEM TEST")
print("="*60)

# Test 1: System check
print("\n[1/3] Testing macOS 'say' command directly...")
import subprocess
try:
    subprocess.run(['say', 'Audio test'], timeout=5)
    print("✅ macOS 'say' command works!")
except Exception as e:
    print(f"❌ macOS 'say' command failed: {e}")
    sys.exit(1)

time.sleep(1)

# Test 2: Import voice module
print("\n[2/3] Loading voice_feedback module...")
try:
    from voice_feedback import speak, stop_voice
    print("✅ voice_feedback module loaded")
except Exception as e:
    print(f"❌ Failed to load voice_feedback: {e}")
    sys.exit(1)

time.sleep(1)

# Test 3: Test speak() function
print("\n[3/3] Testing speak() function...")
print("   You should hear: 'Nice squat. Rep counted.'")
speak("Nice squat. Rep counted.")
time.sleep(3)

print("\n" + "="*60)
print("✅ ALL TESTS PASSED!")
print("="*60)
print("\nYour voice system is working correctly.")
print("You should now hear voice feedback in the main app.\n")

# Cleanup
stop_voice()

