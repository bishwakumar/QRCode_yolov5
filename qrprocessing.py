import os
from pdf2image import convert_from_path
import shutil
import csv
from pathlib import Path
import subprocess

from pyzbar.pyzbar import decode
from PIL import Image
import jwt

# ============ CONFIG ============

# Folder containing images and PDFs
SOURCE_FOLDER = "test_images/"
# Your YOLOv5 trained weights
YOLO_WEIGHTS = "runs/train/exp19/weights/best.pt"
# Confidence threshold for detection
CONF_THRESHOLD = 0.25
# CSV output file for decoded results
CSV_OUTPUT_PATH = "decoded_qrcodes.csv"

# =================================

def convert_pdfs_to_jpg(folder):
    """
    Converts all PDFs in the folder to JPG images, saved in the same folder.
    """
    for filename in os.listdir(folder):
        path = os.path.join(folder, filename)
        if filename.lower().endswith(".pdf"):
            pages = convert_from_path(path, dpi=300)
            for i, page in enumerate(pages):
                new_filename = f"{filename}_page_{i+1}.jpg"
                img_path = os.path.join(folder, new_filename)
                page.save(img_path, "JPEG")
                print(f"Saved PDF page: {img_path}")

def run_yolov5_detect(source_folder, weights_path, conf_threshold):
    """
    Runs YOLOv5 detect.py on all images in the specified folder.
    """
    command = [
        "python",
        "detect.py",
        "--weights", weights_path,
        "--source", source_folder,
        "--conf", str(conf_threshold),
        "--save-crop",
        "--project", "runs/detect",
        "--name", "qr_detect_results",
        "--exist-ok",
    ]
    print("Running YOLOv5 detection...")
    subprocess.run(command, check=True)

def decode_qr_codes_from_folder(crops_folder, output_csv):
    """
    Reads all cropped images from YOLO output and decodes QR codes.
    Saves decoded data into a CSV.
    If the QR data is a JWT, also decodes and stores the payload.
    """
    crops_path = Path(crops_folder)
    result_rows = []

    if not crops_path.exists():
        print(f"No crops folder found at {crops_folder}. Nothing to decode.")
        return

    for img_file in crops_path.rglob("*.jpg"):
        try:
            img = Image.open(img_file)
            decoded_objects = decode(img)
            if decoded_objects:
                for obj in decoded_objects:
                    data = obj.data.decode("utf-8")
                    jwt_payload = ""
                    # Try to decode as JWT (without verification)
                    try:
                        jwt_payload = jwt.decode(data, options={"verify_signature": False})
                    except Exception:
                        jwt_payload = ""
                    result_rows.append({
                        "image_file": str(img_file),
                        "qr_data": data,
                        "jwt_payload": jwt_payload if jwt_payload else ""
                    })
                    print(f"Decoded from {img_file}: {data}")
            else:
                print(f"No QR code detected in cropped image: {img_file}")
        except Exception as e:
            print(f"Error decoding {img_file}: {e}")

    # Save CSV
    if result_rows:
        with open(output_csv, mode="w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=["image_file", "qr_data", "jwt_payload"])
            writer.writeheader()
            for row in result_rows:
                writer.writerow(row)
        print(f"Decoded results saved to {output_csv}")
    else:
        print("No QR codes decoded. CSV not created.")

def main():
    # Step 1: Convert PDFs to JPGs
    convert_pdfs_to_jpg(SOURCE_FOLDER)

    # Step 2: Run YOLOv5 detection
    run_yolov5_detect(
        source_folder=SOURCE_FOLDER,
        weights_path=YOLO_WEIGHTS,
        conf_threshold=CONF_THRESHOLD,
    )

    # Step 3: Decode QR codes from YOLO crops
    crops_dir = "runs/detect/qr_detect_results/crops/QRCode"
    decode_qr_codes_from_folder(
        crops_folder=crops_dir,
        output_csv=CSV_OUTPUT_PATH,
    )

if __name__ == "__main__":
    main()
