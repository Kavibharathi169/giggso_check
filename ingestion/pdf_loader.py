import hashlib
import logging
import json
import os
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")

def _generate_chunk_id(file_path: str, page_num: int) -> str:
    return hashlib.sha256(
        (file_path + str(page_num)).encode("utf-8")
    ).hexdigest()[:16]

def _save_blocks(blocks: list[dict]) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "scraped.jsonl")
    try:
        with open(output_path, "a", encoding="utf-8") as f:
            for block in blocks:
                f.write(json.dumps(block, ensure_ascii=False) + "\n")
        logger.info(f"Saved {len(blocks)} blocks to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save blocks: {e}")

def load_pdf(
    file_path    : str,
    document_type: str,
    org_name     : str
) -> list[dict]:
    logger.info(f"Loading PDF efficiently using PyMuPDF: {file_path}")

    if not os.path.exists(file_path):
        logger.error(f"PDF file not found: {file_path}")
        return []

    import fitz  # PyMuPDF
    import io
    from PIL import Image

    try:
        pdf_document = fitz.open(file_path)
    except Exception as e:
        logger.error(f"Failed to open PDF {file_path}: {e}")
        return []

    document_title = os.path.basename(file_path)
    extracted_at   = datetime.now(timezone.utc).isoformat()
    blocks         = []

    for page_idx in range(len(pdf_document)):
        page_num = page_idx + 1
        try:
            page = pdf_document[page_idx]
            text = page.get_text("text")

            # Fallback for Scanned PDF images
            if not text or len(text.strip()) < 50:
                logger.info(f"Page {page_num} in {file_path} appears image-based. Engaging OCR pipeline...")
                from ingestion.ocr_utils import extract_text_from_image
                try:
                    # Convert fitz page to PIL image
                    pix = page.get_pixmap(dpi=300)
                    img_data = pix.tobytes("png")
                    pil_img = Image.open(io.BytesIO(img_data))
                    
                    ocr_text = extract_text_from_image(pil_img)
                    if ocr_text.strip():
                        text = (text or "") + "\n" + ocr_text 
                except Exception as ocr_e:
                    logger.warning(f"OCR failed for page {page_num}: {ocr_e}")

            text = text.strip() if text else ""
            if not text:
                continue

            chunk_id = _generate_chunk_id(file_path, page_num)

            block = {
                "chunk_id"      : chunk_id,
                "source_url"    : file_path,
                "document_title": document_title,
                "organization"  : org_name,
                "section_title" : f"Page {page_num}",
                "page_number"   : page_num,
                "section_level" : "",
                "chapter"       : "",
                "article"       : "",
                "content_type"  : "paragraph",
                "text"          : text,
                "char_count"    : len(text),
                "extracted_at"  : extracted_at,
            }
            blocks.append(block)
        except Exception as e:
            logger.warning(f"Error extracting page {page_num} from {file_path}: {e}")

    pdf_document.close()

    _save_blocks(blocks)
    logger.info(f"PDF loading complete. Pages extracted: {len(blocks)}")
    return blocks

