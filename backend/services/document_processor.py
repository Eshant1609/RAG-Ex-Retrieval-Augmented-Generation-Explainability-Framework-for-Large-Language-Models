import os
import re
import logging
from typing import Dict, List, Optional
import PyPDF2
import pdfplumber

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Process PDF documents: extract text, chunk, and prepare for embedding"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def process_document(self, filepath: str, filename: str) -> Dict:
        """
        Process a PDF document and extract text with metadata
        
        Args:
            filepath: Path to the PDF file
            filename: Original filename
            
        Returns:
            Dictionary with extracted text, chunks, and metadata
        """
        try:
            # Extract text from PDF
            text = self._extract_text(filepath)
            
            if not text or len(text.strip()) < 100:
                return {
                    'success': False,
                    'error': 'Could not extract sufficient text from PDF'
                }
            
            # Extract metadata
            metadata = self._extract_metadata(text, filename)
            
            # Chunk the text
            chunks = self._chunk_text(text)
            
            return {
                'success': True,
                'text': text,
                'chunks': chunks,
                'title': metadata.get('title', filename),
                'metadata': metadata,
                'chunk_count': len(chunks)
            }
            
        except Exception as e:
            logger.error(f"Error processing document {filename}: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to process document: {str(e)}'
            }
    
    def _extract_text(self, filepath: str) -> str:
        """Extract text from PDF using multiple methods"""
        text = ""
        
        # Try pdfplumber first (better for complex layouts)
        try:
            with pdfplumber.open(filepath) as pdf:
                pages_text = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        pages_text.append(page_text)
                text = '\n\n'.join(pages_text)
        except Exception as e:
            logger.warning(f"pdfplumber failed, trying PyPDF2: {str(e)}")
        
        # Fallback to PyPDF2
        if not text or len(text.strip()) < 100:
            try:
                with open(filepath, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    pages_text = []
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            pages_text.append(page_text)
                    text = '\n\n'.join(pages_text)
            except Exception as e:
                logger.error(f"PyPDF2 extraction failed: {str(e)}")
                raise
        
        # Clean text
        text = self._clean_text(text)
        return text
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\[\]\"\']', ' ', text)
        # Remove multiple spaces
        text = re.sub(r' +', ' ', text)
        return text.strip()
    
    def _extract_metadata(self, text: str, filename: str) -> Dict:
        """Extract metadata from document text"""
        metadata = {
            'filename': filename,
            'word_count': len(text.split()),
            'char_count': len(text)
        }
        
        # Try to extract title (first line or first sentence)
        lines = text.split('\n')
        if lines:
            # Look for title-like patterns
            first_line = lines[0].strip()
            if len(first_line) > 10 and len(first_line) < 200:
                metadata['title'] = first_line
            else:
                # Try first sentence
                sentences = re.split(r'[.!?]', text)
                if sentences:
                    metadata['title'] = sentences[0].strip()[:200]
        
        # Try to extract abstract
        abstract_match = re.search(r'(?i)abstract[:\s]+(.+?)(?:\n\n|introduction|1\.)', text, re.DOTALL)
        if abstract_match:
            metadata['abstract'] = abstract_match.group(1).strip()[:500]
        
        # Try to extract authors
        author_patterns = [
            r'(?i)(?:authors?|by)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+and\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)*)',
            r'([A-Z][a-z]+\s+[A-Z]\.\s+[A-Z][a-z]+(?:\s+and\s+[A-Z][a-z]+\s+[A-Z]\.\s+[A-Z][a-z]+)*)'
        ]
        for pattern in author_patterns:
            match = re.search(pattern, text[:2000])
            if match:
                metadata['authors'] = match.group(1).strip()
                break
        
        return metadata
    
    def _chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks for embedding
        
        Args:
            text: Full document text
            
        Returns:
            List of text chunks
        """
        chunks = []
        
        # Split by sentences first for better chunking
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        current_chunk = ""
        for sentence in sentences:
            # If adding this sentence would exceed chunk size
            if len(current_chunk) + len(sentence) > self.chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                
                # Start new chunk with overlap
                overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                current_chunk = overlap_text + " " + sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        # Add the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # If chunks are too large, split them further
        final_chunks = []
        for chunk in chunks:
            if len(chunk) <= self.chunk_size:
                final_chunks.append(chunk)
            else:
                # Split large chunks by words
                words = chunk.split()
                temp_chunk = ""
                for word in words:
                    if len(temp_chunk) + len(word) + 1 > self.chunk_size:
                        if temp_chunk:
                            final_chunks.append(temp_chunk.strip())
                        temp_chunk = word
                    else:
                        temp_chunk += " " + word if temp_chunk else word
                if temp_chunk:
                    final_chunks.append(temp_chunk.strip())
        
        return final_chunks

