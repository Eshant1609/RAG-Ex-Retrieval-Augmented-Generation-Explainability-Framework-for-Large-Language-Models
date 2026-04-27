import os
import logging
from typing import List, Dict, Optional, Any
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import uuid
from datetime import datetime

from utils.config import Config

logger = logging.getLogger(__name__)

class VectorStore:
    """Manage vector database for semantic search"""
    
    def __init__(self):
        self.embedding_model = SentenceTransformer(Config.EMBEDDING_MODEL)
        # Ensure directory exists
        os.makedirs(Config.VECTOR_DB_PATH, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=Config.VECTOR_DB_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
        # Reuse the persistent collection so data survives backend restarts.
        self.collection = self.client.get_or_create_collection(
            name="research_documents",
            metadata={"hnsw:space": "cosine"}
        )
        logger.info("Vector store initialized")
    
    def add_document(self, text: str, metadata: Dict, chunks: List[str]) -> str:
        """
        Add a document to the vector database
        
        Args:
            text: Full document text
            metadata: Document metadata
            chunks: List of text chunks
            
        Returns:
            Document ID
        """
        try:
            doc_id = str(uuid.uuid4())
            
            # Generate embeddings for chunks
            embeddings = self.embedding_model.encode(chunks, show_progress_bar=False)
            
            # Prepare IDs and metadata for each chunk
            chunk_ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
            chunk_metadatas = []
            
            for i, chunk in enumerate(chunks):
                chunk_metadata = {
                    'document_id': doc_id,
                    'chunk_index': i,
                    'filename': metadata.get('filename', 'unknown'),
                    'title': metadata.get('title', 'unknown'),
                    'upload_date': metadata.get('upload_date', datetime.now().isoformat())
                }
                chunk_metadatas.append(chunk_metadata)
            
            # Add to collection
            self.collection.add(
                ids=chunk_ids,
                embeddings=embeddings.tolist(),
                documents=chunks,
                metadatas=chunk_metadatas
            )
            
            # Store document-level metadata separately (in a simple JSON file for now)
            self._save_document_metadata(doc_id, metadata)
            
            logger.info(f"Added document {doc_id} with {len(chunks)} chunks")
            return doc_id
            
        except Exception as e:
            logger.error(f"Error adding document to vector store: {str(e)}")
            raise
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Perform semantic search
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of search results with metadata
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query], show_progress_bar=False)[0]
            
            # Search in collection
            results = self.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=top_k
            )
            
            # Format results
            formatted_results = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    result = {
                        'chunk_id': results['ids'][0][i],
                        'text': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i] if 'distances' in results else None,
                        'relevance_score': 1 - results['distances'][0][i] if 'distances' in results and results['distances'][0] else 1.0
                    }
                    formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching vector store: {str(e)}")
            raise
    
    def get_document_chunks(self, document_id: str) -> List[Dict]:
        """Get all chunks for a specific document"""
        try:
            results = self.collection.get(
                where={'document_id': document_id}
            )
            
            chunks = []
            if results['ids']:
                for i in range(len(results['ids'])):
                    chunks.append({
                        'chunk_id': results['ids'][i],
                        'text': results['documents'][i],
                        'metadata': results['metadatas'][i]
                    })
            
            # Sort by chunk index
            chunks.sort(key=lambda x: x['metadata'].get('chunk_index', 0))
            return chunks
            
        except Exception as e:
            logger.error(f"Error getting document chunks: {str(e)}")
            return []
    
    def list_documents(self) -> List[Dict]:
        """List all documents in the database"""
        try:
            # Get unique document IDs from metadata
            all_results = self.collection.get()
            
            document_map = {}
            if all_results['ids']:
                for i, metadata in enumerate(all_results['metadatas']):
                    doc_id = metadata.get('document_id')
                    if doc_id and doc_id not in document_map:
                        document_map[doc_id] = {
                            'document_id': doc_id,
                            'filename': metadata.get('filename', 'unknown'),
                            'title': metadata.get('title', 'unknown'),
                            'upload_date': metadata.get('upload_date', 'unknown'),
                            'chunk_count': 0
                        }
                    if doc_id:
                        document_map[doc_id]['chunk_count'] += 1
            
            # Load full metadata
            documents = []
            for doc_id in document_map:
                full_metadata = self._load_document_metadata(doc_id)
                if full_metadata:
                    document_map[doc_id].update(full_metadata)
                documents.append(document_map[doc_id])
            
            return documents
            
        except Exception as e:
            logger.error(f"Error listing documents: {str(e)}")
            return []
    
    def get_document(self, document_id: str) -> Optional[Dict]:
        """Get a specific document with all its chunks"""
        try:
            chunks = self.get_document_chunks(document_id)
            if not chunks:
                return None
            
            metadata = self._load_document_metadata(document_id)
            if not metadata:
                # Extract from first chunk
                if chunks:
                    metadata = chunks[0]['metadata']
            
            return {
                'document_id': document_id,
                'metadata': metadata,
                'chunks': chunks,
                'chunk_count': len(chunks)
            }
            
        except Exception as e:
            logger.error(f"Error getting document: {str(e)}")
            return None
    
    def delete_document(self, document_id: str) -> bool:
        """Delete a document and all its chunks"""
        try:
            # Get all chunk IDs for this document
            chunks = self.get_document_chunks(document_id)
            if not chunks:
                return False
            
            chunk_ids = [chunk['chunk_id'] for chunk in chunks]
            
            # Delete chunks from collection
            self.collection.delete(ids=chunk_ids)
            
            # Delete document metadata
            self._delete_document_metadata(document_id)
            
            logger.info(f"Deleted document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document: {str(e)}")
            return False
    
    def _save_document_metadata(self, doc_id: str, metadata: Dict):
        """Save document metadata to file"""
        import json
        metadata_file = os.path.join(Config.VECTOR_DB_PATH, f"{doc_id}_metadata.json")
        try:
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save metadata for {doc_id}: {str(e)}")
    
    def _load_document_metadata(self, doc_id: str) -> Optional[Dict]:
        """Load document metadata from file"""
        import json
        metadata_file = os.path.join(Config.VECTOR_DB_PATH, f"{doc_id}_metadata.json")
        try:
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load metadata for {doc_id}: {str(e)}")
        return None
    
    def _delete_document_metadata(self, doc_id: str):
        """Delete document metadata file"""
        metadata_file = os.path.join(Config.VECTOR_DB_PATH, f"{doc_id}_metadata.json")
        try:
            if os.path.exists(metadata_file):
                os.remove(metadata_file)
        except Exception as e:
            logger.warning(f"Could not delete metadata for {doc_id}: {str(e)}")
