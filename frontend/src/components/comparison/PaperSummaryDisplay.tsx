import React from 'react';

// Define the expected props
interface Paper {
  id: string;
  title: string;
  summary: string;
  // Add other relevant fields for a paper, e.g., authors, publicationDate, url
}

interface PaperSummaryDisplayProps {
  paper: Paper;
}

const PaperSummaryDisplay: React.FC<PaperSummaryDisplayProps> = ({ paper }) => {
  if (!paper) {
    return null; // Or some fallback UI
  }

  return (
    <div className="paper-summary-display mb-4 p-3 border-l-4 border-indigo-200 bg-indigo-50 rounded-r-md">
      <h4 className="text-sm font-semibold text-indigo-700 mb-1">{paper.title}</h4>
      <p className="text-xs text-gray-700 leading-snug">{paper.summary}</p>
      {/* Optionally, display other paper details here */}
    </div>
  );
};

export default PaperSummaryDisplay; 