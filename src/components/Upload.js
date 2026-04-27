import React, { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { FaUpload, FaSpinner, FaCheckCircle, FaTimesCircle, FaFolder, FaFolderPlus, FaFilePdf, FaCloudUploadAlt } from 'react-icons/fa';
import api from '../services/api';
import './Upload.css';

const Upload = ({ onUploaded, setLoading }) => {
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [folders, setFolders] = useState([]);
  const [selectedFolder, setSelectedFolder] = useState('');
  const [createNewFolder, setCreateNewFolder] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');

  useEffect(() => {
    loadFolders();
  }, []);

  const loadFolders = async () => {
    try {
      const response = await api.get('/api/folders');
      if (response.data.success) {
        setFolders(response.data.folders);
      }
    } catch (error) {
      console.error('Error loading folders:', error);
    }
  };

  const onDrop = useCallback(async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return;

    // Validate all files
    const validFiles = acceptedFiles.filter(file => {
      if (file.type !== 'application/pdf') {
        return false;
      }
      if (file.size > 50 * 1024 * 1024) {
        return false;
      }
      return true;
    });

    if (validFiles.length === 0) {
      setUploadStatus({
        type: 'error',
        message: 'Please upload valid PDF files (max 50MB each)'
      });
      return;
    }

    setUploading(true);
    setUploadStatus(null);
    setLoading(true);

    const formData = new FormData();
    validFiles.forEach(file => {
      formData.append('files', file);
    });

    if (createNewFolder && newFolderName.trim()) {
      formData.append('create_new_folder', 'true');
      formData.append('folder_name', newFolderName.trim());
    } else if (selectedFolder) {
      formData.append('folder_id', selectedFolder);
    }

    try {
      const response = await api.post('/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      if (response.data.success) {
        setUploadStatus({
          type: 'success',
          message: `Successfully processed ${response.data.documents.length} document(s)!`
        });
        setUploadedFiles(response.data.documents);
        if (response.data.folder_id) {
          await loadFolders();
        }
        onUploaded();
        // Reset form
        setCreateNewFolder(false);
        setNewFolderName('');
        setSelectedFolder('');
      } else {
        setUploadStatus({
          type: 'error',
          message: response.data.error || 'Upload failed'
        });
      }
    } catch (error) {
      console.error('Upload error:', error);
      setUploadStatus({
        type: 'error',
        message: error.response?.data?.error || 'Failed to upload documents. Please try again.'
      });
    } finally {
      setUploading(false);
      setLoading(false);
    }
  }, [onUploaded, setLoading, selectedFolder, createNewFolder, newFolderName]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    multiple: true,
    disabled: uploading
  });

  const resetUpload = () => {
    setUploadStatus(null);
    setUploadedFiles([]);
    setCreateNewFolder(false);
    setNewFolderName('');
    setSelectedFolder('');
  };

  return (
    <div className="upload-container-modern">
      <div className="upload-header">
        <h1 className="upload-title">Upload Research Papers</h1>
        <p className="upload-subtitle">Add single or multiple PDF files to your research database</p>
      </div>

      <div className="card-modern upload-main-card">
        <div className="folder-management-section">
          <h3 className="section-title-small">
            <FaFolder className="section-icon" />
            Folder Management
          </h3>
          <div className="folder-options-grid">
            <div className="folder-option-card">
              <input
                type="radio"
                id="existing-folder"
                name="folder-type"
                checked={!createNewFolder}
                onChange={() => setCreateNewFolder(false)}
                className="radio-input"
              />
              <label htmlFor="existing-folder" className="folder-option-label">
                Add to Existing Folder
              </label>
              {!createNewFolder && (
                <select
                  className="input-modern"
                  value={selectedFolder}
                  onChange={(e) => setSelectedFolder(e.target.value)}
                  disabled={uploading}
                >
                  <option value="">No folder (standalone)</option>
                  {folders.map(folder => (
                    <option key={folder.folder_id} value={folder.folder_id}>
                      {folder.name} ({folder.document_count || 0} docs)
                    </option>
                  ))}
                </select>
              )}
            </div>
            <div className="folder-option-card">
              <input
                type="radio"
                id="new-folder"
                name="folder-type"
                checked={createNewFolder}
                onChange={() => setCreateNewFolder(true)}
                className="radio-input"
              />
              <label htmlFor="new-folder" className="folder-option-label">
                <FaFolderPlus className="label-icon" />
                Create New Folder
              </label>
              {createNewFolder && (
                <input
                  type="text"
                  className="input-modern"
                  placeholder="Enter folder name"
                  value={newFolderName}
                  onChange={(e) => setNewFolderName(e.target.value)}
                  disabled={uploading}
                />
              )}
            </div>
          </div>
        </div>

        {!uploadStatus && (
          <div
            {...getRootProps()}
            className={`dropzone-modern ${isDragActive ? 'active' : ''} ${uploading ? 'disabled' : ''}`}
          >
            <input {...getInputProps()} />
            {uploading ? (
              <div className="dropzone-content">
                <FaSpinner className="spinner-large" />
                <p className="dropzone-text-primary">Processing documents...</p>
                <p className="dropzone-text-secondary">This may take a few moments</p>
              </div>
            ) : (
              <div className="dropzone-content">
                <div className="dropzone-icon-wrapper">
                  {isDragActive ? (
                    <FaCloudUploadAlt className="dropzone-icon" />
                  ) : (
                    <FaUpload className="dropzone-icon" />
                  )}
                </div>
                <p className="dropzone-text-primary">
                  {isDragActive
                    ? 'Drop PDF files here'
                    : 'Drag & drop PDF files here, or click to select'}
                </p>
                <p className="dropzone-text-secondary">
                  Multiple files supported • PDF only • Max 50MB per file
                </p>
              </div>
            )}
          </div>
        )}

        {uploadStatus && (
          <div className={`alert-modern alert-${uploadStatus.type}`}>
            <div className="alert-icon-wrapper">
              {uploadStatus.type === 'success' ? (
                <FaCheckCircle className="alert-icon" />
              ) : (
                <FaTimesCircle className="alert-icon" />
              )}
            </div>
            <div className="alert-content">
              <p className="alert-message">{uploadStatus.message}</p>
              {uploadedFiles.length > 0 && (
                <div className="uploaded-files-list">
                  <p className="files-list-title"><strong>Uploaded Files:</strong></p>
                  <ul className="files-list">
                    {uploadedFiles.map((file, index) => (
                      <li key={index} className="file-item">
                        <FaFilePdf className="file-icon" />
                        <span>{file.filename}</span>
                        <span className="file-meta">({file.chunks} chunks)</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}

        {uploadStatus && (
          <button className="btn-secondary btn-full" onClick={resetUpload}>
            Upload More Files
          </button>
        )}
      </div>

      <div className="card-modern folders-display-card">
        <div className="folders-header">
          <h3 className="section-title-small">
            <FaFolder className="section-icon" />
            Your Folders
          </h3>
          <button className="btn-refresh" onClick={loadFolders}>
            Refresh
          </button>
        </div>
        {folders.length === 0 ? (
          <div className="empty-folders">
            <FaFolder className="empty-folder-icon" />
            <p>No folders yet. Create one when uploading files!</p>
          </div>
        ) : (
          <div className="folders-grid-modern">
            {folders.map(folder => (
              <div key={folder.folder_id} className="folder-card-modern">
                <div className="folder-card-icon">
                  <FaFolder />
                </div>
                <div className="folder-card-content">
                  <h4 className="folder-card-name">{folder.name}</h4>
                  <p className="folder-card-count">{folder.document_count || 0} documents</p>
                  {folder.description && (
                    <p className="folder-card-desc">{folder.description}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Upload;
