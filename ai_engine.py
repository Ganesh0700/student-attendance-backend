import os
import cv2
import uuid
import numpy as np
from deepface import DeepFace

# Temp folder setup
TEMP_DIR = "temp_processing"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)


def get_face_embedding(image_data):
    """
    Robust embedding generation:
    1. Uses UUID temp files to avoid file-lock conflicts.
    2. Tries 3 image orientations for mobile portrait inputs.
    3. Falls back to non-strict detection for difficult webcam frames.
    """
    unique_filename = f"scan_{uuid.uuid4().hex}.jpg"
    temp_path = os.path.join(TEMP_DIR, unique_filename)

    try:
        cv2.imwrite(temp_path, image_data)

        attempts = [
            ("normal", image_data),
            ("rotate_90", cv2.rotate(image_data, cv2.ROTATE_90_CLOCKWISE)),
            ("rotate_-90", cv2.rotate(image_data, cv2.ROTATE_90_COUNTERCLOCKWISE)),
        ]

        # Strict pass
        for angle_name, img_variant in attempts:
            cv2.imwrite(temp_path, img_variant)
            try:
                embedding_objs = DeepFace.represent(
                    img_path=temp_path,
                    model_name="Facenet",
                    detector_backend="opencv",
                    enforce_detection=True,
                )
                print(f"AI: strict face detected at angle={angle_name}")
                return embedding_objs[0]["embedding"]
            except ValueError:
                continue

        # Fallback pass
        for angle_name, img_variant in attempts:
            cv2.imwrite(temp_path, img_variant)
            try:
                embedding_objs = DeepFace.represent(
                    img_path=temp_path,
                    model_name="Facenet",
                    detector_backend="opencv",
                    enforce_detection=False,
                )
                if embedding_objs and embedding_objs[0].get("embedding"):
                    print(f"AI: fallback embedding used at angle={angle_name}")
                    return embedding_objs[0]["embedding"]
            except Exception:
                continue

        print("AI: face not detected in any angle")
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


def verify_match(known_embeddings, live_embedding, threshold=0.50):
    """Matches using cosine distance"""
    if not known_embeddings or not live_embedding:
        return False, -1

    live_vec = np.array(live_embedding)
    best_score = 1.0
    best_index = -1

    for i, known_vec in enumerate(known_embeddings):
        known_vec = np.array(known_vec)
        a = np.matmul(known_vec, live_vec)
        b = np.linalg.norm(known_vec) * np.linalg.norm(live_vec)
        distance = 1 - (a / b)

        if distance < best_score:
            best_score = distance
            best_index = i

    print(f"Match score: {best_score:.4f} (threshold: {threshold})")
    if best_score < threshold:
        return True, best_index

    return False, -1
