import React, { useState } from 'react';
import PaperSummaryDisplay from './PaperSummaryDisplay';
// import { Button } from '@/components/ui/button'; // Example: if you have a UI button

// Define the expected props
interface Paper {
  id: string;
  title: string;
  summary: string;
  // Add other relevant fields for a paper
}

interface ResearchDirection {
  id: string;
  title: string;
  summary: string;
  papers: Paper[];
}

interface ResearchDirectionCardProps {
  researchDirection: ResearchDirection;
}

const ResearchDirectionCard: React.FC<ResearchDirectionCardProps> = ({ researchDirection }) => {
  const [papersVisible, setPapersVisible] = useState(false);

  const togglePapersVisibility = () => {
    setPapersVisible(!papersVisible);
  };

  if (!researchDirection) {
    return null; // Or some fallback UI
  }

  return (
    <div className="research-direction-card bg-white border border-gray-200 rounded-lg p-5 shadow-sm flex flex-col h-full"> {/* Basic card styling, added flex for height */}
      <div className="flex-grow">
        <h2 className="text-lg font-semibold text-gray-800 mb-2">{researchDirection.title}</h2>
        <p className="text-sm text-gray-600 mb-4 leading-relaxed">{researchDirection.summary}</p>
      </div>
      
      <button 
        onClick={togglePapersVisibility}
        className="mt-auto text-indigo-600 hover:text-indigo-800 text-sm font-medium py-2 px-3 rounded-md border border-indigo-200 hover:bg-indigo-50 transition-colors duration-150 self-start" // Improved button styling
      >
        {papersVisible ? 'Hide' : 'Show'} Paper Summaries ({researchDirection.papers?.length || 0})
      </button>

      {papersVisible && (
        <div className="paper-summaries-section mt-4 pt-4 border-t border-gray-200">
          {researchDirection.papers && researchDirection.papers.length > 0 ? (
            <>
              <h3 className="text-base font-medium text-gray-700 mb-3">Associated Papers:</h3>
              {researchDirection.papers.map((paper) => (
                <PaperSummaryDisplay key={paper.id} paper={paper} />
              ))}
            </>
          ) : (
            <p className="text-xs text-gray-500 mt-2">No papers associated with this direction.</p>
          )}
        </div>
      )}
    </div>
  );
};

export default ResearchDirectionCard; 