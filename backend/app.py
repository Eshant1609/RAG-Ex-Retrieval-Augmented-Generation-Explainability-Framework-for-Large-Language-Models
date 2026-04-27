from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename
import logging

from services.document_processor import DocumentProcessor
from services.vector_store import VectorStore
from services.rag_service import RAGService
from services.export_service import ExportService
from services.folder_manager import FolderManager
from utils.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_FILE_SIZE * 10  # Allow multiple files
app.config['ALLOWED_EXTENSIONS'] = Config.ALLOWED_EXTENSIONS

# Initialize services
document_processor = DocumentProcessor()
vector_store = VectorStore()
rag_service = RAGService(vector_store)
export_service = ExportService()
folder_manager = FolderManager()

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(Config.SUMMARIES_FOLDER, exist_ok=True)
os.makedirs(Config.EXPORT_FOLDER, exist_ok=True)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'RAG-Ex API is running',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/upload', methods=['POST'])
def upload_document():
    """Upload and process one or multiple research papers"""
    try:
        files = request.files.getlist('files') or request.files.getlist('file')
        folder_id = request.form.get('folder_id', '').strip()
        create_new_folder = request.form.get('create_new_folder', 'false').lower() == 'true'
        folder_name = request.form.get('folder_name', '').strip()
        
        if not files or (files and len(files) == 1 and files[0].filename == ''):
            return jsonify({'error': 'No files provided'}), 400
        
        # Filter valid files
        valid_files = [f for f in files if f.filename and allowed_file(f.filename)]
        if not valid_files:
            return jsonify({'error': 'No valid PDF files provided'}), 400
        
        # Create folder if needed
        if create_new_folder and folder_name:
            folder = folder_manager.create_folder(folder_name)
            folder_id = folder['folder_id']
        elif not folder_id and len(valid_files) > 1:
            # Auto-create folder for multiple files
            folder_name = f"Upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            folder = folder_manager.create_folder(folder_name)
            folder_id = folder['folder_id']
        
        processed_documents = []
        errors = []
        
        for file in valid_files:
            try:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                logger.info(f"Processing document: {filename}")
                
                # Process document
                result = document_processor.process_document(filepath, filename)
                
                if result['success']:
                    # Store in vector database
                    doc_id = vector_store.add_document(
                        text=result['text'],
                        metadata={
                            'filename': filename,
                            'title': result.get('title', filename),
                            'upload_date': datetime.now().isoformat(),
                            'chunks': len(result.get('chunks', []))
                        },
                        chunks=result.get('chunks', [])
                    )
                    
                    # Add to folder if folder_id provided
                    if folder_id:
                        folder_manager.add_document_to_folder(
                            folder_id,
                            doc_id,
                            {
                                'filename': filename,
                                'title': result.get('title', filename),
                                'chunks': len(result.get('chunks', []))
                            }
                        )
                    
                    processed_documents.append({
                        'document_id': doc_id,
                        'filename': filename,
                        'title': result.get('title', filename),
                        'chunks': len(result.get('chunks', []))
                    })
                else:
                    errors.append(f"{filename}: {result.get('error', 'Processing failed')}")
            except Exception as e:
                logger.error(f"Error processing {file.filename}: {str(e)}")
                errors.append(f"{file.filename}: {str(e)}")
        
        return jsonify({
            'success': True,
            'message': f'Processed {len(processed_documents)} document(s)',
            'documents': processed_documents,
            'folder_id': folder_id if folder_id else None,
            'errors': errors if errors else None
        }), 200
            
    except Exception as e:
        logger.error(f"Error uploading documents: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/query', methods=['POST'])
def query_documents():
    """Query the document database using RAG with document/folder selection"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        top_k = data.get('top_k', 5)
        document_ids = data.get('document_ids', [])
        folder_ids = data.get('folder_ids', [])
        
        logger.info(f"Processing query: {query[:50]}...")
        
        # Get document IDs from folders if specified
        if folder_ids:
            for folder_id in folder_ids:
                folder_docs = folder_manager.get_folder_documents(folder_id)
                document_ids.extend(folder_docs)
        
        # Remove duplicates
        document_ids = list(set(document_ids))
        
        # Get response using RAG with document filtering
        if document_ids:
            response = rag_service.query_with_documents(query, document_ids, top_k=top_k)
        else:
            response = rag_service.query(query, top_k=top_k)
        
        return jsonify({
            'success': True,
            'query': query,
            'response': response['answer'],
            'sources': response.get('sources', []),
            'metadata': response.get('metadata', {})
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/summarize', methods=['POST'])
def summarize_documents():
    """Generate contextual summary of documents with folder support"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        document_ids = data.get('document_ids', [])
        folder_ids = data.get('folder_ids', [])
        summary_type = data.get('type', 'general')  # general, detailed, key_points
        
        # Get document IDs from folders if specified
        if folder_ids:
            for folder_id in folder_ids:
                folder_docs = folder_manager.get_folder_documents(folder_id)
                document_ids.extend(folder_docs)
        
        # Remove duplicates
        document_ids = list(set(document_ids))
        
        if not query and not document_ids:
            return jsonify({'error': 'Either query, document_ids, or folder_ids must be provided'}), 400
        
        logger.info(f"Generating summary: type={summary_type}, documents={len(document_ids)}")
        
        # Generate summary using RAG
        if query and document_ids:
            response = rag_service.summarize_with_documents(query, document_ids, summary_type=summary_type)
        elif query:
            response = rag_service.summarize(query, summary_type=summary_type)
        else:
            response = rag_service.summarize_by_ids(document_ids, summary_type=summary_type)
        
        # Save summary
        summary_id = export_service.save_summary(
            summary=response['summary'],
            metadata={
                'query': query,
                'document_ids': document_ids,
                'folder_ids': folder_ids,
                'type': summary_type,
                'sources': response.get('sources', []),
                'created_at': datetime.now().isoformat()
            }
        )
        
        return jsonify({
            'success': True,
            'summary_id': summary_id,
            'summary': response['summary'],
            'sources': response.get('sources', []),
            'metadata': response.get('metadata', {})
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/documents', methods=['GET'])
def list_documents():
    """List all uploaded documents"""
    try:
        documents = vector_store.list_documents()
        return jsonify({
            'success': True,
            'documents': documents,
            'count': len(documents)
        }), 200
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/documents/<document_id>', methods=['GET'])
def get_document(document_id):
    """Get document details"""
    try:
        document = vector_store.get_document(document_id)
        if document:
            return jsonify({
                'success': True,
                'document': document
            }), 200
        else:
            return jsonify({'error': 'Document not found'}), 404
    except Exception as e:
        logger.error(f"Error getting document: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/documents/<document_id>', methods=['DELETE'])
def delete_document(document_id):
    """Delete a document"""
    try:
        success = vector_store.delete_document(document_id)
        if success:
            return jsonify({
                'success': True,
                'message': 'Document deleted successfully'
            }), 200
        else:
            return jsonify({'error': 'Document not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/summaries', methods=['GET'])
def list_summaries():
    """List all generated summaries"""
    try:
        summaries = export_service.list_summaries()
        return jsonify({
            'success': True,
            'summaries': summaries,
            'count': len(summaries)
        }), 200
    except Exception as e:
        logger.error(f"Error listing summaries: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/summaries/<summary_id>', methods=['GET'])
def get_summary(summary_id):
    """Get a specific summary"""
    try:
        summary = export_service.get_summary(summary_id)
        if summary:
            return jsonify({
                'success': True,
                'summary': summary
            }), 200
        else:
            return jsonify({'error': 'Summary not found'}), 404
    except Exception as e:
        logger.error(f"Error getting summary: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/export', methods=['POST'])
def export_data():
    """Export summaries or documents in various formats"""
    try:
        data = request.get_json()
        export_type = data.get('type', 'markdown')  # markdown, json, pdf
        summary_id = data.get('summary_id')
        document_ids = data.get('document_ids', [])
        
        if not summary_id and not document_ids:
            return jsonify({'error': 'Either summary_id or document_ids must be provided'}), 400
        
        # Generate export file
        filepath = export_service.export(
            export_type=export_type,
            summary_id=summary_id,
            document_ids=document_ids
        )
        
        if filepath:
            return send_file(
                filepath,
                as_attachment=True,
                download_name=os.path.basename(filepath)
            )
        else:
            return jsonify({'error': 'Export failed'}), 500
            
    except Exception as e:
        logger.error(f"Error exporting data: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/search', methods=['POST'])
def search_documents():
    """Semantic search for documents"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        top_k = data.get('top_k', 10)
        
        results = vector_store.search(query, top_k=top_k)
        
        return jsonify({
            'success': True,
            'query': query,
            'results': results,
            'count': len(results)
        }), 200
        
    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

# Folder management endpoints
@app.route('/api/folders', methods=['GET'])
def list_folders():
    """List all folders"""
    try:
        folders = folder_manager.list_folders()
        # Add document count for each folder
        for folder in folders:
            folder['document_count'] = len(folder.get('documents', []))
        return jsonify({
            'success': True,
            'folders': folders,
            'count': len(folders)
        }), 200
    except Exception as e:
        logger.error(f"Error listing folders: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/folders', methods=['POST'])
def create_folder():
    """Create a new folder"""
    try:
        data = request.get_json()
        folder_name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        if not folder_name:
            return jsonify({'error': 'Folder name is required'}), 400
        
        folder = folder_manager.create_folder(folder_name, description)
        return jsonify({
            'success': True,
            'folder': folder
        }), 200
    except Exception as e:
        logger.error(f"Error creating folder: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/folders/<folder_id>', methods=['GET'])
def get_folder(folder_id):
    """Get folder details"""
    try:
        folder = folder_manager.get_folder(folder_id)
        if folder:
            return jsonify({
                'success': True,
                'folder': folder
            }), 200
        else:
            return jsonify({'error': 'Folder not found'}), 404
    except Exception as e:
        logger.error(f"Error getting folder: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/folders/<folder_id>', methods=['DELETE'])
def delete_folder(folder_id):
    """Delete a folder"""
    try:
        success = folder_manager.delete_folder(folder_id)
        if success:
            return jsonify({
                'success': True,
                'message': 'Folder deleted successfully'
            }), 200
        else:
            return jsonify({'error': 'Folder not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting folder: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/folders/<folder_id>/documents/<document_id>', methods=['DELETE'])
def remove_document_from_folder(folder_id, document_id):
    """Remove a document from a folder"""
    try:
        success = folder_manager.remove_document_from_folder(folder_id, document_id)
        if success:
            return jsonify({
                'success': True,
                'message': 'Document removed from folder'
            }), 200
        else:
            return jsonify({'error': 'Folder or document not found'}), 404
    except Exception as e:
        logger.error(f"Error removing document from folder: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '5511'))
    logger.info(f"Starting RAG-Ex API server on {host}:{port}...")
    app.run(debug=True, host=host, port=port)
