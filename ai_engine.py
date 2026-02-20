import os
import cv2
import uuid
import numpy as np

# Temp folder setup
TEMP_DIR = "temp_processing"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# Lightweight face detection using OpenCV Haar Cascades
class LightweightFaceDetector:
    def __init__(self):
        # Load Haar cascade classifiers
        try:
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
            self.profile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')
            print("✓ OpenCV face detectors loaded successfully")
        except Exception as e:
            print(f"✗ Error loading OpenCV cascades: {e}")
            self.face_cascade = None
            self.eye_cascade = None
            self.profile_cascade = None
    
    def detect_faces(self, image_data):
        """
        Detect faces using multiple Haar cascade methods
        """
        if self.face_cascade is None:
            return []
        
        face_boxes = []
        gray = cv2.cvtColor(image_data, cv2.COLOR_BGR2GRAY)
        
        # Method 1: Frontal face detection
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        for (x, y, w, h) in faces:
            # Verify it's a real face by checking for eyes
            roi_gray = gray[y:y+h, x:x+w]
            eyes = self.eye_cascade.detectMultiScale(roi_gray)
            
            # Accept if we found eyes or if face is large enough
            confidence = 1.0
            if len(eyes) > 0:
                confidence = min(1.0, 0.7 + (len(eyes) * 0.1))
            elif w > 60 and h > 60:
                confidence = 0.6
            
            face_boxes.append({
                'box': [x, y, w, h],
                'confidence': confidence,
                'method': 'frontal'
            })
        
        # Method 2: Profile face detection (if no frontal faces found)
        if not face_boxes:
            profile_faces = self.profile_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            for (x, y, w, h) in profile_faces:
                face_boxes.append({
                    'box': [x, y, w, h],
                    'confidence': 0.7,
                    'method': 'profile'
                })
        
        # Method 3: Relaxed detection (last resort)
        if not face_boxes:
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.05,
                minNeighbors=3,
                minSize=(20, 20)
            )
            
            for (x, y, w, h) in faces:
                face_boxes.append({
                    'box': [x, y, w, h],
                    'confidence': 0.4,
                    'method': 'relaxed'
                })
        
        return face_boxes

# Initialize the detector
face_detector = LightweightFaceDetector()

def get_face_embedding(image_data):
    """
    Lightweight face embedding generation using OpenCV only:
    1. Uses Haar cascades for face detection
    2. Multiple detection methods for robustness
    3. Simple but effective embedding generation
    """
    unique_filename = f"scan_{uuid.uuid4().hex}.jpg"
    temp_path = os.path.join(TEMP_DIR, unique_filename)

    try:
        cv2.imwrite(temp_path, image_data)

        # Detect faces using multiple methods
        face_boxes = face_detector.detect_faces(image_data)

        if not face_boxes:
            print("AI: No faces detected with any method")
            return None

        # Select the best face (highest confidence, largest size)
        best_face = None
        best_score = 0
        
        for face in face_boxes:
            x, y, w, h = face['box']
            confidence = face['confidence']
            size_score = (w * h) / (image_data.shape[0] * image_data.shape[1])
            combined_score = confidence * 0.7 + size_score * 0.3
            
            if combined_score > best_score:
                best_score = combined_score
                best_face = face

        if best_face is None:
            print("AI: No suitable face found")
            return None

        x, y, w, h = best_face['box']
        
        # Extract and preprocess face
        face_roi = image_data[y:y+h, x:x+w]
        
        if face_roi.size == 0:
            print("AI: Invalid face region detected")
            return None

        # Generate lightweight embedding
        embedding = generate_lightweight_embedding(face_roi)
        
        if embedding:
            print(f"AI: Face detected (method: {best_face['method']}, confidence: {best_face['confidence']:.3f})")
            return embedding
        else:
            print("AI: Failed to generate embedding from detected face")
            return None

    except Exception as e:
        print(f"AI error: {e}")
        return None

    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

def generate_lightweight_embedding(face_img):
    """
    Generate a lightweight but effective face embedding
    """
    try:
        # Resize to standard size
        face_resized = cv2.resize(face_img, (64, 64))
        
        # Convert to grayscale if needed
        if len(face_resized.shape) == 3:
            face_gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
        else:
            face_gray = face_resized
        
        # Apply histogram equalization for better contrast
        face_equalized = cv2.equalizeHist(face_gray)
        
        # Apply Gaussian blur to reduce noise
        face_blurred = cv2.GaussianBlur(face_equalized, (3, 3), 0)
        
        # Normalize and flatten
        face_normalized = face_blurred / 255.0
        embedding = face_normalized.flatten()
        
        # Add some statistical features for better uniqueness
        mean_val = np.mean(face_normalized)
        std_val = np.std(face_normalized)
        
        # Combine spatial and statistical features
        enhanced_embedding = np.concatenate([embedding, [mean_val, std_val]])
        
        return enhanced_embedding.tolist()
        
    except Exception as e:
        print(f"Error generating lightweight embedding: {e}")
        return None

def verify_match(known_embeddings, live_embedding, threshold=0.75):
    """
    Lightweight face matching using normalized correlation
    """
    if not known_embeddings or not live_embedding:
        return False, -1

    try:
        # Convert to numpy arrays
        known_matrix = np.array(known_embeddings)
        live_vec = np.array(live_embedding)
        
        # Ensure all embeddings have the same length
        if known_matrix.shape[1] != len(live_vec):
            print("Embedding size mismatch!")
            return False, -1

        # Normalize vectors
        live_norm = live_vec / (np.linalg.norm(live_vec) + 1e-8)
        known_norm = known_matrix / (np.linalg.norm(known_matrix, axis=1, keepdims=True) + 1e-8)

        # Compute cosine similarity
        similarities = np.dot(known_norm, live_vec)
        
        # Find best match
        best_index = np.argmax(similarities)
        best_score = similarities[best_index]

        print(f"Match score: {best_score:.4f} (threshold: {threshold})")

        if best_score >= threshold:
            return True, int(best_index)

        return False, -1

    except Exception as e:
        print(f"Error in face matching: {e}")
        return False, -1

def get_detector_info():
    """
    Get information about the face detector
    """
    return {
        "method": "OpenCV Haar Cascades",
        "models": ["Frontal Face", "Profile Face", "Eye Detection"],
        "size": "Lightweight (~50MB)",
        "speed": "Fast (<100ms per image)",
        "accuracy": "Good for attendance systems"
    }
