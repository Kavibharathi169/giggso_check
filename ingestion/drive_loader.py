import logging
import os
import re
import tempfile
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _extract_file_id(url: str) -> str:
    """Extract the Google Drive file ID from various URL formats."""
    patterns = [
        r"/file/d/([a-zA-Z0-9_-]+)",      # /file/d/<id>/view
        r"id=([a-zA-Z0-9_-]+)",            # ?id=<id>
        r"/d/([a-zA-Z0-9_-]+)",            # /d/<id>/edit
        r"open\?id=([a-zA-Z0-9_-]+)",      # open?id=<id>
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return ""


def _download_from_drive(file_id: str, output_path: str) -> bool:
    """Download a file from Google Drive using the public export link."""
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    
    try:
        session = requests.Session()
        res = session.get(download_url, headers=headers, stream=True, timeout=30)
        res.raise_for_status()
        
        # Handle Google Drive virus scan confirmation page for large files
        for key, value in res.cookies.items():
            if key.startswith("download_warning"):
                download_url = f"{download_url}&confirm={value}"
                res = session.get(download_url, headers=headers, stream=True, timeout=30)
                break
        
        with open(output_path, "wb") as f:
            for chunk in res.iter_content(chunk_size=32768):
                if chunk:
                    f.write(chunk)
        
        logger.info(f"Downloaded Google Drive file {file_id} to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to download from Google Drive: {e}")
        return False


def _detect_file_type(file_path: str) -> str:
    """Detect file type by reading the first few bytes (magic bytes)."""
    try:
        with open(file_path, "rb") as f:
            header = f.read(8)
        
        if header[:4] == b'%PDF':
            return "pdf"
        elif header[:4] == b'PK\x03\x04':
            # Could be .docx or .xlsx (both are ZIP-based)
            if file_path.endswith(".xlsx"):
                return "excel"
            return "word"  # Default to word for PK archives
        elif header[:2] in (b'\xff\xfe', b'\xfe\xff') or header[:3] == b'\xef\xbb\xbf':
            return "txt"  # BOM-encoded text
        else:
            # Try to read as text
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    sample = f.read(500)
                if "," in sample and "\n" in sample:
                    return "csv"
                return "txt"
            except UnicodeDecodeError:
                return "pdf"  # Binary file, assume PDF
    except Exception:
        return "txt"


def load_drive_document(
    drive_url: str,
    document_type: str,
    org_name: str
) -> list[dict]:
    """
    Download a document from Google Drive and route it to the appropriate loader.
    Supports publicly shared Drive files.
    Returns list of extracted block dicts.
    """
    logger.info(f"Processing Google Drive link: {drive_url}")
    
    file_id = _extract_file_id(drive_url)
    if not file_id:
        logger.error(f"Could not extract file ID from Drive URL: {drive_url}")
        return []
    
    # Download to temp file
    fd, tmp_path = tempfile.mkstemp(suffix=".tmp")
    os.close(fd)
    
    if not _download_from_drive(file_id, tmp_path):
        return []
    
    try:
        # Detect file type and route to correct loader
        file_type = _detect_file_type(tmp_path)
        logger.info(f"Detected file type: {file_type} for Drive file {file_id}")
        
        if file_type == "pdf":
            final_path = tmp_path + ".pdf"
            os.rename(tmp_path, final_path)
            from ingestion.pdf_loader import load_pdf
            return load_pdf(final_path, document_type, org_name)
        
        elif file_type == "word":
            final_path = tmp_path + ".docx"
            os.rename(tmp_path, final_path)
            from ingestion.word_loader import load_word
            return load_word(final_path, document_type, org_name)
        
        elif file_type == "excel":
            final_path = tmp_path + ".xlsx"
            os.rename(tmp_path, final_path)
            from ingestion.excel_loader import load_excel
            return load_excel(final_path, document_type, org_name)
        
        elif file_type == "csv":
            final_path = tmp_path + ".csv"
            os.rename(tmp_path, final_path)
            from ingestion.csv_loader import load_csv
            return load_csv(final_path, document_type, org_name)
        
        else:
            # Plain text fallback
            import hashlib
            from datetime import datetime, timezone
            try:
                with open(tmp_path, "r", encoding="utf-8") as f:
                    text = f.read()
            except Exception:
                return []
            
            chunk_id = hashlib.sha256(drive_url.encode("utf-8")).hexdigest()[:16]
            return [{
                "chunk_id": chunk_id,
                "source_url": drive_url,
                "document_title": f"Drive Document ({file_id[:8]})",
                "organization": org_name,
                "section_title": "Google Drive Document",
                "section_level": "",
                "chapter": "",
                "article": "",
                "content_type": "paragraph",
                "text": text,
                "char_count": len(text),
                "extracted_at": datetime.now(timezone.utc).isoformat(),
            }]
    except Exception as e:
        logger.error(f"Failed to process Google Drive document: {e}")
        return []
    finally:
        # Clean up temp files
        for path in [tmp_path, tmp_path + ".pdf", tmp_path + ".docx", 
                     tmp_path + ".xlsx", tmp_path + ".csv"]:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass
