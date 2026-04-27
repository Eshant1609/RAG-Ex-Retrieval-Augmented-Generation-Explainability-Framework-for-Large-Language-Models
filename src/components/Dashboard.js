import React, { useState } from 'react';
import { FaFilePdf, FaTrash, FaCalendar, FaFileAlt, FaSpinner, FaChartLine } from 'react-icons/fa';
import api from '../services/api';
import './Dashboard.css';

const Dashboard = ({ documents, summaries, onDocumentDeleted, loading }) => {
  const [deleting, setDeleting] = useState(null);

  const handleDelete = async (documentId) => {
    if (!window.confirm('Are you sure you want to delete this document?')) {
      return;
    }

    setDeleting(documentId);
    try {
      await api.delete(`/api/documents/${documentId}`);
      onDocumentDeleted();
    } catch (error) {
      console.error('Error deleting document:', error);
      alert('Failed to delete document');
    } finally {
      setDeleting(null);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  return (
    <div className="dashboard-modern">
      <div className="dashboard-header">
        <div>
          <h1 className="dashboard-title">RAG-Ex Dashboard</h1>
          <p className="dashboard-subtitle">Retrieval-Augmented Generation Explainability Framework for LLMs</p>
        </div>
      </div>

      <div className="project-abstract-card">
        <h2 className="project-abstract-title">Project Title: RAG-Ex: Retrieval-Augmented Generation Explainability Framework for LLMs</h2>
        <h3 className="project-abstract-subtitle">Abstract</h3>
        <p className="project-abstract-text">
          Large Language Models (LLMs) enhanced with Retrieval-Augmented Generation (RAG) have shown significant improvements in accuracy by grounding responses in external knowledge sources. However, these systems often lack transparency, making it difficult for users to understand how retrieved documents influence the generated outputs. RAG-Ex is an explainability framework designed to improve transparency, trust, and interpretability in RAG-based LLM systems.
        </p>
        <p className="project-abstract-text">
          The proposed framework tracks and analyzes the complete RAG pipeline, including query processing, document retrieval, relevance scoring, and response generation. RAG-Ex highlights which retrieved documents, passages, or chunks contributed to specific parts of the generated answer. Explainability techniques such as attention visualization, similarity scoring, and evidence attribution are applied to map generated tokens back to their source documents.
        </p>
        <p className="project-abstract-text">
          The framework provides an interactive dashboard that displays retrieved context, confidence scores, and explanation summaries, enabling users to verify factual grounding and identify potential hallucinations. RAG-Ex supports use cases in enterprise knowledge systems, healthcare, legal research, and education, where explainability and accountability are critical. By making RAG-based LLMs more transparent and interpretable, this project enhances user trust and promotes responsible deployment of generative AI systems.
        </p>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon documents">
            <FaFilePdf />
          </div>
          <div className="stat-content">
            <h3 className="stat-value">{documents.length}</h3>
            <p className="stat-label">Documents</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon summaries">
            <FaFileAlt />
          </div>
          <div className="stat-content">
            <h3 className="stat-value">{summaries.length}</h3>
            <p className="stat-label">Summaries</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon chunks">
            <FaChartLine />
          </div>
          <div className="stat-content">
            <h3 className="stat-value">
              {documents.reduce((sum, doc) => sum + (doc.chunk_count || 0), 0)}
            </h3>
            <p className="stat-label">Total Chunks</p>
          </div>
        </div>
      </div>

      <div className="dashboard-section">
        <div className="section-header">
          <h2 className="section-title">Recent Documents</h2>
          <span className="section-count">{documents.length} total</span>
        </div>
        {loading ? (
          <div className="loading-container">
            <FaSpinner className="spinner-icon" />
            <p>Loading documents...</p>
          </div>
        ) : documents.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon-wrapper">
              <FaFilePdf className="empty-icon" />
            </div>
            <h3>No documents yet</h3>
            <p>Upload your first research paper to get started</p>
          </div>
        ) : (
          <div className="documents-grid">
            {documents.map((doc) => (
              <div key={doc.document_id} className="document-card-modern">
                <div className="document-header">
                  <div className="document-icon-wrapper">
                    <FaFilePdf className="document-icon" />
                  </div>
                  <div className="document-info">
                    <h3 className="document-title">{doc.title || doc.filename}</h3>
                    <p className="document-filename">{doc.filename}</p>
                  </div>
                </div>
                <div className="document-details">
                  <div className="document-detail-item">
                    <FaCalendar className="detail-icon" />
                    <span>{formatDate(doc.upload_date)}</span>
                  </div>
                  <div className="document-detail-item">
                    <FaFileAlt className="detail-icon" />
                    <span>{doc.chunk_count || 0} chunks</span>
                  </div>
                </div>
                <button
                  className="btn-delete"
                  onClick={() => handleDelete(doc.document_id)}
                  disabled={deleting === doc.document_id}
                >
                  {deleting === doc.document_id ? (
                    <FaSpinner className="spinner-icon-small" />
                  ) : (
                    <FaTrash />
                  )}
                  Delete
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {summaries.length > 0 && (
        <div className="dashboard-section">
          <div className="section-header">
            <h2 className="section-title">Recent Summaries</h2>
            <span className="section-count">{summaries.length} total</span>
          </div>
          <div className="summaries-grid">
            {summaries.slice(0, 6).map((summary) => (
              <div key={summary.summary_id} className="summary-card-modern">
                <div className="summary-header">
                  <FaFileAlt className="summary-icon" />
                  <span className="summary-type-badge">
                    {summary.metadata?.type || 'general'}
                  </span>
                </div>
                <p className="summary-preview">{summary.preview}</p>
                <div className="summary-footer">
                  <FaCalendar className="footer-icon" />
                  <span>{formatDate(summary.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
