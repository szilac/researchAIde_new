import React from 'react';
import ResearchDirectionCard from './ResearchDirectionCard';

// Define the expected props, especially for researchDirections
interface ResearchDirection {
  id: string;
  title: string;
  summary: string;
  papers: Array<{
    id: string;
    title: string;
    summary: string;
    // Add other relevant fields for a research direction
  }>;
  // Add other relevant fields for a research direction
}

interface ResearchDirectionsReportViewProps {
  researchDirections: ResearchDirection[];
}

const ResearchDirectionsReportView: React.FC<ResearchDirectionsReportViewProps> = ({ researchDirections }) => {
  if (!researchDirections || researchDirections.length === 0) {
    return <p className="p-4 text-gray-500">No research directions to display.</p>;
  }

  return (
    <div className="research-directions-report-view p-4">
      {/* Layout will be handled by Tailwind classes here - flex/grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"> {/* Increased gap */}
        {researchDirections.map((direction) => (
          <ResearchDirectionCard key={direction.id} researchDirection={direction} />
        ))}
      </div>
    </div>
  );
};

export default ResearchDirectionsReportView; 