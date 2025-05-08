import React from 'react';
import PropTypes from 'prop-types';
import { cn } from '../../utils/cn';

/**
 * A progress bar component to indicate loading or completion status.
 */
const Progress = React.forwardRef(
  ({ className, value, max = 100, indicatorClassName, ...props }, ref) => {
    const percentage = max > 0 ? (value / max) * 100 : 0;

    return (
      <div
        ref={ref}
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin="0"
        aria-valuemax={max}
        className={cn(
          'relative h-4 w-full overflow-hidden rounded-full bg-secondary',
          className
        )}
        {...props}
      >
        <div
          className={cn('h-full w-full flex-1 bg-primary transition-all', indicatorClassName)}
          style={{ transform: `translateX(-${100 - percentage}%)` }}
        />
      </div>
    );
  }
);
Progress.displayName = 'Progress';

Progress.propTypes = {
  /** Additional classes for the progress bar container. */
  className: PropTypes.string,
  /** Current value of the progress. */
  value: PropTypes.number.isRequired,
  /** Maximum value of the progress. Defaults to 100. */
  max: PropTypes.number,
  /** Additional classes for the progress indicator element. */
  indicatorClassName: PropTypes.string,
};

export { Progress };
