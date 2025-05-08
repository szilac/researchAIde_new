import React from 'react';

const SelectField = ({
  id,
  label,
  value,
  onChange,
  options = [], // Expects an array of { value: string | number, label: string }
  error = null,
  disabled = false,
  required = false,
  className = '', // For the container div
  selectClassName = '', // For the select element itself
  labelClassName = '', // For the label element
  ...props
}) => {
  const baseSelectStyles = `
    mt-1 block w-full pl-3 pr-10 py-2 text-base border border-gray-300 rounded-md shadow-sm
    focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm
  `;
  const errorSelectStyles = 'border-red-500 focus:ring-red-500 focus:border-red-500';
  const disabledSelectStyles = 'bg-gray-100 cursor-not-allowed';

  const selectStyles = `
    ${baseSelectStyles}
    ${error ? errorSelectStyles : ''}
    ${disabled ? disabledSelectStyles : ''}
    ${selectClassName}
  `.trim().replace(/\s+/g, ' ');

  const baseLabelStyles = 'block text-sm font-medium text-gray-700';
  const labelStyles = `${baseLabelStyles} ${labelClassName}`.trim().replace(/\s+/g, ' ');

  return (
    <div className={`mb-4 ${className}`}>
      {label && (
        <label htmlFor={id} className={labelStyles}>
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      <select
        id={id}
        name={id}
        value={value}
        onChange={onChange}
        disabled={disabled}
        required={required}
        className={selectStyles}
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={error ? `${id}-error` : undefined}
        {...props}
      >
        {/* Optionally add a default placeholder option */}
        {/* <option value="" disabled={required}>Please select</option> */}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {error && (
        <p id={`${id}-error`} className="mt-1 text-xs text-red-600" role="alert">
          {error}
        </p>
      )}
    </div>
  );
};

export default SelectField; 