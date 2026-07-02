from pathlib import Path
from fastapi_app.core.config import MEDIA_DIR
from uuid import uuid4
from typing import Optional

# ============================================================================
# MEDIA ROOT
# ============================================================================

MEDIA_ROOT = Path(MEDIA_DIR)

MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

# ============================================================================
# DEFAULT UPLOAD FOLDERS
# ============================================================================

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".webp",
    ".svg",
}

DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".txt",
    ".rtf",
}

CSV_EXTENSIONS = {
    ".csv",
}

EXCEL_EXTENSIONS = {
    ".xls",
    ".xlsx",
}

PRESENTATION_EXTENSIONS = {
    ".ppt",
    ".pptx",
}

ARCHIVE_EXTENSIONS = {
    ".zip",
    ".rar",
    ".7z",
    ".tar",
    ".gz",
}


# ============================================================================
# DETERMINE DEFAULT FOLDER
# ============================================================================

def get_upload_folder(extension: str) -> str:
    """
    Automatically determine upload folder based on extension.
    Used only when folder is not explicitly provided.
    """

    extension = extension.lower()

    if extension in IMAGE_EXTENSIONS:
        return "uploads/images"

    if extension in CSV_EXTENSIONS:
        return "uploads/csv"

    if extension in EXCEL_EXTENSIONS:
        return "uploads/excel"

    if extension in DOCUMENT_EXTENSIONS:
        return "uploads/documents"

    if extension in PRESENTATION_EXTENSIONS:
        return "uploads/presentations"

    if extension in ARCHIVE_EXTENSIONS:
        return "uploads/archives"

    return "uploads/others"


# ============================================================================
# SAVE FILE
# ============================================================================

def save_uploaded_file(
    file_bytes: bytes,
    filename: str,
    folder: Optional[str] = None,
) -> dict:
    """
    Save uploaded file.

    Parameters
    ----------
    file_bytes : bytes
    filename : original filename
    folder : Optional[str]

        If provided:
            profile_pictures
            company_logos
            reports
            etc...

        If None:
            Automatically categorizes based on extension.

    Returns
    -------
    dict
    """

    extension = Path(filename).suffix.lower()

    if not folder:
        folder = get_upload_folder(extension)

    upload_dir = MEDIA_ROOT / folder

    upload_dir.mkdir(parents=True, exist_ok=True)

    unique_filename = f"{uuid4().hex}{extension}"

    file_path = upload_dir / unique_filename

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    return {
        "filename": unique_filename,
        "original_filename": filename,
        "extension": extension,
        "folder": folder,
        "file_path": str(file_path),
        "file_url": f"/media/{folder}/{unique_filename}",
    }


# ============================================================================
# DELETE FILE
# ============================================================================

def delete_file(file_path: str) -> bool:
    """
    Delete a file from disk.
    """

    path = Path(file_path)

    if path.exists():
        path.unlink()
        return True

    return False


# ============================================================================
# REPLACE FILE
# ============================================================================

def replace_file(
    old_file_path: str,
    file_bytes: bytes,
    filename: str,
    folder: Optional[str] = None,
) -> dict:
    """
    Delete old file and save new one.
    """

    delete_file(old_file_path)

    return save_uploaded_file(
        file_bytes=file_bytes,
        filename=filename,
        folder=folder,
    )


# ============================================================================
# FILE EXISTS
# ============================================================================

def file_exists(file_path: str) -> bool:
    return Path(file_path).exists()


# ============================================================================
# FILE SIZE
# ============================================================================

def get_file_size(file_path: str) -> int:
    path = Path(file_path)

    if path.exists():
        return path.stat().st_size

    return 0


# ============================================================================
# FILE EXTENSION
# ============================================================================

def get_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


# ============================================================================
# CREATE MEDIA SUBDIRECTORY
# ============================================================================

def create_media_folder(folder: str) -> Path:
    """
    Creates folder if it doesn't exist.
    """

    directory = MEDIA_ROOT / folder

    directory.mkdir(parents=True, exist_ok=True)

    return directory