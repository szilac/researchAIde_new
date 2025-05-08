import React, { useState } from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ConfirmationDialog } from './ConfirmationDialog';
import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Basic Modal needs to be mocked or provided via context if it has complex portal logic
// For now, assuming it renders inline for testing purposes.
// You might need setupTests.js for mocking portals if using React Portals in Modal.

describe('ConfirmationDialog component', () => {
  const mockOnClose = vi.fn();
  const mockOnConfirm = vi.fn();

  beforeEach(() => {
    mockOnClose.mockClear();
    mockOnConfirm.mockClear();
  });

  test('does not render when isOpen is false', () => {
    render(
      <ConfirmationDialog
        isOpen={false}
        onClose={mockOnClose}
        onConfirm={mockOnConfirm}
        title="Test Title"
        description="Test Description"
      />
    );
    expect(screen.queryByText('Test Title')).not.toBeInTheDocument();
    expect(screen.queryByText('Test Description')).not.toBeInTheDocument();
  });

  test('renders title, description, and default buttons when open', () => {
    render(
      <ConfirmationDialog
        isOpen={true}
        onClose={mockOnClose}
        onConfirm={mockOnConfirm}
        title="Confirm Action"
        description="Are you sure you want to proceed?"
      />
    );
    expect(screen.getByText('Confirm Action')).toBeInTheDocument();
    expect(screen.getByText('Are you sure you want to proceed?')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Confirm' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
  });

  test('calls onConfirm when confirm button is clicked', () => {
    render(
      <ConfirmationDialog isOpen={true} onClose={mockOnClose} onConfirm={mockOnConfirm} />
    );
    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }));
    expect(mockOnConfirm).toHaveBeenCalledTimes(1);
    expect(mockOnClose).not.toHaveBeenCalled();
  });

  test('calls onClose when cancel button is clicked', () => {
    render(
      <ConfirmationDialog isOpen={true} onClose={mockOnClose} onConfirm={mockOnConfirm} />
    );
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(mockOnClose).toHaveBeenCalledTimes(1);
    expect(mockOnConfirm).not.toHaveBeenCalled();
  });

  test('calls onClose when overlay is clicked (inherited from Modal)', () => {
    render(
      <ConfirmationDialog isOpen={true} onClose={mockOnClose} onConfirm={mockOnConfirm} />
    );
    // Assuming Modal overlay has role='dialog'
    fireEvent.click(screen.getByRole('dialog')); 
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

   test('calls onClose when Escape key is pressed (inherited from Modal)', () => {
    render(
      <ConfirmationDialog isOpen={true} onClose={mockOnClose} onConfirm={mockOnConfirm} />
    );
    fireEvent.keyDown(document, { key: 'Escape', code: 'Escape' });
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  test('renders custom button text', () => {
    render(
      <ConfirmationDialog
        isOpen={true}
        onClose={mockOnClose}
        onConfirm={mockOnConfirm}
        confirmText="Delete"
        cancelText="Keep"
      />
    );
    expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Keep' })).toBeInTheDocument();
  });

  test('applies confirmVariant to confirm button', () => {
    render(
      <ConfirmationDialog
        isOpen={true}
        onClose={mockOnClose}
        onConfirm={mockOnConfirm}
        confirmText="Delete"
        confirmVariant="destructive"
      />
    );
    // Check for the presence of the class associated with the destructive variant
    expect(screen.getByRole('button', { name: 'Delete' })).toHaveClass('bg-destructive');
  });

  test('shows loading state when isConfirming is true', () => {
    render(
      <ConfirmationDialog
        isOpen={true}
        onClose={mockOnClose}
        onConfirm={mockOnConfirm}
        confirmText="Submit"
        isConfirming={true}
      />
    );
    const confirmButton = screen.getByRole('button', { name: /processing/i });
    expect(confirmButton).toBeInTheDocument();
    expect(confirmButton).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled();
    // Also check if the default Modal close button is hidden
    expect(screen.queryByRole('button', { name: /close/i })).not.toBeInTheDocument();
  });
});
