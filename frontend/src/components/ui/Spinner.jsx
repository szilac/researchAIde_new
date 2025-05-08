import React from 'react';
import PropTypes from 'prop-types';
import { cn } from '../../utils/cn';
import { Loader2 } from 'lucide-react'; // Use Loader2 icon for a common spinner look

/**
 * A simple spinner component to indicate loading.
 */
const Spinner = ({ className, size = 'default', ...props }) => {
  const sizeClasses = {
    sm: 'h-4 w-4',
    default: 'h-6 w-6',
    lg: 'h-8 w-8',
  };

  return (
    <Loader2
      className={cn('animate-spin text-primary', sizeClasses[size], className)}
      {...props}
    />
  );
};

Spinner.propTypes = {
  /** Additional classes for the spinner icon. */
  className: PropTypes.string,
  /** Size of the spinner. */
  size: PropTypes.oneOf(['sm', 'default', 'lg']),
};

export { Spinner };
