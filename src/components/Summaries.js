import React, { useState } from 'react';
import { FaFileAlt, FaDownload, FaTrash, FaCalendar, FaSpinner, FaFolder, FaEye, FaEyeSlash } from 'react-icons/fa';
import api from '../services/api';
import './Summaries.css';

const Summaries = ({ summaries, documents }) => {
  const [selectedSummary, setSelectedSummary] = useState(null);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [summaryDetails, setSummaryDetails] = useState(null);

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleViewSummary = async (summaryId) => {
    if (selectedSummary === summaryId && summaryDetails) {
      setSelectedSummary(null);
      setSummaryDetails(null);
      return;
    }

    setSelectedSummary(summaryId);
    setLoadingSummary(true);

    try {
      const summary = summaries.find(s => s.summary_id === summaryId);
      if (summary) {
        try {
          const response = await api.get(`/api/summaries/${summaryId}`);
          if (response.data.success) {
            setSummaryDetails(response.data.summary);
          } else {
            setSummaryDetails(summary);
          }
        } catch (error) {
          setSummaryDetails(summary);
        }
      }
    } catch (error) {
      console.error('Error loading summary:', error);
      const summary = summaries.find(s => s.summary_id === summaryId);
      setSummaryDetails(summary);
    } finally {
      setLoadingSummary(false);
    }
  };

  const handleExport = async (summaryId, format) => {
    try {
      const response = await api.post(
        '/api/export',
        {
          type: format,
          summary_id: summaryId
        },
        {
          responseType: 'blob'
        }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `summary_${summaryId.slice(0, 8)}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Export error:', error);
      alert('Failed to export summary');
    }
  };

  return (
    <div className="summaries-container-modern">
      <div className="summaries-header">
        <h1 className="summaries-title">Generated Summaries</h1>
        <p className="summaries-subtitle">View and manage your research summaries</p>
      </div>

      {summaries.length === 0 ? (
        <div className="card-modern empty-state-card">
          <div className="empty-state-content">
            <div className="empty-icon-wrapper-large">
              <FaFileAlt className="empty-icon-large" />
            </div>
            <h3>No summaries generated yet</h3>
            <p>Generate summaries using the Query page</p>
          </div>
        </div>
      ) : (
        <div className="summaries-layout">
          <div className="summaries-list-section">
            <div className="list-section-header">
              <h2 className="list-section-title">All Summaries</h2>
              <span className="list-section-count">{summaries.length} total</span>
            </div>
            <div className="summaries-list-modern">
              {summaries.map((summary) => (
                <div
                  key={summary.summary_id}
                  className={`summary-item-modern ${selectedSummary === summary.summary_id ? 'active' : ''}`}
                  onClick={() => handleViewSummary(summary.summary_id)}
                >
                  <div className="summary-item-header">
                    <div className="summary-item-icon-wrapper">
                      <FaFileAlt />
                    </div>
                    <div className="summary-item-info">
                      <h4 className="summary-item-title">Summary {summary.summary_id.slice(0, 8)}</h4>
                      <p className="summary-item-date">
                        <FaCalendar /> {formatDate(summary.created_at)}
                      </p>
                    </div>
                  </div>
                  <p className="summary-item-preview">{summary.preview}</p>
                  {summary.metadata?.type && (
                    <span className="summary-type-badge-modern">{summary.metadata.type}</span>
                  )}
                  <div className="summary-item-actions">
                    {selectedSummary === summary.summary_id ? (
                      <FaEyeSlash className="action-icon" />
                    ) : (
                      <FaEye className="action-icon" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {selectedSummary && (
            <div className="summary-detail-section slide-up">
              {loadingSummary ? (
                <div className="card-modern loading-card">
                  <FaSpinner className="spinner-large" />
                  <p>Loading summary...</p>
                </div>
              ) : summaryDetails ? (
                <div className="card-modern summary-detail-card-modern">
                  <div className="summary-detail-header-modern">
                    <div>
                      <h2 className="detail-title">Summary Details</h2>
                      <p className="detail-meta">
                        Created: {formatDate(summaryDetails.created_at || summaryDetails.metadata?.created_at)}
                        {summaryDetails.metadata?.type && (
                          <span className="detail-type-badge">{summaryDetails.metadata.type}</span>
                        )}
                      </p>
                    </div>
                    <div className="detail-actions">
                      <button
                        className="btn-export"
                        onClick={() => handleExport(selectedSummary, 'markdown')}
                        title="Export as Markdown"
                      >
                        <FaDownload /> MD
                      </button>
                      <button
                        className="btn-export"
                        onClick={() => handleExport(selectedSummary, 'json')}
                        title="Export as JSON"
                      >
                        <FaDownload /> JSON
                      </button>
                      <button
                        className="btn-export"
                        onClick={() => handleExport(selectedSummary, 'pdf')}
                        title="Export as PDF"
                      >
                        <FaDownload /> PDF
                      </button>
                    </div>
                  </div>
                  <div className="summary-detail-content-modern">
                    <h3 className="content-section-title">Summary</h3>
                    <div className="summary-text-modern">
                      {(summaryDetails.summary || summaryDetails.preview || '').split('\n').map((paragraph, index) => (
                        <p key={index} className="summary-paragraph">{paragraph}</p>
                      ))}
                    </div>
                    {summaryDetails.metadata?.sources && summaryDetails.metadata.sources.length > 0 && (
                      <div className="summary-detail-sources-modern">
                        <h3 className="content-section-title">Sources</h3>
                        <ul className="sources-list-modern">
                          {summaryDetails.metadata.sources.map((source, index) => (
                            <li key={index} className="source-item-modern">
                              <FaFileAlt className="source-icon-modern" />
                              <div className="source-content">
                                <strong className="source-title">{source.title}</strong>
                                <span className="source-filename">{source.filename}</span>
                              </div>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {summaryDetails.metadata?.query && (
                      <div className="summary-detail-query-modern">
                        <h3 className="content-section-title">Original Query</h3>
                        <p className="query-text">{summaryDetails.metadata.query}</p>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="card-modern">
                  <p>Summary not found</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Summaries;
