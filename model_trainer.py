import cv2
import numpy as np
import os
from PIL import Image

# 1. Face Detector Initialization
# Load OpenCV's frontal face Haar Cascade locally
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

def capture_face_samples(numeric_id, num_samples=40, progress_callback=None):
    """
    Automated Face Capture Function
    Captures `num_samples` of faces for the given `numeric_id`.
    """
    dataset_dir = f"dataset/{numeric_id}"
    
    # Ensure directory exists: dataset/{numeric_id}/
    if not os.path.exists(dataset_dir):
        os.makedirs(dataset_dir)
        
    # Open webcam
    cap = cv2.VideoCapture(0)
    
    count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break
            
        # Convert frame to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect face
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(60, 60))
        
        for (x, y, w, h) in faces:
            count += 1
            
            # Crop bounding box, resize to (200, 200)
            face_crop = gray[y:y+h, x:x+w]
            face_resized = cv2.resize(face_crop, (200, 200))
            
            # Save as dataset/{numeric_id}/{count}.jpg
            cv2.imwrite(f"{dataset_dir}/{count}.jpg", face_resized)
            
            # Draw a green rectangle and text overlay showing progress
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, f"Capturing: {count}/{num_samples}", (x, y-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            # Trigger progress_callback(count, num_samples) if provided
            if progress_callback:
                progress_callback(count, num_samples)
                
            # Wait 100ms between captures to allow varied head angles
            cv2.waitKey(100)
            
        # Display feed in window 'Face Enrollment - Move head slightly'
        cv2.imshow('Face Enrollment - Move head slightly', frame)
        
        # Break when count >= num_samples or key 'q' is pressed
        if count >= num_samples:
            break
        
        # Also allow early exit if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release camera, destroy OpenCV window, and return True on success
    cap.release()
    cv2.destroyAllWindows()
    return True


def train_custom_model():
    """
    Local LBPH Training Function
    Reads all images from dataset/ and trains the LBPH Face Recognizer.
    """
    dataset_path = "dataset"
    faces = []
    labels = []
    
    # Iterate through all folders in dataset/
    if not os.path.exists(dataset_path):
        return (False, "Dataset folder does not exist.")
        
    user_folders = [f for f in os.listdir(dataset_path) if os.path.isdir(os.path.join(dataset_path, f))]
    
    for folder in user_folders:
        try:
            user_id = int(folder)
        except ValueError:
            continue # skip non-numeric folders
            
        folder_path = os.path.join(dataset_path, folder)
        image_files = [f for f in os.listdir(folder_path) if f.endswith('.jpg')]
        
        for image_name in image_files:
            image_path = os.path.join(folder_path, image_name)
            
            # Read each image, convert to uint8 NumPy array
            img_pil = Image.open(image_path).convert('L') # Convert to grayscale
            image_np = np.array(img_pil, 'uint8')
            
            # Append face arrays to faces and folder IDs to labels
            faces.append(image_np)
            labels.append(user_id)
            
    if len(faces) == 0:
        return (False, "No face samples found in dataset.")
        
    # Initialize recognizer
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    
    # Train model
    recognizer.train(faces, np.array(labels))
    
    # Ensure models/ directory exists and save to models/trained_model.yml
    if not os.path.exists("models"):
        os.makedirs("models")
        
    recognizer.save("models/trained_model.yml")
    
    return (True, f"Model trained on {len(faces)} face samples across {len(set(labels))} users.")

# Self-Test Block
if __name__ == '__main__':
    print("model_trainer.py loaded successfully. Ready for Data Collection and Training.")
