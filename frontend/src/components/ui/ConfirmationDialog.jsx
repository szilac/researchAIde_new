import React from 'react';
import PropTypes from 'prop-types';
import { Modal } from './Modal';
import { Button } from './Button';
import { Spinner } from './Spinner';
import { cn } from '../../utils/cn';

/**
 * A reusable confirmation dialog component built on top of Modal.
 */
const ConfirmationDialog = ({
  isOpen,
  onClose,
  onConfirm,
  title = 'Are you sure?', // Default title
  description,
  confirmText = 'Confirm', // Default confirm button text
  cancelText = 'Cancel', // Default cancel button text
  confirmVariant = 'default', // Default variant for confirm button
  isConfirming = false, // Optional: Show loading state on confirm button
  dialogClassName,
  descriptionClassName,
  // ... any other Modal props you might want to pass through
}) => {
  if (!isOpen) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose} // Allow closing via Esc or overlay click
      title={title}
      className={dialogClassName} // Pass through dialog class name if needed
      // Prevent closing via overlay/esc if confirmation action is in progress?
      // onClose={isConfirming ? undefined : onClose} 
      showCloseButton={!isConfirming} // Hide close button while confirming
      footer={
        <div className="flex justify-end gap-2">
          <Button 
            variant="outline" 
            onClick={onClose}
            disabled={isConfirming}
          >
            {cancelText}
          </Button>
          <Button 
            variant={confirmVariant} 
            onClick={onConfirm}
            disabled={isConfirming}
            className="flex items-center gap-x-1.5"
          >
            {isConfirming && <Spinner size="sm" className="mr-1" />}
            {isConfirming ? 'Processing...' : confirmText}
          </Button>
        </div>
      }
    >
      {description && (
        <p className={cn("text-sm text-muted-foreground", descriptionClassName)}>
          {description}
        </p>
      )}
    </Modal>
  );
};

ConfirmationDialog.propTypes = {
  /** Whether the dialog is open. */
  isOpen: PropTypes.bool.isRequired,
  /** Function to call when the dialog should be closed (Cancel/Overlay/Esc). */
  onClose: PropTypes.func.isRequired,
  /** Function to call when the confirm button is clicked. */
  onConfirm: PropTypes.func.isRequired,
  /** The title of the confirmation dialog. */
  title: PropTypes.string,
  /** The descriptive text/message within the dialog. */
  description: PropTypes.node,
  /** Text for the confirmation button. */
  confirmText: PropTypes.string,
  /** Text for the cancel button. */
  cancelText: PropTypes.string,
  /** Visual variant for the confirmation button (e.g., 'default', 'destructive'). */
  confirmVariant: PropTypes.oneOf([
    'default',
    'destructive',
    'outline',
    'secondary',
    'ghost',
    'link',
  ]),
  /** Optional flag to indicate the confirmation action is processing (disables buttons, shows loading text). */
  isConfirming: PropTypes.bool,
  /** Optional additional classes for the Modal container. */
  dialogClassName: PropTypes.string,
  /** Optional additional classes for the description paragraph. */
  descriptionClassName: PropTypes.string,
};

export { ConfirmationDialog };
