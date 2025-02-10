from typing import BinaryIO
import pdfplumber
from docx import Document
import io
import os
from pathlib import Path

def save_file(file_content: bytes, file_name: str, save_dir: str = "saved_reports") -> str:
    """
    Save a file to the specified directory.
    
    :param file_content: The binary content of the file.
    :param file_name: The name of the file to be saved.
    :param save_dir: The directory where the file should be stored. Defaults to 'saved_reports'.
    :return: The full path of the saved file.
    """
    try:
        # Ensure the directory exists
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        
        # Define the full file path
        file_path = os.path.join(save_dir, file_name)
        
        # Write the file content to the specified path
        with open(file_path, "wb") as file:
            file.write(file_content)
        
        return file_path
    except Exception as e:
        raise IOError(f"Failed to save file {file_name}: {str(e)}")


async def extract_text_from_file(file: BinaryIO, content_type: str) -> str:
    """
    Extract text from various file formats asynchronously
    """
    try:
        content = await file.read()
        file_bytes = io.BytesIO(content)
        
        if content_type == "application/pdf":
            with pdfplumber.open(file_bytes) as pdf:
                return "\n".join(page.extract_text() for page in pdf.pages)
                
        elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = Document(file_bytes)
            return "\n".join(paragraph.text for paragraph in doc.paragraphs)
            
        elif content_type == "text/plain":
            return content.decode('utf-8')
            
        else:
            raise ValueError(f"Unsupported file type: {content_type}")
            
    except Exception as e:
        raise ValueError(f"Error extracting text from file: {str(e)}")
    finally:
        await file.close()
