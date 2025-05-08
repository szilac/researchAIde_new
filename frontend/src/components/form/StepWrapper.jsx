import React from 'react';

const StepWrapper = ({
  title = null,
  children,
  className = '',
}) => {
  return (
    <div className={`step-wrapper w-full py-4 ${className}`}>
      {title && (
        <h2 className="text-xl font-semibold mb-4 text-gray-800">
          {title}
        </h2>
      )}
      <div>
        {children}
      </div>
    </div>
  );
};

export default StepWrapper; 