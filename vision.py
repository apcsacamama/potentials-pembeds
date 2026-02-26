import cv2
import face_recognition
import requests
import time
import os
import numpy as np  
import serial

PHP_BACKEND_URL = "http://localhost/facs/log_access.php" 
AUTHORIZED_FACES_DIR = "authorized_faces"

try:
    print("Connecting to Arduino...")
    arduino = serial.Serial('COM4', 9600, timeout=1)
    time.sleep(2)
    print("Arduino Connected successfully!")
except Exception as e:
    print(f"Warning: Could not connect to Arduino. Is it plugged in?: {e}")
    arduino = None

known_face_encodings = []
known_face_names = []

print("Loading authorized faces...")
for filename in os.listdir(AUTHORIZED_FACES_DIR):
    if filename.endswith(".jpg") or filename.endswith(".png"):
        image_path = os.path.join(AUTHORIZED_FACES_DIR, filename)
        image = face_recognition.load_image_file(image_path)
        
        # <-- THE FIX: Grab all faces found in the image safely -->
        encodings = face_recognition.face_encodings(image)
        
        # Check if it actually found at least one face!
        if len(encodings) > 0:
            encoding = encodings[0] # Grab the first face safely
            known_face_encodings.append(encoding)
            # Use filename without extension as the person's name
            known_face_names.append(os.path.splitext(filename)[0].capitalize())
        else:
            # If no face is found, just print a warning and keep going without crashing
            print(f"  -> ⚠️ WARNING: No clear face found in '{filename}'. Skipping this profile!")

print(f"Loaded {len(known_face_names)} authorized profiles: {known_face_names}")

# Initialize Webcam (0 is usually the built-in or default USB webcam)
cap = cv2.VideoCapture(0)

# Cooldown to prevent spamming the database/Arduino every single frame
last_log_time = 0
cooldown_seconds = 5 

print("Starting video stream... Press 'q' to quit.")

while True:
    # 1. Input: Capture frame-by-frame
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    # Resize frame to 1/4 size for faster processing
    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
    
    # Force the memory into a contiguous C-block so dlib cannot reject it
    rgb_small_frame = np.ascontiguousarray(small_frame[:, :, ::-1])

    # 2. Processing: Find faces and encode them
    face_locations = face_recognition.face_locations(rgb_small_frame)
    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

    for face_encoding, face_location in zip(face_encodings, face_locations):
        # Compare against pre-approved database
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        name = "Intruder"

        if True in matches:
            first_match_index = matches.index(True)
            name = known_face_names[first_match_index]

            # 3. AI Decision: Match Found
            current_time = time.time()
            if current_time - last_log_time > cooldown_seconds:
                print(f"\n[MATCH FOUND] User: {name}")
                
                # Send the physical unlock signal to Arduino!
                if arduino:
                    print(">> ACTION: Sending signal '1' to Arduino via Serial to UNLOCK!")
                    arduino.write(b'1') 
                else:
                    print(">> ACTION: Sending signal '1' to Arduino (Simulated - Board not connected)")
                
                # Send POST request to PHP/MySQL dashboard
                try:
                    payload = {"user": name, "status": "Authorized"}
                    response = requests.post(PHP_BACKEND_URL, data=payload) 
                    print(f">> ACTION: POST log to MySQL via PHP -> {payload}")
                except Exception as e:
                    print(f"Database logging failed: {e}")
                
                last_log_time = current_time

        else:
            # 3. AI Decision: No Match
            current_time = time.time()
            if current_time - last_log_time > cooldown_seconds:
                print("\n[ALERT] System flagged an Intruder!")
                print(">> ACTION: Logging Failed Attempt")
                
                # Send POST request to PHP/MySQL dashboard for Intruders
                try:
                    payload = {"user": "Unknown", "status": "Intruder"}
                    response = requests.post(PHP_BACKEND_URL, data=payload) 
                    print(f">> ACTION: POST log to MySQL via PHP -> {payload}")
                except Exception as e:
                    print(f"Database logging failed: {e}")
                    
                last_log_time = current_time

        # Draw a box around the face for visual feedback
        top, right, bottom, left = [coord * 4 for coord in face_location] # Scale back up
        color = (0, 255, 0) if name != "Intruder" else (0, 0, 255)
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        cv2.putText(frame, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255), 1)

    # Show the resulting image
    cv2.imshow('F.A.C.S. Live Feed', frame)

    # Hit 'q' on the keyboard to quit!
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Clean up
if arduino:
    arduino.close() # Safely close the USB connection
cap.release()
cv2.destroyAllWindows()