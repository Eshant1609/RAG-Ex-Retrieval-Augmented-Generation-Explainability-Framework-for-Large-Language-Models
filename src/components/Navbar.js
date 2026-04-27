import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FaBook, FaUpload, FaSearch, FaFileAlt, FaHome } from 'react-icons/fa';
import './Navbar.css';

const Navbar = () => {
  const location = useLocation();

  const isActive = (path) => {
    return location.pathname === path ? 'active' : '';
  };

  return (
    <nav className="navbar-modern">
      <div className="navbar-container">
        <Link to="/dashboard" className="navbar-brand">
          <div className="brand-icon">
            <FaBook />
          </div>
          <div className="brand-text">
            <span className="brand-name">RAG-Ex</span>
            <span className="brand-tagline">RAG Explainability Framework</span>
          </div>
        </Link>
        <ul className="navbar-links">
          <li>
            <Link to="/dashboard" className={`nav-link ${isActive('/dashboard')}`}>
              <FaHome className="nav-icon" />
              <span>Dashboard</span>
            </Link>
          </li>
          <li>
            <Link to="/upload" className={`nav-link ${isActive('/upload')}`}>
              <FaUpload className="nav-icon" />
              <span>Upload</span>
            </Link>
          </li>
          <li>
            <Link to="/query" className={`nav-link ${isActive('/query')}`}>
              <FaSearch className="nav-icon" />
              <span>Query</span>
            </Link>
          </li>
          <li>
            <Link to="/summaries" className={`nav-link ${isActive('/summaries')}`}>
              <FaFileAlt className="nav-icon" />
              <span>Summaries</span>
            </Link>
          </li>
        </ul>
      </div>
    </nav>
  );
};

export default Navbar;
