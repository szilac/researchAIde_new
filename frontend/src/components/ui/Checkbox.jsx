import React from 'react';
import PropTypes from 'prop-types';
import { cn } from '../../utils/cn';
import { Check } from 'lucide-react'; // Reusing lucide-react

/**
 * A checkbox component for selecting items.
 */
const Checkbox = React.forwardRef(
  ({ className, id, checked, onChange, label, disabled, ...props }, ref) => {
    // We need an internal state if the component is used uncontrolled,
    // but typically it will be controlled via `checked` and `onChange` props.
    // For simplicity here, assuming controlled usage.
    
    // Generate a unique ID if none is provided, for accessibility
    const internalId = id || React.useId();

    return (
      <div className={cn("flex items-center space-x-2", className)}>
        <button
          ref={ref}
          id={internalId}
          type="button" // Use button role for better accessibility and styling control
          role="checkbox"
          aria-checked={checked}
          disabled={disabled}
          onClick={() => !disabled && onChange && onChange(!checked)} // Toggle checked state
          className={cn(
            'peer h-4 w-4 shrink-0 rounded-sm border border-primary ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
            'data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground', // Custom attribute for styling checked state
            className
          )}
          data-state={checked ? 'checked' : 'unchecked'} // Use data attribute for styling
          {...props}
        >
          <Check 
            className={cn(
              "h-4 w-4",
              checked ? "opacity-100" : "opacity-0" // Show/hide check icon
            )}
            strokeWidth={3} // Make check thicker
          />
        </button>
        {label && (
          <label
            htmlFor={internalId}
            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
          >
            {label}
          </label>
        )}
      </div>
    );
  }
);
Checkbox.displayName = 'Checkbox';

Checkbox.propTypes = {
  /** Additional classes for the container div. */
  className: PropTypes.string,
  /** Unique ID for the checkbox, linking label and input. */
  id: PropTypes.string,
  /** Whether the checkbox is checked. (Controlled component) */
  checked: PropTypes.bool.isRequired,
  /** Function called when the checked state changes. Receives the new boolean state. */
  onChange: PropTypes.func.isRequired,
  /** Optional label text to display next to the checkbox. */
  label: PropTypes.string,
  /** Whether the checkbox is disabled. */
  disabled: PropTypes.bool,
};

export { Checkbox };
