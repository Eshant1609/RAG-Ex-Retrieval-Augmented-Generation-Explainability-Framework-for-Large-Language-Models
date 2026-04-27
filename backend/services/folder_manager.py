import os
import json
import logging
import uuid
from typing import List, Dict, Optional
from datetime import datetime

from utils.config import Config

logger = logging.getLogger(__name__)

class FolderManager:
    """Manage folders and documents organization"""
    
    def __init__(self):
        self.folders_file = os.path.join(Config.VECTOR_DB_PATH, 'folders.json')
        self._load_folders()
    
    def _load_folders(self):
        """Load folders from file"""
        if os.path.exists(self.folders_file):
            try:
                with open(self.folders_file, 'r') as f:
                    self.folders = json.load(f)
            except Exception as e:
                logger.error(f"Error loading folders: {str(e)}")
                self.folders = {}
        else:
            self.folders = {}
        self._save_folders()
    
    def _save_folders(self):
        """Save folders to file"""
        try:
            with open(self.folders_file, 'w') as f:
                json.dump(self.folders, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving folders: {str(e)}")
    
    def create_folder(self, folder_name: str, description: str = "") -> Dict:
        """Create a new folder"""
        folder_id = str(uuid.uuid4())
        folder = {
            'folder_id': folder_id,
            'name': folder_name,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'documents': []
        }
        self.folders[folder_id] = folder
        self._save_folders()
        logger.info(f"Created folder: {folder_name} ({folder_id})")
        return folder
    
    def add_document_to_folder(self, folder_id: str, document_id: str, document_metadata: Dict) -> bool:
        """Add a document to a folder"""
        if folder_id not in self.folders:
            return False
        
        # Check if document already exists
        for doc in self.folders[folder_id]['documents']:
            if doc['document_id'] == document_id:
                return True  # Already exists
        
        self.folders[folder_id]['documents'].append({
            'document_id': document_id,
            'filename': document_metadata.get('filename', 'unknown'),
            'title': document_metadata.get('title', 'unknown'),
            'added_at': datetime.now().isoformat(),
            **document_metadata
        })
        self.folders[folder_id]['updated_at'] = datetime.now().isoformat()
        self._save_folders()
        logger.info(f"Added document {document_id} to folder {folder_id}")
        return True
    
    def remove_document_from_folder(self, folder_id: str, document_id: str) -> bool:
        """Remove a document from a folder"""
        if folder_id not in self.folders:
            return False
        
        original_count = len(self.folders[folder_id]['documents'])
        self.folders[folder_id]['documents'] = [
            doc for doc in self.folders[folder_id]['documents']
            if doc['document_id'] != document_id
        ]
        
        if len(self.folders[folder_id]['documents']) < original_count:
            self.folders[folder_id]['updated_at'] = datetime.now().isoformat()
            self._save_folders()
            logger.info(f"Removed document {document_id} from folder {folder_id}")
            return True
        return False
    
    def delete_folder(self, folder_id: str) -> bool:
        """Delete a folder"""
        if folder_id in self.folders:
            del self.folders[folder_id]
            self._save_folders()
            logger.info(f"Deleted folder {folder_id}")
            return True
        return False
    
    def get_folder(self, folder_id: str) -> Optional[Dict]:
        """Get folder details"""
        return self.folders.get(folder_id)
    
    def list_folders(self) -> List[Dict]:
        """List all folders"""
        return list(self.folders.values())
    
    def get_folder_documents(self, folder_id: str) -> List[str]:
        """Get list of document IDs in a folder"""
        if folder_id not in self.folders:
            return []
        return [doc['document_id'] for doc in self.folders[folder_id]['documents']]
    
    def get_document_folders(self, document_id: str) -> List[str]:
        """Get list of folder IDs containing a document"""
        folder_ids = []
        for folder_id, folder in self.folders.items():
            for doc in folder['documents']:
                if doc['document_id'] == document_id:
                    folder_ids.append(folder_id)
                    break
        return folder_ids
    
    def update_folder(self, folder_id: str, name: Optional[str] = None, description: Optional[str] = None) -> bool:
        """Update folder metadata"""
        if folder_id not in self.folders:
            return False
        
        if name:
            self.folders[folder_id]['name'] = name
        if description is not None:
            self.folders[folder_id]['description'] = description
        
        self.folders[folder_id]['updated_at'] = datetime.now().isoformat()
        self._save_folders()
        return True

