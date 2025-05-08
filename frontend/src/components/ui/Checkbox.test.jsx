import React, { useState } from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { Checkbox } from './Checkbox';
import '@testing-library/jest-dom';
import { vi } from 'vitest';

describe('Checkbox component', () => {
  test('renders unchecked by default', () => {
    render(<Checkbox checked={false} onChange={() => {}} label="Test Checkbox" />);
    const checkbox = screen.getByRole('checkbox', { name: /test checkbox/i });
    expect(checkbox).toBeInTheDocument();
    expect(checkbox).toHaveAttribute('aria-checked', 'false');
    expect(checkbox).toHaveAttribute('data-state', 'unchecked');
  });

  test('renders checked when checked prop is true', () => {
    render(<Checkbox checked={true} onChange={() => {}} label="Test Checkbox" />);
    const checkbox = screen.getByRole('checkbox', { name: /test checkbox/i });
    expect(checkbox).toHaveAttribute('aria-checked', 'true');
    expect(checkbox).toHaveAttribute('data-state', 'checked');
  });

  test('calls onChange with new state when clicked', () => {
    const handleChange = vi.fn();
    render(<Checkbox checked={false} onChange={handleChange} label="Click Me" />);
    const checkbox = screen.getByRole('checkbox', { name: /click me/i });

    fireEvent.click(checkbox);
    expect(handleChange).toHaveBeenCalledTimes(1);
    expect(handleChange).toHaveBeenCalledWith(true); // Should call with the new state
  });

   test('calls onChange with new state when clicked (starting checked)', () => {
    const handleChange = vi.fn();
    render(<Checkbox checked={true} onChange={handleChange} label="Click Me" />);
    const checkbox = screen.getByRole('checkbox', { name: /click me/i });

    fireEvent.click(checkbox);
    expect(handleChange).toHaveBeenCalledTimes(1);
    expect(handleChange).toHaveBeenCalledWith(false); // Should call with the new state
  });

  test('does not call onChange when disabled and clicked', () => {
    const handleChange = vi.fn();
    render(<Checkbox checked={false} onChange={handleChange} label="Disabled Check" disabled />);
    const checkbox = screen.getByRole('checkbox', { name: /disabled check/i });

    expect(checkbox).toBeDisabled();
    fireEvent.click(checkbox);
    expect(handleChange).not.toHaveBeenCalled();
  });

  test('renders label correctly and links it via id/htmlFor', () => {
    render(<Checkbox checked={false} onChange={() => {}} label="My Label" id="my-check" />);
    const label = screen.getByText(/my label/i);
    expect(label).toBeInTheDocument();
    expect(label).toHaveAttribute('for', 'my-check');
    expect(screen.getByRole('checkbox')).toHaveAttribute('id', 'my-check');
  });

   test('generates an id if not provided', () => {
    render(<Checkbox checked={false} onChange={() => {}} label="Auto ID" />);
    const checkbox = screen.getByRole('checkbox', { name: /auto id/i });
    const label = screen.getByText(/auto id/i);
    const generatedId = checkbox.getAttribute('id');
    expect(generatedId).toMatch(/^radix-/); // React.useId generates IDs starting with :R, but test env might differ - check for non-empty
    expect(generatedId).toBeTruthy();
    expect(label).toHaveAttribute('for', generatedId);
  });
});
