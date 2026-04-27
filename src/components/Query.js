import React, { useState, useEffect } from 'react';
import { FaSearch, FaSpinner, FaFileAlt, FaDownload, FaCheckCircle, FaFolder, FaFolderOpen, FaChevronDown, FaChevronUp } from 'react-icons/fa';
import api from '../services/api';
import './Query.css';

const Query = ({ documents: initialDocuments, folders: initialFolders, onSummaryCreated }) => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [summaryType, setSummaryType] = useState('general');
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryResult, setSummaryResult] = useState(null);
  const [documents, setDocuments] = useState(initialDocuments || []);
  const [folders, setFolders] = useState(initialFolders || []);
  const [selectedDocuments, setSelectedDocuments] = useState([]);
  const [selectedFolders, setSelectedFolders] = useState([]);
  const [showDocumentSelector, setShowDocumentSelector] = useState(false);

  // Reload documents and folders when component mounts to ensure fresh data
  useEffect(() => {
    loadDocuments();
    loadFolders();
  }, []);

  // Update when props change
  useEffect(() => {
    if (initialDocuments) {
      setDocuments(initialDocuments);
    }
  }, [initialDocuments]);

  useEffect(() => {
    if (initialFolders) {
      setFolders(initialFolders);
    }
  }, [initialFolders]);

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

  const handleQuery = async (e) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    setLoading(true);
    setResponse(null);

    try {
      const payload = {
        query: query.trim(),
        top_k: 5
      };

      if (selectedDocuments.length > 0) {
        payload.document_ids = selectedDocuments;
      }
      if (selectedFolders.length > 0) {
        payload.folder_ids = selectedFolders;
      }

      const result = await api.post('/api/query', payload, { timeout: 300000 }); // 5 minutes timeout

      if (result.data.success) {
        setResponse({
          response: result.data.response || result.data.answer || 'No response generated',
          sources: result.data.sources || [],
          metadata: result.data.metadata || {}
        });
      } else {
        setResponse({
          response: 'Error: ' + (result.data.error || 'Failed to process query'),
          sources: []
        });
      }
    } catch (error) {
      console.error('Query error:', error);
      setResponse({
        response: error.response?.data?.error || 'Failed to process query. Please try again.',
        sources: []
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSummarize = async () => {
    if (summaryLoading) return;

    setSummaryLoading(true);
    setSummaryResult(null);

    try {
      const payload = {
        type: summaryType
      };

      if (query.trim()) {
        payload.query = query.trim();
      }

      if (selectedDocuments.length > 0) {
        payload.document_ids = selectedDocuments;
      }
      if (selectedFolders.length > 0) {
        payload.folder_ids = selectedFolders;
      }

      if (!payload.query && !payload.document_ids && !payload.folder_ids) {
        alert('Please select documents/folders or enter a query');
        setSummaryLoading(false);
        return;
      }

      const result = await api.post('/api/summarize', payload, { timeout: 300000 }); // 5 minutes timeout

      if (result.data.success) {
        setSummaryResult(result.data);
        onSummaryCreated();
      } else {
        alert('Error: ' + (result.data.error || 'Failed to generate summary'));
      }
    } catch (error) {
      console.error('Summary error:', error);
      alert(error.response?.data?.error || 'Failed to generate summary. Please try again.');
    } finally {
      setSummaryLoading(false);
    }
  };

  const handleExport = async (format) => {
    if (!summaryResult) return;

    try {
      const result = await api.post(
        '/api/export',
        {
          type: format,
          summary_id: summaryResult.summary_id
        },
        {
          responseType: 'blob'
        }
      );

      const url = window.URL.createObjectURL(new Blob([result.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `summary_${summaryResult.summary_id.slice(0, 8)}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Export error:', error);
      alert('Failed to export summary');
    }
  };

  const toggleDocument = (docId) => {
    setSelectedDocuments(prev =>
      prev.includes(docId)
        ? prev.filter(id => id !== docId)
        : [...prev, docId]
    );
  };

  const toggleFolder = (folderId) => {
    setSelectedFolders(prev =>
      prev.includes(folderId)
        ? prev.filter(id => id !== folderId)
        : [...prev, folderId]
    );
  };

  const selectAllDocuments = () => {
    setSelectedDocuments(documents.map(doc => doc.document_id));
  };

  const clearSelection = () => {
    setSelectedDocuments([]);
    setSelectedFolders([]);
  };

  return (
    <div className="query-container-modern">
      <div className="query-header">
        <h1 className="query-title">RAG-Ex Query + Explainability</h1>
        <p className="query-subtitle">Ask grounded questions and inspect evidence, relevance, and attribution</p>
      </div>

      {documents.length === 0 && folders.length === 0 && (
        <div className="card-modern alert-info-card">
          <div className="alert-info-content">
            <FaFileAlt className="alert-info-icon" />
            <p>No documents uploaded yet. Please upload some research papers first.</p>
          </div>
        </div>
      )}

      <div className="card-modern context-selector-card-modern">
        <div 
          className="context-selector-header-modern"
          onClick={() => setShowDocumentSelector(!showDocumentSelector)}
        >
          <div className="header-left">
            <FaFolderOpen className="header-icon" />
            <div>
              <h3 className="header-title">Select Context</h3>
              <p className="header-subtitle">Choose specific documents or folders to query</p>
            </div>
          </div>
          <button className="toggle-btn">
            {showDocumentSelector ? <FaChevronUp /> : <FaChevronDown />}
          </button>
        </div>
        
        {showDocumentSelector && (
          <div className="context-selector-content-modern">
            <div className="selector-section-modern">
              <h4 className="selector-section-title">
                <FaFolder className="section-title-icon" />
                Folders
              </h4>
              {folders.length === 0 ? (
                <p className="empty-selector-message">No folders available</p>
              ) : (
                <div className="folder-selector-modern">
                  {folders.map(folder => (
                    <label key={folder.folder_id} className={`selector-item-modern folder-item-modern ${selectedFolders.includes(folder.folder_id) ? 'selected' : ''}`}>
                      <input
                        type="checkbox"
                        checked={selectedFolders.includes(folder.folder_id)}
                        onChange={() => toggleFolder(folder.folder_id)}
                        className="checkbox-modern"
                      />
                      <FaFolder className="item-icon" />
                      <div className="item-content">
                        <strong className="item-title">{folder.name}</strong>
                        <span className="item-subtitle">{folder.document_count || 0} documents</span>
                      </div>
                    </label>
                  ))}
                </div>
              )}
            </div>

            <div className="selector-section-modern">
              <div className="selector-section-header-modern">
                <h4 className="selector-section-title">
                  <FaFileAlt className="section-title-icon" />
                  Individual Documents
                </h4>
                <div className="selector-actions-modern">
                  <button className="action-btn" onClick={selectAllDocuments}>Select All</button>
                  <button className="action-btn" onClick={clearSelection}>Clear</button>
                </div>
              </div>
              {documents.length === 0 ? (
                <p className="empty-selector-message">No documents available</p>
              ) : (
                <div className="document-selector-modern">
                  {documents.map(doc => (
                    <label key={doc.document_id} className={`selector-item-modern document-item-modern ${selectedDocuments.includes(doc.document_id) ? 'selected' : ''}`}>
                      <input
                        type="checkbox"
                        checked={selectedDocuments.includes(doc.document_id)}
                        onChange={() => toggleDocument(doc.document_id)}
                        className="checkbox-modern"
                      />
                      <FaFileAlt className="item-icon" />
                      <div className="item-content">
                        <strong className="item-title">{doc.title || doc.filename}</strong>
                        <span className="item-subtitle">{doc.filename}</span>
                      </div>
                    </label>
                  ))}
                </div>
              )}
            </div>

            {(selectedDocuments.length > 0 || selectedFolders.length > 0) && (
              <div className="selection-summary-modern">
                <strong>Selected:</strong> {selectedFolders.length} folder(s), {selectedDocuments.length} document(s)
              </div>
            )}
          </div>
        )}
      </div>

      <div className="card-modern query-card-modern">
        <form onSubmit={handleQuery} className="query-form-modern">
          <div className="input-group-modern">
            <label className="input-label-modern">Enter your question</label>
            <textarea
              className="textarea-modern"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., What are the main findings of the research? What methodology was used?"
              rows="4"
              disabled={loading || (documents.length === 0 && folders.length === 0)}
            />
          </div>
          <button
            type="submit"
            className="btn-primary btn-large-modern"
            disabled={!query.trim() || loading || (documents.length === 0 && folders.length === 0)}
          >
            {loading ? (
              <>
                <FaSpinner className="spinner-icon" /> Processing...
              </>
            ) : (
              <>
                <FaSearch /> Search
              </>
            )}
          </button>
        </form>
      </div>

      {response && (
        <div className="card-modern response-card-modern slide-up">
          <div className="response-header-modern">
            <h3 className="response-title">Answer</h3>
          </div>
          <div className="response-content-modern">
            <p className="response-text">{response.response || response.answer}</p>
          </div>
          {response.sources && response.sources.length > 0 && (
            <div className="sources-section-modern">
              <h4 className="sources-title">Sources</h4>
              <ul className="sources-list-modern">
                {response.sources.map((source, index) => (
                  <li key={index} className="source-item-modern">
                    <FaFileAlt className="source-icon-modern" />
                    <div className="source-content">
                      <strong className="source-title">{source.title}</strong>
                      <span className="source-filename">{source.filename}</span>
                      {typeof source.max_relevance_score === 'number' && (
                        <span className="source-score">Max relevance: {(source.max_relevance_score * 100).toFixed(1)}%</span>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {response.metadata?.explainability && (
            <div className="explainability-section-modern">
              <h4 className="explainability-title">RAG-Ex Explainability</h4>
              <p className="explainability-summary">{response.metadata.explainability.explanation_summary}</p>

              <div className="explainability-metrics-grid">
                <div className="explainability-metric-card">
                  <span className="metric-label">Confidence</span>
                  <span className="metric-value">{((response.metadata.explainability.confidence_score || 0) * 100).toFixed(1)}%</span>
                </div>
                <div className="explainability-metric-card">
                  <span className="metric-label">Retrieved Chunks</span>
                  <span className="metric-value">{response.metadata.explainability.retrieved_chunk_count || 0}</span>
                </div>
                <div className="explainability-metric-card">
                  <span className="metric-label">Source Documents</span>
                  <span className="metric-value">{response.metadata.explainability.document_count || 0}</span>
                </div>
              </div>

              {response.metadata.explainability.document_contributions?.length > 0 && (
                <div className="explainability-block">
                  <h5 className="explainability-block-title">Document Contributions</h5>
                  <ul className="explainability-list">
                    {response.metadata.explainability.document_contributions.map((doc, index) => (
                      <li key={`${doc.document_id || doc.filename}-${index}`} className="explainability-item">
                        <div className="explainability-item-header">
                          <strong>{doc.filename}</strong>
                          <span>{(doc.max_relevance_score * 100).toFixed(1)}%</span>
                        </div>
                        <p className="explainability-item-subtext">
                          {doc.supporting_chunks} supporting chunk(s), avg relevance {(doc.avg_relevance_score * 100).toFixed(1)}%
                        </p>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {response.metadata.explainability.evidence_chunks?.length > 0 && (
                <div className="explainability-block">
                  <h5 className="explainability-block-title">Retrieved Evidence Chunks</h5>
                  <ul className="explainability-list">
                    {response.metadata.explainability.evidence_chunks.map((chunk, index) => (
                      <li key={`${chunk.document_id || chunk.filename}-${chunk.chunk_index}-${index}`} className="explainability-item">
                        <div className="explainability-item-header">
                          <strong>{chunk.filename} {Number.isInteger(chunk.chunk_index) ? `(chunk ${chunk.chunk_index + 1})` : ''}</strong>
                          <span>{(chunk.relevance_score * 100).toFixed(1)}%</span>
                        </div>
                        <p className="explainability-item-subtext">{chunk.chunk_preview}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {response.metadata.explainability.answer_attribution?.length > 0 && (
                <div className="explainability-block">
                  <h5 className="explainability-block-title">Answer Attribution</h5>
                  <ul className="explainability-list">
                    {response.metadata.explainability.answer_attribution.map((item, index) => (
                      <li key={`${item.filename}-${item.chunk_index}-${index}`} className="explainability-item">
                        <p className="attribution-segment">{item.answer_segment}</p>
                        <p className="explainability-item-subtext">
                          Attributed to <strong>{item.filename}</strong> {Number.isInteger(item.chunk_index) ? `(chunk ${item.chunk_index + 1})` : ''} ·
                          relevance {(item.relevance_score * 100).toFixed(1)}% ·
                          attribution {(item.attribution_score * 100).toFixed(1)}%
                        </p>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <div className="card-modern summary-card-modern">
        <div className="summary-header-modern">
          <div>
            <h3 className="summary-title">Generate Summary</h3>
            <p className="summary-subtitle">Create contextual summaries from selected documents/folders or query</p>
          </div>
        </div>
        <div className="summary-controls-modern">
          <div className="input-group-modern">
            <label className="input-label-modern">Summary Type</label>
            <select
              className="input-modern"
              value={summaryType}
              onChange={(e) => setSummaryType(e.target.value)}
              disabled={summaryLoading}
            >
              <option value="general">General Summary</option>
              <option value="detailed">Detailed Summary</option>
              <option value="key_points">Key Points</option>
            </select>
          </div>
          <button
            className="btn-primary btn-large-modern"
            onClick={handleSummarize}
            disabled={summaryLoading || (!query.trim() && selectedDocuments.length === 0 && selectedFolders.length === 0)}
          >
            {summaryLoading ? (
              <>
                <FaSpinner className="spinner-icon" /> Generating...
              </>
            ) : (
              <>
                <FaFileAlt /> Generate Summary
              </>
            )}
          </button>
        </div>
      </div>

      {summaryResult && (
        <div className="card-modern summary-result-card-modern slide-up">
          <div className="summary-result-header-modern">
            <div>
              <h3 className="summary-result-title">Generated Summary</h3>
              <p className="summary-meta-modern">Type: {summaryResult.metadata?.type || 'general'}</p>
            </div>
            <div className="export-buttons-modern">
              <button
                className="btn-export"
                onClick={() => handleExport('markdown')}
                title="Export as Markdown"
              >
                <FaDownload /> MD
              </button>
              <button
                className="btn-export"
                onClick={() => handleExport('json')}
                title="Export as JSON"
              >
                <FaDownload /> JSON
              </button>
              <button
                className="btn-export"
                onClick={() => handleExport('pdf')}
                title="Export as PDF"
              >
                <FaDownload /> PDF
              </button>
            </div>
          </div>
          <div className="summary-result-content-modern">
            <div className="summary-text-modern">
              {summaryResult.summary.split('\n').map((paragraph, index) => (
                <p key={index} className="summary-paragraph">{paragraph}</p>
              ))}
            </div>
            {summaryResult.sources && summaryResult.sources.length > 0 && (
              <div className="summary-sources-modern">
                <h4 className="sources-title">Sources</h4>
                <ul className="sources-list-modern">
                  {summaryResult.sources.map((source, index) => (
                    <li key={index} className="source-item-modern">
                      <FaFileAlt className="source-icon-modern" />
                      <div className="source-content">
                        <strong className="source-title">{source.title}</strong>
                        <span className="source-filename">{source.filename}</span>
                        {typeof source.max_relevance_score === 'number' && (
                          <span className="source-score">Max relevance: {(source.max_relevance_score * 100).toFixed(1)}%</span>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {summaryResult.metadata?.explainability && (
              <div className="explainability-section-modern">
                <h4 className="explainability-title">RAG-Ex Explainability (Summary)</h4>
                <p className="explainability-summary">{summaryResult.metadata.explainability.explanation_summary}</p>

                <div className="explainability-metrics-grid">
                  <div className="explainability-metric-card">
                    <span className="metric-label">Confidence</span>
                    <span className="metric-value">{((summaryResult.metadata.explainability.confidence_score || 0) * 100).toFixed(1)}%</span>
                  </div>
                  <div className="explainability-metric-card">
                    <span className="metric-label">Retrieved Chunks</span>
                    <span className="metric-value">{summaryResult.metadata.explainability.retrieved_chunk_count || 0}</span>
                  </div>
                  <div className="explainability-metric-card">
                    <span className="metric-label">Source Documents</span>
                    <span className="metric-value">{summaryResult.metadata.explainability.document_count || 0}</span>
                  </div>
                </div>

                {summaryResult.metadata.explainability.document_contributions?.length > 0 && (
                  <div className="explainability-block">
                    <h5 className="explainability-block-title">Document Contributions</h5>
                    <ul className="explainability-list">
                      {summaryResult.metadata.explainability.document_contributions.map((doc, index) => (
                        <li key={`${doc.document_id || doc.filename}-${index}`} className="explainability-item">
                          <div className="explainability-item-header">
                            <strong>{doc.filename}</strong>
                            <span>{(doc.max_relevance_score * 100).toFixed(1)}%</span>
                          </div>
                          <p className="explainability-item-subtext">
                            {doc.supporting_chunks} supporting chunk(s), avg relevance {(doc.avg_relevance_score * 100).toFixed(1)}%
                          </p>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {summaryResult.metadata.explainability.evidence_chunks?.length > 0 && (
                  <div className="explainability-block">
                    <h5 className="explainability-block-title">Retrieved Evidence Chunks</h5>
                    <ul className="explainability-list">
                      {summaryResult.metadata.explainability.evidence_chunks.map((chunk, index) => (
                        <li key={`${chunk.document_id || chunk.filename}-${chunk.chunk_index}-${index}`} className="explainability-item">
                          <div className="explainability-item-header">
                            <strong>{chunk.filename} {Number.isInteger(chunk.chunk_index) ? `(chunk ${chunk.chunk_index + 1})` : ''}</strong>
                            <span>{(chunk.relevance_score * 100).toFixed(1)}%</span>
                          </div>
                          <p className="explainability-item-subtext">{chunk.chunk_preview}</p>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
          <div className="summary-success-modern">
            <FaCheckCircle className="success-icon" />
            <span>Summary saved successfully</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default Query;
