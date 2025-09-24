import io
import zipfile
from typing import Dict


def create_zip_download(modified_files: Dict[str, str]) -> bytes:
    """Create a zip file containing all modified files"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, content in modified_files.items():
            zip_file.writestr(filename, content)
    zip_buffer.seek(0)
    return zip_buffer.read()


