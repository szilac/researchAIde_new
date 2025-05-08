import React from 'react';
import { render, screen } from '@testing-library/react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from './Card';
import '@testing-library/jest-dom';

describe('Card component and its parts', () => {
  test('renders Card with content', () => {
    render(<Card data-testid="card-container">Card Content</Card>);
    const cardElement = screen.getByTestId('card-container');
    expect(cardElement).toBeInTheDocument();
    expect(cardElement).toHaveTextContent('Card Content');
    expect(cardElement).toHaveClass('rounded-lg border bg-card text-card-foreground shadow-sm');
  });

  test('renders CardHeader with CardTitle and CardDescription', () => {
    render(
      <CardHeader data-testid="card-header">
        <CardTitle>Test Title</CardTitle>
        <CardDescription>Test Description</CardDescription>
      </CardHeader>
    );
    const headerElement = screen.getByTestId('card-header');
    expect(headerElement).toBeInTheDocument();
    expect(screen.getByText('Test Title')).toBeInTheDocument();
    expect(screen.getByText('Test Description')).toBeInTheDocument();
    expect(screen.getByText('Test Title')).toHaveClass('text-2xl font-semibold');
    expect(screen.getByText('Test Description')).toHaveClass('text-sm text-muted-foreground');
  });

  test('renders CardContent', () => {
    render(<CardContent>Main content here</CardContent>);
    expect(screen.getByText('Main content here')).toBeInTheDocument();
    expect(screen.getByText('Main content here')).toHaveClass('p-6 pt-0');
  });

  test('renders CardFooter', () => {
    render(<CardFooter>Footer content</CardFooter>);
    expect(screen.getByText('Footer content')).toBeInTheDocument();
    expect(screen.getByText('Footer content')).toHaveClass('flex items-center p-6 pt-0');
  });

  test('renders a complete Card structure', () => {
    render(
      <Card className="my-custom-card">
        <CardHeader className="my-custom-header">
          <CardTitle className="my-custom-title">Complete Card</CardTitle>
          <CardDescription className="my-custom-description">This is a full card.</CardDescription>
        </CardHeader>
        <CardContent className="my-custom-content">
          <p>Card body content.</p>
        </CardContent>
        <CardFooter className="my-custom-footer">
          <button>Action</button>
        </CardFooter>
      </Card>
    );

    expect(screen.getByText('Complete Card').closest('.my-custom-card')).toBeInTheDocument();
    expect(screen.getByText('Complete Card')).toHaveClass('my-custom-title');
    expect(screen.getByText('This is a full card.')).toHaveClass('my-custom-description');
    expect(screen.getByText('Card body content.').closest('.my-custom-content')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /action/i }).closest('.my-custom-footer')).toBeInTheDocument();
  });
});
