import React from 'react';

const InputField = ({
  id,
  label,
  type = 'text',
  value,
  onChange,
  placeholder = '',
  error = null,
  disabled = false,
  required = false,
  className = '', // For the container div
  inputClassName = '', // For the input element itself
  labelClassName = '', // For the label element
  ...props
}) => {
  const baseInputStyles = `
    mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm 
    focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm
  `;
  const errorInputStyles = 'border-red-500 focus:ring-red-500 focus:border-red-500';
  const disabledInputStyles = 'bg-gray-100 cursor-not-allowed';

  const inputStyles = `
    ${baseInputStyles}
    ${error ? errorInputStyles : ''}
    ${disabled ? disabledInputStyles : ''}
    ${inputClassName}
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
      <input
        type={type}
        id={id}
        name={id} // Often useful for forms
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        disabled={disabled}
        required={required}
        className={inputStyles}
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={error ? `${id}-error` : undefined}
        {...props}
      />
      {error && (
        <p id={`${id}-error`} className="mt-1 text-xs text-red-600" role="alert">
          {error}
        </p>
      )}
    </div>
  );
};

export default InputField; 