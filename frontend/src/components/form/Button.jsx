import React from 'react';

const Button = ({
  children,
  onClick,
  type = 'button',
  variant = 'primary', // e.g., primary, secondary, danger, outline
  size = 'md',      // e.g., sm, md, lg
  disabled = false,
  className = '', // Allow custom classes to be passed
  ...props
}) => {
  // Base styles
  let baseStyles = 'font-semibold rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 transition ease-in-out duration-150';

  // Size styles
  const sizeStyles = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base',
  };

  // Variant styles
  const variantStyles = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500',
    secondary: 'bg-gray-200 text-gray-800 hover:bg-gray-300 focus:ring-gray-400',
    danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
    outline: 'bg-transparent text-blue-600 border border-blue-600 hover:bg-blue-50 focus:ring-blue-500',
    link: 'bg-transparent text-blue-600 hover:text-blue-700 underline focus:ring-blue-500 p-0',
  };

  if (disabled) {
    baseStyles += ' opacity-50 cursor-not-allowed';
  }

  const combinedClassName = `
    ${baseStyles}
    ${sizeStyles[size] || sizeStyles.md}
    ${variantStyles[variant] || variantStyles.primary}
    ${className}
  `.trim().replace(/\s+/g, ' '); // Clean up extra spaces

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={combinedClassName}
      {...props}
    >
      {children}
    </button>
  );
};

export default Button; 