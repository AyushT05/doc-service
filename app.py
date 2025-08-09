from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from pptx import Presentation
from PIL import Image
import pytesseract
from io import BytesIO
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import logging
import subprocess
import tempfile

# Setup logging
logger = logging.getLogger("uvicorn.error")

# Configure Tesseract for Windows (optional, skip on Linux/Colab)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

app = FastAPI()

# ------------------------- PPTX Extraction Logic ------------------------- #

def extract_text_from_shape(shape):
    text = ''
    if hasattr(shape, 'text_frame') and shape.text_frame:
        for paragraph in shape.text_frame.paragraphs:
            for run in paragraph.runs:
                text += run.text
            text += '\n'
    elif shape.shape_type == 6:  # Group Shape
        for subshape in shape.shapes:
            text += extract_text_from_shape(subshape)
    elif shape.has_table:
        for row in shape.table.rows:
            for cell in row.cells:
                text += cell.text + '\t'
            text += '\n'
    return text

def extract_text_and_ocr_from_pptx(file_bytes):
    prs = Presentation(BytesIO(file_bytes))
    slide_texts = []

    for i, slide in enumerate(prs.slides, start=1):
        slide_text = f"Slide {i}:\n"
        for shape in slide.shapes:
            if shape.has_text_frame or shape.has_table or shape.shape_type == 6:
                slide_text += extract_text_from_shape(shape)

            if shape.shape_type == 13:  # Picture
                image = shape.image
                img_bytes = image.blob
                img = Image.open(BytesIO(img_bytes))
                ocr_text = pytesseract.image_to_string(img)
                slide_text += "[OCR]: " + ocr_text + '\n'
        slide_texts.append(slide_text.strip())

    return "\n\n---\n\n".join(slide_texts)

@app.post("/extract-pptx/")
async def extract_pptx(request: Request):
    try:
        data = await request.json()
        document_url = data.get("documentUrl")
        logger.info(f"PPTX URL received: {document_url}")

        if not document_url or not urlparse(document_url).path.lower().endswith(".pptx"):
            return PlainTextResponse("Only .pptx files are supported", status_code=400)

        response = requests.get(document_url, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code != 200:
            return PlainTextResponse("Failed to download file", status_code=400)

        content = extract_text_and_ocr_from_pptx(response.content)
        return PlainTextResponse(content, status_code=200)

    except Exception as e:
        logger.exception("Error during PPTX processing:")
        return PlainTextResponse(f"Processing error: {str(e)}", status_code=500)

# ------------------------- Web Page Scraping Logic ------------------------- #

def fetch_and_clean_content(url):
    try:
        logger.info(f"Scraping URL: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup(["script", "style"]):
            script.extract()

        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        cleaned_text = '\n'.join(chunk for chunk in chunks if chunk)

        return cleaned_text
    except requests.exceptions.RequestException as e:
        logger.error(f"Scraping error: {e}")
        return None

@app.post("/extract-url/")
async def extract_webpage_text(request: Request):
    try:
        data = await request.json()
        url = data.get("url")

        if not url:
            return JSONResponse({"error": "Missing 'url' in request body"}, status_code=400)

        content = fetch_and_clean_content(url)

        if content:
            return JSONResponse({"url": url, "content": content}, status_code=200)
        else:
            return JSONResponse({"error": "Failed to retrieve content"}, status_code=500)

    except Exception as e:
        logger.exception("Error during URL scraping:")
        return JSONResponse({"error": str(e)}, status_code=500)
