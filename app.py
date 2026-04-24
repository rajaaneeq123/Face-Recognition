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

for person_name in os.listdir("known_faces"):
    person_dir = os.path.join("known_faces", person_name)

    if os.path.isdir(person_dir):
        for image_filename in os.listdir(person_dir):
            image_path = os.path.join(person_dir, image_filename)

            # Load and encode the image
            image = face_recognition.load_image_file(image_path)
            encodings = face_recognition.face_encodings(image)

            if len(encodings) > 0:
                known_face_encodings.append(encodings[0])
                known_face_names.append(person_name)

print(f"Loaded {len(known_face_names)} images for {len(set(known_face_names))} people.")

if os.path.exists("known_faces"):
    for filename in os.listdir("known_faces"):
        if filename.endswith((".jpg", ".png")):
            encoding_image = face_recognition.load_image_file(f"known_faces/{filename}")
            face_encodings = face_recognition.face_encodings(encoding_image)
            if len(face_encodings) > 0:
                known_face_encodings.append(face_encodings[0])
                known_face_names.append(os.path.splitext(filename)[0].capitalize())

options = vision.FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path="face_landmarker.task"),
    running_mode=vision.RunningMode.VIDEO, # Optimized for continuous frames
    num_faces=1,
    min_face_detection_confidence=0.5,
    min_face_presence_confidence=0.5,
    min_tracking_confidence=0.5
)
detector = vision.FaceLandmarker.create_from_options(options)

camera = None
current_identity = "Scanning"
last_face_location = None
face_count = 0
start_time = None

def generate_frames():
    global camera, current_identity, face_count
    counter = 0
    while(True):
        if camera is None:
            break
        success, frame = camera.read()
        if not success:
            break
        else:
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            frame_timestamp_ms = int(time.time() * 1000)
            detection_result = detector.detect_for_video(mp_image, frame_timestamp_ms)

            if detection_result.face_landmarks:
                face_count = len(detection_result.face_landmarks)
                for face_landmarks in detection_result.face_landmarks:
                    for landmark in face_landmarks:
                        x_pixel = int(landmark.x * frame.shape[1])
                        y_pixel = int(landmark.y * frame.shape[0])

                        cv2.circle( img=frame, center=(x_pixel, y_pixel), radius=1, color=(255, 255, 0), )
            else:
                face_count = 0;

            if counter % 20 == 0:
                face_locations = face_recognition.face_locations(rgb_frame)
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

                current_identity = "Unknown"
                last_face_location = None

                for face_encoding in face_encodings:
                    matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                    if True in matches:
                        match_index = matches.index(True)
                        current_identity = known_face_names[match_index]

                    last_face_location = face_locations[0]

            counter += 1

            if last_face_location and current_identity != "Scanning...":
                t, r, b, l = last_face_location
                cv2.putText( frame, f"ID: {current_identity}", (l, t - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2 )

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
    global camera
    if camera is not None:
        camera.release()
        camera = None
    return "camera stopped"

@app.route('/get_stats')
def get_stats():
    global face_count, start_time

    duration = "00:00"
    if start_time:
        elapsed = int(time.time() - start_time)
        mins, secs = divmod(elapsed, 60)
        duration = f"{mins:02d}:{secs:02d}"

    return {"face_found": face_count, "session_time": duration, "status": "ACTIVE" if camera is not None else "IDLE", "current_user": current_identity }

if __name__ == '__main__':
    app.run(debug=True)
