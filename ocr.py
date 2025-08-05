# ocr.py
import easyocr
import numpy as np
from io import BytesIO
from PIL import Image, ImageEnhance

# Initialize EasyOCR reader for English language
reader = easyocr.Reader(['en'], gpu=False)

def preprocess_image_pil(content: bytes) -> np.ndarray:
    """
    Preprocess the input image bytes: convert to grayscale, enhance contrast, and binarize.
    Returns the processed image as a numpy array.
    """
    # Open image and convert to grayscale
    image = Image.open(BytesIO(content)).convert('L')

    # 1. Increase contrast
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2)  # Try factors 1.5–3 as needed

    # 2. Binarize (black and white)
    threshold = 128
    image = image.point(lambda p: 255 if p > threshold else 0)

    # Convert to array for EasyOCR
    return np.array(image)

def extract_text_from_image(content: bytes) -> str:
    """
    Receives image bytes, preprocesses, and extracts text using EasyOCR.
    """
    processed_img = preprocess_image_pil(content)
    
    # Restrict OCR to numbers and math symbols for better accuracy
    result = reader.readtext(processed_img, allowlist='0123456789+-=')
    return ' '.join([text for (_, text, _) in result])
