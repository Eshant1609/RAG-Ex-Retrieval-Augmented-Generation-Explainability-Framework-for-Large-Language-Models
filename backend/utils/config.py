import os

class Config:
    """Configuration settings for RAG-Ex"""
    
    # File upload settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../../data/uploads')
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {'pdf'}
    
    # Vector database settings
    VECTOR_DB_PATH = os.path.join(os.path.dirname(__file__), '../../data/vector_db')
    EMBEDDING_MODEL = 'all-MiniLM-L6-v2'  # Sentence transformer model
    CHUNK_SIZE = 1000  # Characters per chunk
    CHUNK_OVERLAP = 200  # Overlap between chunks
    
    # Ollama settings
    OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2')  # Default model (change to match your installed model)
    
    # RAG settings
    TOP_K_RETRIEVAL = 5  # Number of chunks to retrieve
    TEMPERATURE = 0.7  # LLM temperature
    
    # Export settings
    SUMMARIES_FOLDER = os.path.join(os.path.dirname(__file__), '../../data/summaries')
    EXPORT_FOLDER = os.path.join(os.path.dirname(__file__), '../../data/exports')
    
    # Create necessary directories
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(VECTOR_DB_PATH, exist_ok=True)
    os.makedirs(SUMMARIES_FOLDER, exist_ok=True)
    os.makedirs(EXPORT_FOLDER, exist_ok=True)
