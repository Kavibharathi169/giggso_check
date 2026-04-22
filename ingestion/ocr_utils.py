import logging
import os
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)

# Try to initialize EasyOCR purely to avoid Tesseract Windows PATH issues       
_reader = None

def get_easyocr_reader():
    global _reader
    if _reader is None:
        try:
            import easyocr
            # Load the model into memory once. using cpu to avoid heavy GPU driver issues for local users
            logger.info("Loading EasyOCR model into memory (first time might take a moment to download)...")
            _reader = easyocr.Reader(['en'], gpu=False)
        except ImportError:
            logger.warning("EasyOCR not installed. OCR might fail or rely on pytesseract fallback.")
    return _reader


def _preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """
    Applies image processing techniques to substantially increase OCR accuracy.
    Includes resolution upscaling, grayscale conversion, and contrast enhancement.
    """
    # 1. Upscale resolution (2x) - gives algorithms more pixels per character
    width, height = image.size
    image = image.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
    
    # 2. Convert to grayscale to remove color noise/artifacts
    image = image.convert('L')
    
    # 3. Aggressively enhance contrast to make text "pop" against the background
    contrast_enhancer = ImageEnhance.Contrast(image)
    image = contrast_enhancer.enhance(2.0)
    
    # 4. Apply sharpening filter to crisp up fuzzy edges of letters
    image = image.filter(ImageFilter.SHARPEN)
    
    # Convert back to RGB because some OCR engines strictly expect 3 channels
    return image.convert('RGB')


def extract_text_from_image(image_obj_or_path) -> str:
    """
    Takes either a string file path to an image or a PIL.Image object.
    Runs Optical Character Recognition (OCR) and returns the extracted text.    
    """
    try:
        # Load the image
        if isinstance(image_obj_or_path, str):
            image = Image.open(image_obj_or_path)
        else:
            image = image_obj_or_path

        # Apply Advanced Image Pre-processing for higher OCR accuracy
        enhanced_image = _preprocess_image_for_ocr(image)

        # Method 1: Try EasyOCR first (Reliable on Windows without external Exe)
        reader = get_easyocr_reader()
        if reader is not None:
            img_np = np.array(enhanced_image)
            # Adjust contrast threshold internally in EasyOCR
            result = reader.readtext(
                img_np, 
                detail=0, 
                paragraph=True,
                contrast_ths=0.1,  # Lower threshold for better text detection in low contrast
                adjust_contrast=0.5 # Tell EasyOCR to internally adjust contrast
            )
            text = "\n".join(result)
            if text.strip():
                return text

        # Method 2: Fallback to PyTesseract
        import pytesseract
        # Using PSM 3 (Fully automatic page segmentation)
        config = r'--oem 3 --psm 3'
        text = pytesseract.image_to_string(enhanced_image, config=config)
        return text

    except Exception as e:
        logger.error(f"OCR failed for image: {e}")
        return ""
