import React from 'react';

interface IconWrapperProps extends React.SVGProps<SVGSVGElement> {
  // If using a library like Lucide, the icon prop could be more specific
  // For now, we assume children will be the SVG content or an <img> tag
  children: React.ReactNode;
  size?: number | string;
}

const IconWrapper = React.forwardRef<SVGSVGElement, IconWrapperProps>(
  ({ className, children, size = 24, ...props }, ref) => {
    // Apply size to direct SVG child if possible, or use it for a container
    // This is a simplistic approach; a more robust solution might involve cloning the child
    // and injecting width/height props if it's a React SVG component.
    return (
      <span
        style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
        className={className}
      >
        {/* If children is an SVG, we might want to inject width/height here */} 
        {/* For now, this acts as a simple span container */} 
        {/* A more direct approach for SVGs would be to pass them as children to an svg tag if we control the SVG source */} 
        {React.Children.map(children, child => {
          if (React.isValidElement(child) && typeof child.type === 'string' && child.type === 'svg') {
            return React.cloneElement(child as React.ReactElement<React.SVGProps<SVGSVGElement>>, {
              width: size,
              height: size,
              ref: ref, // Forwarding ref to the SVG element itself
              ...child.props, // Spread existing props from the child
              className: `${child.props.className || ''} ${className || ''}`.trim(), // Merge classNames
              ...props // Spread any additional SVGProps passed to IconWrapper
            });
          }
          // If it's not an SVG or not a direct SVG child, render as is within a span for potential styling with size.
          // This part might need refinement based on how icons are actually used.
          return <svg width={size} height={size} ref={ref} {...props} className={className}>{children}</svg>; 
        })}
      </span>
    );
  }
);

IconWrapper.displayName = 'IconWrapper';

export { IconWrapper };
export type { IconWrapperProps };
