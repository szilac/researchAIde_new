import React from 'react';
import PropTypes from 'prop-types';
import { cn } from '../../utils/cn';

/**
 * A container that displays content and actions about a single subject.
 */
const Card = React.forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('rounded-lg border bg-card text-card-foreground shadow-sm', className)}
    {...props}
  />
));
Card.displayName = 'Card';
Card.propTypes = {
  /** Additional classes for the card container. */
  className: PropTypes.string
};

/**
 * Header section for a Card component.
 */
const CardHeader = React.forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('flex flex-col space-y-1.5 p-6', className)}
    {...props}
  />
));
CardHeader.displayName = 'CardHeader';
CardHeader.propTypes = {
  /** Additional classes for the card header. */
  className: PropTypes.string
};

/**
 * Title section for a CardHeader.
 */
const CardTitle = React.forwardRef(({ className, children, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn('text-2xl font-semibold leading-none tracking-tight', className)}
    {...props}
  >
    {children}
  </h3>
));
CardTitle.displayName = 'CardTitle';
CardTitle.propTypes = {
  /** Additional classes for the card title. */
  className: PropTypes.string,
  /** The content of the card title. */
  children: PropTypes.node,
};

/**
 * Description section for a CardHeader.
 */
const CardDescription = React.forwardRef(({ className, children, ...props }, ref) => (
  <p
    ref={ref}
    className={cn('text-sm text-muted-foreground', className)}
    {...props}
  >
    {children}
  </p>
));
CardDescription.displayName = 'CardDescription';
CardDescription.propTypes = {
  /** Additional classes for the card description. */
  className: PropTypes.string,
  /** The content of the card description. */
  children: PropTypes.node,
};

/**
 * Main content area for a Card.
 */
const CardContent = React.forwardRef(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('p-6 pt-0', className)} {...props} />
));
CardContent.displayName = 'CardContent';
CardContent.propTypes = {
  /** Additional classes for the card content. */
  className: PropTypes.string
};

/**
 * Footer section for a Card.
 */
const CardFooter = React.forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('flex items-center p-6 pt-0', className)}
    {...props}
  />
));
CardFooter.displayName = 'CardFooter';
CardFooter.propTypes = {
  /** Additional classes for the card footer. */
  className: PropTypes.string
};

export {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
};
