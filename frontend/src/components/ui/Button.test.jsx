import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from './Button';
import '@testing-library/jest-dom';

describe('Button component', () => {
  test('renders with default props', () => {
    render(<Button>Click Me</Button>);
    const buttonElement = screen.getByRole('button', { name: /click me/i });
    expect(buttonElement).toBeInTheDocument();
    expect(buttonElement).toHaveClass('bg-primary'); // Default variant
    expect(buttonElement).toHaveClass('h-10'); // Default size
  });

  test('renders with a specific variant and size', () => {
    render(<Button variant="destructive" size="lg">Delete</Button>);
    const buttonElement = screen.getByRole('button', { name: /delete/i });
    expect(buttonElement).toHaveClass('bg-destructive');
    expect(buttonElement).toHaveClass('h-11');
  });

  test('calls onClick handler when clicked', () => {
    const handleClick = vi.fn(); // Using Vitest's vi for mocking
    render(<Button onClick={handleClick}>Submit</Button>);
    const buttonElement = screen.getByRole('button', { name: /submit/i });
    fireEvent.click(buttonElement);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  test('is disabled when disabled prop is true', () => {
    render(<Button disabled>Disabled</Button>);
    const buttonElement = screen.getByRole('button', { name: /disabled/i });
    expect(buttonElement).toBeDisabled();
    expect(buttonElement).toHaveClass('disabled:opacity-50');
  });

  test('renders as a span when asChild is true', () => {
    render(
      <Button asChild>
        <a href="/">Link Button</a>
      </Button>
    );
    // Check if the inner element (anchor) received button-like classes
    // and that the component rendered is indeed a span containing the anchor.
    const linkElement = screen.getByRole('link', { name: /link button/i });
    expect(linkElement).toBeInTheDocument();
    
    // The component itself is a span
    const spanElement = linkElement.parentElement;
    expect(spanElement.tagName).toBe('SPAN');
    expect(spanElement).toHaveClass('bg-primary'); // Default variant styles applied to the span
  });

  test('applies additional className', () => {
    render(<Button className="my-custom-class">Custom</Button>);
    const buttonElement = screen.getByRole('button', { name: /custom/i });
    expect(buttonElement).toHaveClass('my-custom-class');
  });
});
