"""
Service for handling universal document ingestion and chunking.
Supports PDF, Word, Excel, CSV, HTML, and text-based files.
Uses PyMuPDF (fitz) for PDF parsing with semantic chunking strategy.
"""
import fitz  # PyMuPDF
from typing import List, Dict, Optional
from pathlib import Path
import re
from finetuneme.core.config import settings

# Import the new universal loader system


class DocumentChunk:
    """Represents a chunk of text from a document"""
    def __init__(self, text: str, page_num: int, metadata: Dict = None, images: Optional[List[str]] = None):
        self.text = text
        self.page_num = page_num
        self.metadata = metadata or {}
        self.images = images  # List of base64 encoded strings

def clean_text(text: str) -> str:
    """Clean extracted text"""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove non-printable characters
    text = ''.join(char for char in text if char.isprintable() or char in '\n\t')
    return text.strip()

def chunk_text_semantic(text: str, max_chunk_size: int = None, overlap: int = None) -> List[str]:
    """
    Chunk text semantically with overlap.
    Tries to split on paragraph boundaries, then sentences, then words.
    """
    if max_chunk_size is None:
        max_chunk_size = settings.CHUNK_SIZE
    if overlap is None:
        overlap = settings.CHUNK_OVERLAP

    # Split into paragraphs first
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # If adding this paragraph doesn't exceed limit, add it
        if len(current_chunk) + len(para) < max_chunk_size:
            current_chunk += para + "\n\n"
        else:
            # Save current chunk if it exists
            if current_chunk:
                chunks.append(current_chunk.strip())

                # Create overlap from end of previous chunk
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = overlap_text + para + "\n\n"
            else:
                current_chunk = para + "\n\n"

    # Add remaining chunk
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

def process_pdf(file_path: str) -> List[DocumentChunk]:
    """
    Process PDF file and extract text chunks.

    Args:
        file_path: Local filesystem path to the PDF file

    Returns:
        List of DocumentChunk objects
    """
    # Open PDF with PyMuPDF (directly from local file)
    doc = fitz.open(file_path)
    all_chunks = []

    # Extract text from each page
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()

        # Clean the text
        cleaned_text = clean_text(text)

        if not cleaned_text:
            continue

        # Chunk the page text
        page_chunks = chunk_text_semantic(cleaned_text)

        # Create DocumentChunk objects
        for chunk_text in page_chunks:
            chunk = DocumentChunk(
                text=chunk_text,
                page_num=page_num + 1,  # 1-indexed
                metadata={
                    "source": file_path,
                    "total_pages": len(doc)
                }
            )
            all_chunks.append(chunk)

    doc.close()

    return all_chunks


# Universal document processing function
# This is the new recommended function that supports all file types
def process_document(file_path: str) -> List[DocumentChunk]:
    """
    Process any supported document type (PDF, Word, Excel, CSV, HTML, text files, code).
    This function automatically detects the file type and uses the appropriate loader.

    Args:
        file_path: Local filesystem path to the document file

    Returns:
        List of DocumentChunk objects

    Raises:
        ValueError: If file type is not supported
    """
    # Import here to avoid circular dependency
    from finetuneme.services.loaders import process_document as process_any_document
    return process_any_document(file_path)
