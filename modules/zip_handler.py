import io
import zipfile
from typing import Dict, Tuple


def extract_zip_files(zip_bytes: bytes) -> Dict[str, str]:
    """Extract all files from uploaded zip and return as dict"""
    files_dict = {}
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_file:
            for file_info in zip_file.filelist:
                if not file_info.filename.endswith('/'):  # Skip directories
                    content = zip_file.read(file_info.filename).decode('utf-8', errors='ignore')
                    files_dict[file_info.filename] = content
        return files_dict
    except Exception as e:
        raise ValueError(f"Failed to extract zip file: {str(e)}")


def create_zip_from_dict(files_dict: Dict[str, str]) -> bytes:
    """Create zip file from dict preserving original filenames"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, content in files_dict.items():
            zip_file.writestr(filename, content)
    zip_buffer.seek(0)
    return zip_buffer.read()