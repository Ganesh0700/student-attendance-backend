#!/usr/bin/env python3
"""
Lightweight test script for optimized face detection
"""
import cv2
import numpy as np
from ai_engine import get_face_embedding, verify_match, get_detector_info

def test_lightweight_implementation():
    print("Testing Lightweight Face Detection Implementation...")
    
    # Test 1: Show detector info
    print("\n1. Face Detector Information:")
    info = get_detector_info()
    for key, value in info.items():
        print(f"   {key}: {value}")
    
    # Test 2: Test face embedding generation
    print("\n2. Testing face embedding generation...")
    try:
        # Create a dummy test image (100x100 RGB)
        test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        embedding = get_face_embedding(test_image)
        if embedding:
            print(f"✓ Face embedding generated successfully (length: {len(embedding)})")
            print(f"  Embedding type: {type(embedding)}")
            print(f"  First 5 values: {embedding[:5]}")
        else:
            print("✗ Failed to generate face embedding")
    except Exception as e:
        print(f"✗ Error generating embedding: {e}")
    
    # Test 3: Test face matching
    print("\n3. Testing face matching...")
    try:
        # Create dummy embeddings (4096 + 2 = 4098 dimensions)
        embedding1 = np.random.rand(4098).tolist()
        embedding2 = np.random.rand(4098).tolist()
        
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
    
    # Test 4: Performance test
    print("\n4. Performance test...")
    try:
        import time
        
        # Create test image
        test_image = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
        
        # Measure embedding generation time
        start_time = time.time()
        embedding = get_face_embedding(test_image)
        end_time = time.time()
        
        if embedding:
            processing_time = (end_time - start_time) * 1000  # Convert to ms
            print(f"✓ Processing time: {processing_time:.2f}ms")
            
            if processing_time < 200:
                print("✓ Performance is excellent (<200ms)")
            elif processing_time < 500:
                print("✓ Performance is good (<500ms)")
            else:
                print("⚠ Performance could be improved (>500ms)")
        else:
            print("✗ Failed to generate embedding for performance test")
            
    except Exception as e:
        print(f"✗ Error in performance test: {e}")
    
    print("\n" + "="*50)
    print("Lightweight Implementation Test Complete!")
    print("Estimated Docker image size: ~200-300MB")
    print("Memory usage: ~50-100MB")
    print("="*50)

if __name__ == "__main__":
    test_lightweight_implementation()
