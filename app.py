from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from pptx import Presentation
from PIL import Image
import pytesseract
from io import BytesIO

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

app = FastAPI()

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

            if shape.shape_type == 13:
                image = shape.image
                img_bytes = image.blob
                img = Image.open(BytesIO(img_bytes))
                ocr_text = pytesseract.image_to_string(img)
                slide_text += "[OCR]: " + ocr_text + '\n'
        slide_texts.append(slide_text.strip())

    return "\n\n---\n\n".join(slide_texts)

@app.post("/extract-pptx/")
async def extract_pptx(file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        extracted_text = extract_text_and_ocr_from_pptx(file_bytes)
        return JSONResponse(content={"extractedText": extracted_text})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
