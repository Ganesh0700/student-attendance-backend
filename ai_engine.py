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

        # 1. Fast Path: Strict detection on normal image
        try:
            embedding_objs = DeepFace.represent(
                img_path=temp_path,
                model_name="Facenet",
                detector_backend="opencv",
                enforce_detection=True,
            )
            return embedding_objs[0]["embedding"]
        except:
            pass # Continue to robust search

        # 2. Robust Path: Rotations
        attempts = [
            ("rotate_90", cv2.rotate(image_data, cv2.ROTATE_90_CLOCKWISE)),
            ("rotate_-90", cv2.rotate(image_data, cv2.ROTATE_90_COUNTERCLOCKWISE)),
        ]

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

        # 3. Last Resort: Fallback (Non-strict) on original image only
        # We avoid running fallback on rotations to save time/memory
        cv2.imwrite(temp_path, image_data)
        try:
            embedding_objs = DeepFace.represent(
                img_path=temp_path,
                model_name="Facenet",
                detector_backend="opencv",
                enforce_detection=False,
            )
            if embedding_objs and embedding_objs[0].get("embedding"):
                print(f"AI: fallback embedding used at angle=normal")
                return embedding_objs[0]["embedding"]
        except Exception:
            pass

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
    """
    Matches using vectorized cosine distance for O(1) complexity relative to loop overhead.
    """
    if not known_embeddings or not live_embedding:
        return False, -1

    # Convert to numpy arrays for vectorization
    # known_matrix shape: (N, D)
    # live_vec shape: (D,)
    known_matrix = np.array(known_embeddings)
    live_vec = np.array(live_embedding)

    # Compute Norms
    # axis=1 computes norm for each row (student)
    norm_known = np.linalg.norm(known_matrix, axis=1)
    norm_live = np.linalg.norm(live_vec)

    # Avoid division by zero
    if norm_live == 0 or np.any(norm_known == 0):
        return False, -1

    # Dot Product: (N, D) dot (D,) -> (N,)
    dot_products = np.dot(known_matrix, live_vec)

    # Cosine Similarity: (N,)
    similarities = dot_products / (norm_known * norm_live)

    # Cosine Distance: (N,)
    distances = 1 - similarities

    # Find best match
    best_index = np.argmin(distances)
    best_score = distances[best_index]

    print(f"Match score: {best_score:.4f} (threshold: {threshold})")

    if best_score < threshold:
        return True, int(best_index)

    return False, -1
