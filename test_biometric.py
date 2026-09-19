import cv2
import numpy as np

from mediapipe_face import detect_and_crop_face
from arcface_model import get_embedding


def main():

    image_path = input("Enter the path of a face image: ").strip()

    # Read image using OpenCV
    image_bgr = cv2.imread(image_path)

    if image_bgr is None:
        print("ERROR: Could not read the image.")
        return

    print("\nImage loaded successfully.")
    print("Original image shape:", image_bgr.shape)

    # Convert BGR -> RGB
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

    # --------------------------------------------------
    # STEP 1: MediaPipe face detection
    # --------------------------------------------------

    print("\nRunning MediaPipe face detection...")

    face_crop, bbox = detect_and_crop_face(image_rgb)

    if face_crop is None:
        print("ERROR: No face detected.")
        return

    print("Face detected successfully.")
    print("Bounding box:", bbox)
    print("Face crop shape:", face_crop.shape)

    # Save cropped face so we can visually inspect it
    face_crop_bgr = cv2.cvtColor(face_crop, cv2.COLOR_RGB2BGR)
    cv2.imwrite("detected_face.jpg", face_crop_bgr)

    print("Cropped face saved as: detected_face.jpg")

    # --------------------------------------------------
    # STEP 2: ArcFace embedding
    # --------------------------------------------------

    print("\nGenerating ArcFace embedding...")

    embedding = get_embedding(face_crop)

    if embedding is None:
        print("ERROR: Could not generate embedding.")
        return

    print("ArcFace embedding generated successfully.")
    print("Embedding shape:", embedding.shape)
    print("Embedding dimension:", len(embedding))
    print("Embedding data type:", embedding.dtype)

    # --------------------------------------------------
    # STEP 3: Verify embedding
    # --------------------------------------------------

    print("\nEmbedding verification:")

    if len(embedding) == 512:
        print("✓ Embedding contains exactly 512 values.")
    else:
        print("✗ Embedding does NOT contain 512 values.")

    norm = np.linalg.norm(embedding)

    print("Embedding norm:", norm)

    # --------------------------------------------------
    # STEP 4: Display embedding
    # --------------------------------------------------

    print("\nFirst 10 embedding values:")

    for i in range(10):
        print(f"{i + 1}: {embedding[i]}")

    print("\nComplete 512-dimensional embedding:")
    print(embedding)

    print("\n======================================")
    print("BIOMETRIC PIPELINE TEST SUCCESSFUL")
    print("======================================")


if __name__ == "__main__":
    main()