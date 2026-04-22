import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SUPPORTED_SOURCE_TYPES = [
    "webpage",
    "pdf",
    "excel",
    "csv",
    "word",
    "txt",
    "image",
    "google_drive"
]

def _download_to_tmp(url: str, ext: str) -> str:
    import tempfile
    import requests
    import os
    
    logger.info(f"Downloading file from URL: {url}")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    
    # Use stream=True to prevent loading large files entirely into memory
    res = requests.get(url, headers=headers, timeout=15, stream=True, verify=False)
    res.raise_for_status()
    
    # Create temp file and ensure it is properly closed before returning
    fd, tmp = tempfile.mkstemp(suffix=ext)
    try:
        with os.fdopen(fd, 'wb') as f:
            for chunk in res.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        logger.info(f"Successfully downloaded {url} to {tmp}")
        return tmp
    except Exception as e:
        logger.error(f"Error writing text/bytes to temp file for {url}: {e}")
        raise

def route_file(file_path: str, document_type: str, org_name: str) -> list[dict]:
    """Helper to auto-detect source_type from file extension and route."""      
    if file_path.startswith("http"):
        # Let's check the URL ending to see if it's a direct file link
        path_lower = file_path.lower()
        if path_lower.endswith(".pdf"):
            from ingestion.pdf_loader import load_pdf
            tmp = _download_to_tmp(file_path, ".pdf")
            return load_pdf(tmp, document_type, org_name)
        elif path_lower.endswith(".docx"):
            from ingestion.word_loader import load_word
            tmp = _download_to_tmp(file_path, ".docx")
            return load_word(tmp, document_type, org_name)
        elif path_lower.endswith(".xlsx") or path_lower.endswith(".csv"):
            if path_lower.endswith(".csv"):
                from ingestion.csv_loader import load_csv
                tmp = _download_to_tmp(file_path, ".csv")
                return load_csv(tmp, document_type, org_name)
            from ingestion.excel_loader import load_excel
            tmp = _download_to_tmp(file_path, ".xlsx")
            return load_excel(tmp, document_type, org_name)
        # Check if it's a Google Drive link
        if "drive.google.com" in path_lower or "docs.google.com" in path_lower:
            from ingestion.drive_loader import load_drive_document
            return load_drive_document(file_path, document_type, org_name)
        # Otherwise treat as typical webpage
        return route_ingestion("webpage", file_path, document_type, org_name)

    ext = file_path.lower().split('.')[-1]
    if ext == "pdf":
        source_type = "pdf"
    elif ext in ["xlsx", "xls"]:
        source_type = "excel"
    elif ext == "csv":
        source_type = "csv"
    elif ext in ["docx", "doc"]:
        source_type = "word"
    elif ext in ["png", "jpg", "jpeg", "bmp", "tiff", "webp"]:
        source_type = "image"
    else:
        source_type = "txt"
        
    return route_ingestion(source_type, file_path, document_type, org_name)

def route_ingestion(
    source_type  : str,
    source       : str,
    document_type: str,
    org_name     : str,
    max_depth    : int = 2
) -> list[dict]:
    """
    Route ingestion request to the correct loader
    based on source_type.
    Returns list of extracted block dicts.
    """
    logger.info(
        f"Routing ingestion — "
        f"source_type: {source_type}, "
        f"source: {source}"
    )

    # Validate source_type
    if source_type not in SUPPORTED_SOURCE_TYPES:
        raise ValueError(
            f"Unsupported source_type: '{source_type}'. "
            f"Supported types: {SUPPORTED_SOURCE_TYPES}"
        )

    # ── Webpage ──────────────────────────────────────
    if source_type == "webpage":
        logger.info("Selected loader: Web Scraper")
        from ingestion.scraper import scrape
        return scrape(
            seed_url      = source,
            document_type = document_type,
            org_name      = org_name,
            max_depth     = max_depth
        )

    # ── PDF ──────────────────────────────────────────
    elif source_type == "pdf":
        logger.info("Selected loader: PDF Loader")
        from ingestion.pdf_loader import load_pdf
        return load_pdf(
            file_path     = source,
            document_type = document_type,
            org_name      = org_name
        )

    # ── Excel ─────────────────────────────────────────
    elif source_type == "excel":
        logger.info("Selected loader: Excel Loader")
        from ingestion.excel_loader import load_excel
        return load_excel(
            file_path     = source,
            document_type = document_type,
            org_name      = org_name
        )

    # ── CSV ──────────────────────────────────────────
    elif source_type == "csv":
        logger.info("Selected loader: CSV Loader")
        from ingestion.csv_loader import load_csv
        return load_csv(
            file_path     = source,
            document_type = document_type,
            org_name      = org_name
        )

    # ── Word ─────────────────────────────────────────
    elif source_type == "word":
        logger.info("Selected loader: Word Loader")
        from ingestion.word_loader import load_word
        return load_word(
            file_path     = source,
            document_type = document_type,
            org_name      = org_name
        )
        
    # ── Txt ──────────────────────────────────────────
    elif source_type == "txt":
        logger.info("Selected loader: TXT Loader fallback")
        import hashlib, datetime
        try:
            with open(source, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception:
            return []
            
        chunk_id = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
        return [{
            "chunk_id": chunk_id,
            "source_url": source,
            "document_title": os.path.basename(source),
            "organization": org_name,
            "section_title": "Text Document",
            "section_level": "",
            "chapter": "",
            "article": "",
            "content_type": "paragraph",
            "text": text,
            "char_count": len(text),
            "extracted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }]

    elif source_type == "image":
        logger.info("Selected loader: Image Loader")
        from ingestion.image_loader import load_image
        return load_image(
            file_path     = source,
            document_type = document_type,
            org_name      = org_name
        )

    return []