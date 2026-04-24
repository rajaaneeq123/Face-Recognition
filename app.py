import cv2
import time
from flask import Flask, render_template, Response
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python import BaseOptions

app = Flask(__name__)

model_path = "face_landmarker.task"

options = vision.FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=model_path),
    running_mode=vision.RunningMode.VIDEO, # Optimized for continuous frames
    num_faces=1,
    min_face_detection_confidence=0.5,
    min_face_presence_confidence=0.5,
    min_tracking_confidence=0.5
)
detector = vision.FaceLandmarker.create_from_options(options)

camera = None

def generate_frames():
    global camera
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
                for face_landmarks in detection_result.face_landmarks:
                    for landmark in face_landmarks:
                        # MediaPipe gives 'normalized' coordinates (0.0 to 1.0)
                        # We multiply by frame width/height to get actual pixel positions
                        x_pixel = int(landmark.x * frame.shape[1])
                        y_pixel = int(landmark.y * frame.shape[0])

                        # Draw a tiny cyan circle at every landmark point
                        cv2.circle(
                            img=frame,
                            center=(x_pixel, y_pixel),
                            radius=1,
                            color=(255, 255, 0),  # Cyan/Yellow-ish
                            thickness=-1
                        )

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
    global camera
    if camera is None:
        camera = cv2.VideoCapture(0)
    return "camera started"

@app.route('/stop_camera')
def stop_camera():
    global camera
    if camera is not None:
        camera.release()
        camera = None
    return "camera stopped"

if __name__ == '__main__':
    app.run()
