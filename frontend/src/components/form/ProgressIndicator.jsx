import React from 'react';

const ProgressIndicator = ({
  currentStep, // 1-indexed
  totalSteps,
  stepNames = [], // Optional array of names for each step
  className = '',
}) => {
  if (totalSteps <= 0) return null;

  return (
    <div className={`flex items-center justify-between w-full mb-8 ${className}`}>
      {Array.from({ length: totalSteps }, (_, index) => {
        const stepNumber = index + 1;
        const isCompleted = stepNumber < currentStep;
        const isCurrent = stepNumber === currentStep;
        const stepName = stepNames[index] || `Step ${stepNumber}`;

        let circleClasses = 'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ';
        let lineClasses = 'flex-1 h-0.5 '; // Line between circles
        let textClasses = 'text-xs mt-2 text-center ';

        if (isCompleted) {
          circleClasses += 'bg-blue-600 text-white';
          lineClasses += 'bg-blue-600';
          textClasses += 'text-blue-600';
        } else if (isCurrent) {
          circleClasses += 'bg-blue-600 text-white ring-4 ring-blue-200';
          lineClasses += 'bg-gray-300';
          textClasses += 'text-blue-600 font-semibold';
        } else { // Future step
          circleClasses += 'bg-gray-300 text-gray-600';
          lineClasses += 'bg-gray-300';
          textClasses += 'text-gray-500';
        }

        return (
          <React.Fragment key={stepNumber}>
            <div className="flex flex-col items-center">
              <div className={circleClasses}>
                {isCompleted ? (
                  // Checkmark SVG icon (simple one)
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  stepNumber
                )}
              </div>
              {stepNames.length > 0 && <div className={textClasses}>{stepName}</div>}
            </div>
            {stepNumber < totalSteps && (
              <div className={lineClasses} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};

export default ProgressIndicator; 