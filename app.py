from flask import Flask, render_template, Response
import face_recognition
import os
import cv2
import time
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python import BaseOptions

app = Flask(__name__)

known_face_encodings = []
known_face_names = []

if os.path.exists("known_faces"):
    for person_name in os.listdir("known_faces"):
        person_dir = os.path.join("known_faces", person_name)
        if os.path.isdir(person_dir):
            for filename in os.listdir(person_dir):
                if filename.lower().endswith((".jpg", ".jpeg", ".png")):
                    path = os.path.join(person_dir, filename)
                    image = face_recognition.load_image_file(path)
                    encodings = face_recognition.face_encodings(image, model="large")
                    if encodings:
                        known_face_encodings.append(encodings[0])
                        known_face_names.append(person_name.capitalize())
                    else:
                        print(f"[WARN] No face found in training image: {path}")

print(f"[INFO] Loaded {len(known_face_encodings)} known face(s): {set(known_face_names)}")

options = vision.FaceLandmarkerOptions( base_options=BaseOptions(model_asset_path="face_landmarker.task"), running_mode=vision.RunningMode.VIDEO, num_faces=1,
                                        min_face_detection_confidence=0.5,
                                        min_face_presence_confidence=0.5,
                                        min_tracking_confidence=0.5
                                        )
detector = vision.FaceLandmarker.create_from_options(options)

camera = None
current_identity = ""
current_names = []
last_face_locations = []
face_count = 0
start_time = None
fps = 0
recognition_enabled = True

def generate_frames():
    global camera, current_identity, face_count, fps, last_face_locations, current_names
    counter = 0
    prev_time = 0

    while(True):
        if camera is None:
            break
        success, frame = camera.read()
        if not success or frame is None:
            continue

        curr_time = time.time()
        fps = 1 / (curr_time - prev_time) if prev_time != 0 else 0
        prev_time = curr_time

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        mp_image = mp.Image(mp.ImageFormat.SRGB, rgb_frame)
        frame_timestamp_ms = int(time.time() * 1000)
        detection_result = detector.detect_for_video(mp_image, frame_timestamp_ms)

        if detection_result.face_landmarks:
            face_count = len(detection_result.face_landmarks)
            for face_landmarks in detection_result.face_landmarks:
                for landmark in face_landmarks:
                    x_pixel = int(landmark.x * frame.shape[1])
                    y_pixel = int(landmark.y * frame.shape[0])
                    cv2.circle( frame, (x_pixel, y_pixel), 1, (255, 255, 0), )
        else:
            face_count = 0

        if counter % 5 == 0 and recognition_enabled:
            small_frame = cv2.resize(frame, (0, 0), fx=0.75, fy=0.75)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

            face_locations = face_recognition.face_locations(rgb_small_frame)
            if face_locations:
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations, model="large")

                current_names = []
                last_face_locations = []

                for encoding, location in zip(face_encodings, face_locations):
                    name = "Unknown"
                    if known_face_encodings:
                        face_distances = face_recognition.face_distance(known_face_encodings, encoding)
                        best_idx = face_distances.argmin()
                        if face_distances[best_idx] < 0.65:
                            name = known_face_names[best_idx]

                    current_names.append(name)
                    scale = 1 / 0.75
                    t, r, b, l = location
                    last_face_locations.append((int(t * scale), int(r * scale), int(b * scale), int(l * scale)))

                current_identity = current_names[0] if current_names else "Scanning..."
            else:
                current_identity = "Scanning..."
                last_face_locations = []
                current_names = []
        for (t, r, b, l), name_label in zip(last_face_locations, current_names):
            if recognition_enabled:
                color = (0, 255, 0) if name_label != "Unknown" else (0, 0, 255)
                if t >= 0 and l >= 0 and b <= frame.shape[0] and r <= frame.shape[1]:
                    cv2.rectangle(frame, (l, t), (r, b), color, 2)
                cv2.putText(frame, name_label, (l, max(t - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        counter += 1

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start_camera')
def start_camera():
    global camera, start_time
    if camera is None:
        camera = cv2.VideoCapture(0)
        start_time = time.time()
    return "camera started"

@app.route('/stop_camera')
def stop_camera():
    global camera, current_identity, face_count, current_names, last_face_locations
    if camera is not None:
        camera.release()
        camera = None
    current_identity = ""
    face_count = 0
    current_names = []
    last_face_locations = []
    return "camera stopped"

@app.route('/toggle_recognition/<state>')
def toggle_recognition(state):
    global recognition_enabled, current_names, current_identity, last_face_locations
    recognition_enabled = state == "on"
    if not recognition_enabled:
        current_names = []
        last_face_locations = []
        current_identity = ""
    return "ok"

@app.route('/get_stats')
def get_stats():
    global face_count, start_time, fps, current_identity

    duration = "00:00"
    if start_time:
        elapsed = int(time.time() - start_time)
        mins, secs = divmod(elapsed, 60)
        duration = f"{mins:02d}:{secs:02d}"

    recognized_count = 1 if (current_identity and current_identity not in ("Scanning...", "Unknown")) else 0
    unknown_count = 1 if current_identity == "Unknown" else 0

    return {
        "face_found": face_count,
        "fps": round(fps, 1),
        "session_time": duration,
        "status": "ACTIVE" if camera is not None else "IDLE",
        "current_user": current_identity,
        "recognized": recognized_count,
        "unknown": unknown_count
    }

if __name__ == '__main__':
    app.run(debug=True)