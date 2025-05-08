import React, { useEffect } from 'react';
import PropTypes from 'prop-types';
import { cn } from '../../utils/cn';
import { X } from 'lucide-react'; // Using lucide-react for icons, will need to be installed

/**
 * A modal dialog that overlays the page content.
 */
const Modal = ({
  isOpen,
  onClose,
  title,
  children,
  footer,
  className,
  titleClassName,
  bodyClassName,
  footerClassName,
  showCloseButton = true,
}) => {
  useEffect(() => {
    const handleEsc = (event) => {
      if (event.keyCode === 27) {
        onClose();
      }
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden'; // Prevent background scroll
      window.addEventListener('keydown', handleEsc);
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      window.removeEventListener('keydown', handleEsc);
      document.body.style.overflow = 'unset'; // Ensure body scroll is restored
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className={cn(
        'fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm',
        className
      )}
      onClick={onClose} // Close on overlay click
      role="dialog" // Added role
      aria-modal="true" // Added aria-modal
    >
      <div
        className={cn(
          'relative m-4 w-full max-w-lg rounded-lg border bg-card p-6 shadow-lg text-card-foreground',
          'max-h-[90vh] flex flex-col' // Max height and flex column for scrolling content
        )}
        onClick={(e) => e.stopPropagation()} // Prevent closing when clicking inside modal content
      >
        {/* Header */}
        <div className="flex items-start justify-between border-b border-border pb-4 mb-4">
          {title && (
            <h2 id="modal-title" className={cn('text-xl font-semibold', titleClassName)}>
              {title}
            </h2>
          )}
          {showCloseButton && (
            <button
              onClick={onClose}
              className="ml-auto rounded-sm p-1 text-muted-foreground ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground"
            >
              <X className="h-5 w-5" />
              <span className="sr-only">Close</span>
            </button>
          )}
        </div>

        {/* Body */}
        <div className={cn('flex-grow overflow-y-auto', bodyClassName)}>
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div className={cn('mt-6 flex justify-end space-x-2 border-t border-border pt-4', footerClassName)}>
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};

Modal.propTypes = {
  /** Whether the modal is open. */
  isOpen: PropTypes.bool.isRequired,
  /** Function to call when the modal should be closed. */
  onClose: PropTypes.func.isRequired,
  /** Optional title for the modal header. */
  title: PropTypes.string,
  /** Content of the modal body. */
  children: PropTypes.node,
  /** Optional footer content for the modal. */
  footer: PropTypes.node,
  /** Additional classes for the modal overlay. */
  className: PropTypes.string,
  /** Additional classes for the modal title. */
  titleClassName: PropTypes.string,
  /** Additional classes for the modal body container. */
  bodyClassName: PropTypes.string,
  /** Additional classes for the modal footer container. */
  footerClassName: PropTypes.string,
  /** Whether to show the close button in the header. Defaults to true. */
  showCloseButton: PropTypes.bool,
};

export { Modal };
