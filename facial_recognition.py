from flask import Flask, render_template, Response, jsonify
import cv2
import sqlite3
import smtplib
from email.mime.text import MIMEText
import numpy as np
from collections import deque
import face_recognition
from sklearn.cluster import KMeans

app = Flask(__name__)

#Initialize the camera and face detection model
camera = cv2.VideoCapture(0)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eyes_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

MAX_OCCUPANCY = 500
current_occupancy = 0
face_encodings_list = deque(maxlen=100)

#Email settings for alert notifications
EMAIL_SENDER = "your_email@example.com"
EMAIL_RECEIVER = "store_owner@example.com"
EMAIL_PASSWORD = "your_email_password"

#Initialize the SQLite database if it doesn't exist
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS occupancy (id INTEGER PRIMARY KEY, count INTEGER)''')
    cursor.execute('INSERT INTO occupancy (count) VALUES (0)')
    conn.commit()
    conn.close()

#Send an email alert if occupancy is exceeded
def send_alert_email():
    subject = "Occupancy Alert: Maximum Limit Reached"
    body = "The store has reached its maximum occupancy limit. Please take necessary action."
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        server.quit()
        print("Alert email sent successfully.")
    except Exception as e:
        print(f"Error sending email: {e}")

#Update the current occupancy in the database
def update_occupancy(count):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE occupancy SET count = ? WHERE id = 1', (count,))
    conn.commit()
    conn.close()

    if count >= MAX_OCCUPANCY:
        send_alert_email()

#Retrieve the current occupancy count from the database
def get_occupancy():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT count FROM occupancy WHERE id = 1')
    count = cursor.fetchone()[0]
    conn.close()
    return count

#Cluster faces to identify unique individuals
def cluster_faces(face_encodings):
    if len(face_encodings) >= 2:
        kmeans = KMeans(n_clusters=min(len(face_encodings), 5))
        kmeans.fit(face_encodings)
        return len(set(kmeans.labels_))
    return len(face_encodings)

#Capture video frames and detect unique faces in real-time
def generate_frames():
    global current_occupancy
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            
            for face_encoding in face_encodings:
                face_encodings_list.append(face_encoding)
            
            current_occupancy = cluster_faces(list(face_encodings_list))
            update_occupancy(current_occupancy)
            
            for (top, right, bottom, left) in face_locations:
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blurred, 50, 150)
            edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
            frame = cv2.addWeighted(frame, 0.7, edges_colored, 0.3, 0)
            
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

#Serve the homepage
@app.route('/')
def index():
    return render_template('index.html')

#Provide a video feed for real-time tracking
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

#API endpoint to fetch the current occupancy status
@app.route('/get_occupancy')
def get_occupancy_data():
    return jsonify({'occupancy': get_occupancy(), 'max_occupancy': MAX_OCCUPANCY})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
