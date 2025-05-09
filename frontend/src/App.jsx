import React, { useState, useMemo, useCallback } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Header from './components/Header';
import Footer from './components/Footer';
import HomePage from './pages/HomePage';
import AboutPage from './pages/AboutPage';
import ResearchSetupPage from './pages/ResearchSetupPage';
import WorkflowDisplayPage from './pages/WorkflowDisplayPage';
import ShortlistTestPage from './pages/ShortlistTestPage';
import ResearchReportDisplayPage from './pages/ResearchReportDisplayPage';
import AssessmentsPage from './pages/AssessmentsPage';
import ExportPage from './pages/ExportPage';
import ResearchInterfaceLayout from './layouts/ResearchInterfaceLayout';
import { useTheme } from './hooks/useTheme';
import { PaperListControls } from './components/PaperListControls';
import { PaperCard } from './components/PaperCard';
import { filterPapersByKeyword, sortPapers } from './utils/filtering';
import './App.css';

// Mock Data (as used in filtering.test.js)
const mockPapersData = [
  { id: '1', title: 'Paper A about AI', authors: ['Author X'], date: '2023-01-15', relevance: 90, abstract: 'An abstract discussing artificial intelligence.' },
  { id: '2', title: 'Paper B on Machine Learning', authors: ['Author Y', 'Author Z'], date: '2022-11-20', relevance: 85, abstract: 'Focuses on ML techniques.' },
  { id: '3', title: 'Another AI Paper', authors: ['Author X'], date: '2024-03-10', relevance: 95, abstract: 'More details on AI progress.' },
  { id: '4', title: 'Data Science Methods', authors: ['Author A'], date: '2023-05-01', relevance: 80, abstract: 'Discusses data analysis.' },
  { id: '5', title: 'Paper without Author', date: '2021-01-01', relevance: 70, abstract: 'Old paper.' },
  { id: '6', title: 'Machine Concepts', authors: ['Author B'], date: '2023-12-31', relevance: 88, abstract: 'Deep dive into machines.' },
];

function App() {
  const { theme } = useTheme();
  const [filters, setFilters] = useState({
    searchTerm: '',
    sortBy: 'relevance', 
    sortOrder: 'desc',
  });

  const [selectedPaperIds, setSelectedPaperIds] = useState(() => new Set());

  const handleFilterChange = useCallback((newFilters) => {
    setFilters(newFilters);
  }, []);

  // Apply filtering and sorting
  const filteredAndSortedPapers = useMemo(() => {
    const filtered = filterPapersByKeyword(mockPapersData, filters.searchTerm);
    return sortPapers(filtered, filters.sortBy, filters.sortOrder);
  }, [filters]);

  const handleSelectionChange = useCallback((paperId, isSelected) => {
    setSelectedPaperIds(prevSelectedIds => {
      const newSelectedIds = new Set(prevSelectedIds);
      if (isSelected) {
        newSelectedIds.add(paperId);
      } else {
        newSelectedIds.delete(paperId);
      }
      return newSelectedIds;
    });
  }, []);

  const handleSelectAllChange = useCallback((selectAll) => {
    setSelectedPaperIds(() => {
      if (selectAll) {
        // Select all *currently filtered* papers
        return new Set(filteredAndSortedPapers.map(p => p.id));
      } else {
        // Deselect all
        return new Set();
      }
    });
  }, [filteredAndSortedPapers]); // Dependency needed to select only filtered items

  return (
    <div className={`app-container ${theme}`}>
      <Header />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/setup" element={<ResearchSetupPage />} />
          <Route path="/workflow/:workflowId" element={<WorkflowDisplayPage />} />
          <Route path="/shortlist-test" element={<ShortlistTestPage />} />
          <Route path="/exploration" element={<ResearchInterfaceLayout />}>
            <Route index element={<Navigate to="report" replace />} />
            <Route path="report" element={<ResearchReportDisplayPage />} />
            <Route path="assessments" element={<AssessmentsPage />} />
            <Route path="export" element={<ExportPage />} />
          </Route>
        </Routes>
      </main>
      <Footer />
    </div>
  );
}

export default App;
