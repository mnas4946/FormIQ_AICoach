```bash
$ cd core/
$ python3 realtime_detection.py

============================================================
AI COACH - EXERCISE SELECTION
============================================================

Available exercises:
  [1] Squat
  [2] Arm Circle
  [3] Both (track both simultaneously)

Select exercise (1/2/3): 1

✓ Selected: SQUAT
✓ Loading model from: .../core/yolov8n-pose.pt
✓ Loaded squat reference angles:
   DOWN: Avg knee = 56.1°
   UP:   Avg knee = 165.9°

============================================================
STARTING AI COACH
============================================================
Exercise: Squat

Controls:
  'q' - Quit
  'p' - Pause/Resume
  'c' - Calibrate (capture scale)
============================================================

[Camera window opens - start exercising!]

[When you press 'q':]

============================================================
AI COACH SESSION ENDED
============================================================
Final rep counts:
  Squats: 15
============================================================
```

---

## 🎉 You're Ready!

Just run:
```bash
cd core/
python3 realtime_detection.py
```

And start exercising! 💪

