import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';
import Navbar from './components/Navbar';
import Dashboard from './components/Dashboard';
import Upload from './components/Upload';
import Query from './components/Query';
import Summaries from './components/Summaries';
import api from './services/api';

function App() {
  const [documents, setDocuments] = useState([]);
  const [summaries, setSummaries] = useState([]);
  const [folders, setFolders] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadDocuments();
    loadSummaries();
    loadFolders();
  }, []);

  const loadDocuments = async () => {
    try {
      const response = await api.get('/api/documents');
      if (response.data.success) {
        setDocuments(response.data.documents);
      }
    } catch (error) {
      console.error('Error loading documents:', error);
    }
  };

  const loadSummaries = async () => {
    try {
      const response = await api.get('/api/summaries');
      if (response.data.success) {
        setSummaries(response.data.summaries);
      }
    } catch (error) {
      console.error('Error loading summaries:', error);
    }
  };

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

  const handleDocumentUploaded = () => {
    loadDocuments();
    loadFolders();
  };

  const handleSummaryCreated = () => {
    loadSummaries();
  };

  const handleDocumentDeleted = () => {
    loadDocuments();
    loadFolders();
  };

  return (
    <Router>
      <div className="App">
        <Navbar />
        <div className="main-content">
          <Routes>
            <Route 
              path="/" 
              element={<Navigate to="/dashboard" replace />} 
            />
            <Route 
              path="/dashboard" 
              element={
                <Dashboard 
                  documents={documents}
                  summaries={summaries}
                  onDocumentDeleted={handleDocumentDeleted}
                  loading={loading}
                />
              } 
            />
            <Route 
              path="/upload" 
              element={
                <Upload 
                  onUploaded={handleDocumentUploaded}
                  setLoading={setLoading}
                />
              } 
            />
            <Route 
              path="/query" 
              element={
                <Query 
                  documents={documents}
                  folders={folders}
                  onSummaryCreated={handleSummaryCreated}
                />
              } 
            />
            <Route 
              path="/summaries" 
              element={
                <Summaries 
                  summaries={summaries}
                  documents={documents}
                />
              } 
            />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
