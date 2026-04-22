import os
import datetime
import hashlib
import logging

from ingestion.ocr_utils import extract_text_from_image

logger = logging.getLogger(__name__)

def load_image(file_path: str, document_type: str, org_name: str) -> list[dict]:
    """
    Extracts text from a standalone image using OCR.
    """
    logger.info(f"Extracting standard Image (OCR) from: {file_path}")
    
    text = extract_text_from_image(file_path)
    
    if not text.strip():
        logger.warning(f"No text could be extracted from image via OCR: {file_path}")
        return []
        
    chunk_id = hashlib.sha256(f"{file_path}_{text[:50]}".encode('utf-8')).hexdigest()[:16]
    
    blocks = [{
        "chunk_id": chunk_id,
        "source_url": file_path,
        "document_title": os.path.basename(file_path),
        "organization": org_name,
        "section_title": "Image OCR Extraction",
        "section_level": "Document",
        "chapter": "",
        "article": "",
        "content_type": "image_ocr",
        "source_format": "image",
        "document_type": document_type,
        "text": text.strip(),
        "char_count": len(text),
        "extracted_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }]
    
    logger.info(f"Successfully processed {file_path} with OCR.")
    return blocks
