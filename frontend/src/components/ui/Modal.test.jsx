import React, { useState } from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { Modal } from './Modal';
import { Button } from './Button'; // To render a footer button for interaction
import '@testing-library/jest-dom';

// Mock document.body.style.overflow for JSDOM environment
const originalOverflow = document.body.style.overflow;
beforeEach(() => {
  document.body.style.overflow = originalOverflow;
});
afterEach(() => {
  document.body.style.overflow = originalOverflow;
});

describe('Modal component', () => {
  test('does not render when isOpen is false', () => {
    render(
      <Modal isOpen={false} onClose={() => {}} title="Test Modal">
        <p>Modal Content</p>
      </Modal>
    );
    expect(screen.queryByText('Test Modal')).not.toBeInTheDocument();
    expect(screen.queryByText('Modal Content')).not.toBeInTheDocument();
  });

  test('renders with title and content when isOpen is true', () => {
    render(
      <Modal isOpen={true} onClose={() => {}} title="Visible Modal">
        <p>Hello from Modal</p>
      </Modal>
    );
    expect(screen.getByText('Visible Modal')).toBeInTheDocument();
    expect(screen.getByText('Hello from Modal')).toBeInTheDocument();
  });

  test('calls onClose when close button is clicked', () => {
    const handleClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={handleClose} title="Closable Modal">
        <p>Content</p>
      </Modal>
    );
    fireEvent.click(screen.getByRole('button', { name: /close/i }));
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  test('calls onClose when Escape key is pressed', () => {
    const handleClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={handleClose} title="Esc Modal">
        <p>Content</p>
      </Modal>
    );
    fireEvent.keyDown(document, { key: 'Escape', code: 'Escape', keyCode: 27, charCode: 27 });
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  test('calls onClose when overlay is clicked', () => {
    const handleClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={handleClose} title="Overlay Click Modal">
        <p>Content</p>
      </Modal>
    );
    // The overlay is the div with role='dialog'
    fireEvent.click(screen.getByRole('dialog'));
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  test('does not call onClose when content inside modal is clicked', () => {
    const handleClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={handleClose} title="Content Click Modal">
        <p data-testid="modal-content-p">Click me</p>
      </Modal>
    );
    fireEvent.click(screen.getByTestId('modal-content-p'));
    expect(handleClose).not.toHaveBeenCalled();
  });

  test('renders footer content', () => {
    const handleFooterClick = vi.fn();
    render(
      <Modal
        isOpen={true}
        onClose={() => {}}
        title="Modal with Footer"
        footer={<Button onClick={handleFooterClick}>Footer Action</Button>}
      >
        <p>Body</p>
      </Modal>
    );
    const footerButton = screen.getByRole('button', { name: /footer action/i });
    expect(footerButton).toBeInTheDocument();
    fireEvent.click(footerButton);
    expect(handleFooterClick).toHaveBeenCalledTimes(1);
  });

  test('manages body overflow style', () => {
    const { rerender } = render(<Modal isOpen={false} onClose={() => {}} title="Overflow Test"/>);
    expect(document.body.style.overflow).not.toBe('hidden');
    
    rerender(<Modal isOpen={true} onClose={() => {}} title="Overflow Test"/>);
    expect(document.body.style.overflow).toBe('hidden');
    
    rerender(<Modal isOpen={false} onClose={() => {}} title="Overflow Test"/>);
    expect(document.body.style.overflow).not.toBe('hidden');
  });

  test('cleans up event listener and body overflow on unmount', () => {
    const addSpy = vi.spyOn(window, 'addEventListener');
    const removeSpy = vi.spyOn(window, 'removeEventListener');
    const originalBodyOverflow = document.body.style.overflow;

    const { unmount } = render(<Modal isOpen={true} onClose={() => {}} title="Cleanup Test"/>);
    expect(document.body.style.overflow).toBe('hidden');
    expect(addSpy).toHaveBeenCalledWith('keydown', expect.any(Function));

    unmount();

    expect(document.body.style.overflow).toBe(originalBodyOverflow);
    expect(removeSpy).toHaveBeenCalledWith('keydown', expect.any(Function));

    addSpy.mockRestore();
    removeSpy.mockRestore();
  });
});
