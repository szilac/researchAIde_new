import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { Input } from './Input';
import '@testing-library/jest-dom';

describe('Input component', () => {
  test('renders with default props', () => {
    render(<Input placeholder="Enter text" />);
    const inputElement = screen.getByPlaceholderText(/enter text/i);
    expect(inputElement).toBeInTheDocument();
    expect(inputElement).toHaveAttribute('type', 'text'); // Default type
  });

  test('renders with a specific type', () => {
    render(<Input type="password" placeholder="Enter password" />);
    const inputElement = screen.getByPlaceholderText(/enter password/i);
    expect(inputElement).toHaveAttribute('type', 'password');
  });

  test('calls onChange handler when value changes', () => {
    const handleChange = vi.fn();
    render(<Input onChange={handleChange} placeholder="Test input" />);
    const inputElement = screen.getByPlaceholderText(/test input/i);
    fireEvent.change(inputElement, { target: { value: 'new value' } });
    expect(handleChange).toHaveBeenCalledTimes(1);
    // Note: In a real scenario with controlled components, you might also check inputElement.value
    // but since this is uncontrolled for the test, we focus on the event.
  });

  test('is disabled when disabled prop is true', () => {
    render(<Input disabled placeholder="Disabled input" />);
    const inputElement = screen.getByPlaceholderText(/disabled input/i);
    expect(inputElement).toBeDisabled();
  });

  test('applies additional className', () => {
    render(<Input className="my-custom-class" placeholder="Custom" />);
    const inputElement = screen.getByPlaceholderText(/custom/i);
    expect(inputElement).toHaveClass('my-custom-class');
  });

  test('accepts and displays a value', () => {
    render(<Input value="Initial Value" readOnly placeholder="Value test"/>);
    const inputElement = screen.getByPlaceholderText(/value test/i);
    expect(inputElement).toHaveValue('Initial Value');
  });
});
