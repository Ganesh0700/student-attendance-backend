#!/usr/bin/env python3
"""
Test script for YOLOv8 face detection implementation
"""
import cv2
import numpy as np
from ai_engine import get_face_embedding, verify_match, download_yolov8_model

def test_yolov8_implementation():
    print("Testing YOLOv8 Face Detection Implementation...")
    
    # Test 1: Check if YOLOv8 model loads
    print("\n1. Testing YOLOv8 model loading...")
    try:
        model = download_yolov8_model()
        if model:
            print("✓ YOLOv8 model loaded successfully")
        else:
            print("✗ YOLOv8 model failed to load")
    except Exception as e:
        print(f"✗ Error loading YOLOv8: {e}")
    
    # Test 2: Test face embedding generation with a dummy image
    print("\n2. Testing face embedding generation...")
    try:
        # Create a dummy test image (100x100 RGB)
        test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        embedding = get_face_embedding(test_image)
        if embedding:
            print(f"✓ Face embedding generated successfully (length: {len(embedding)})")
        else:
            print("✗ Failed to generate face embedding")
    except Exception as e:
        print(f"✗ Error generating embedding: {e}")
    
    # Test 3: Test face matching
    print("\n3. Testing face matching...")
    try:
        # Create dummy embeddings
        embedding1 = np.random.rand(4096).tolist()  # 64x64 = 4096
        embedding2 = np.random.rand(4096).tolist()
        
        # Test with same embedding (should match)
        is_match, index = verify_match([embedding1], embedding1, threshold=0.5)
        if is_match:
            print("✓ Face matching works (identical embeddings)")
        else:
            print("✗ Face matching failed for identical embeddings")
        
        # Test with different embeddings (should not match)
        is_match, index = verify_match([embedding1], embedding2, threshold=0.9)
        if not is_match:
            print("✓ Face matching correctly rejects different embeddings")
        else:
            print("✗ Face matching incorrectly matched different embeddings")
            
    except Exception as e:
        print(f"✗ Error in face matching: {e}")
    
    print("\n" + "="*50)
    print("YOLOv8 Implementation Test Complete!")
    print("="*50)

if __name__ == "__main__":
    test_yolov8_implementation()
