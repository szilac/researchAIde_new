import React from 'react';
import { render, screen } from '@testing-library/react';
import { Progress } from './Progress';
import '@testing-library/jest-dom';

describe('Progress component', () => {
  test('renders with a given value and default max', () => {
    render(<Progress value={50} data-testid="progress-bar" />);
    const progressBar = screen.getByTestId('progress-bar');
    expect(progressBar).toBeInTheDocument();
    expect(progressBar).toHaveAttribute('aria-valuenow', '50');
    expect(progressBar).toHaveAttribute('aria-valuemax', '100');

    const indicator = progressBar.firstChild;
    expect(indicator).toHaveStyle('transform: translateX(-50%)'); // 100 - 50 = 50%
  });

  test('renders with a given value and custom max', () => {
    render(<Progress value={25} max={200} data-testid="progress-bar" />);
    const progressBar = screen.getByTestId('progress-bar');
    expect(progressBar).toHaveAttribute('aria-valuenow', '25');
    expect(progressBar).toHaveAttribute('aria-valuemax', '200');
    
    const indicator = progressBar.firstChild;
    // (25 / 200) * 100 = 12.5% => transform: translateX(-(100-12.5)%) = translateX(-87.5%)
    expect(indicator).toHaveStyle('transform: translateX(-87.5%)');
  });

  test('renders at 0% if value is 0', () => {
    render(<Progress value={0} data-testid="progress-bar" />);
    const indicator = screen.getByTestId('progress-bar').firstChild;
    expect(indicator).toHaveStyle('transform: translateX(-100%)');
  });

  test('renders at 100% if value equals max', () => {
    render(<Progress value={100} max={100} data-testid="progress-bar" />);
    const indicator = screen.getByTestId('progress-bar').firstChild;
    expect(indicator).toHaveStyle('transform: translateX(0%)');
  });

   test('applies custom className and indicatorClassName', () => {
    render(
      <Progress 
        value={75} 
        className="my-custom-progress" 
        indicatorClassName="my-custom-indicator"
        data-testid="progress-bar"
      />
    );
    const progressBar = screen.getByTestId('progress-bar');
    expect(progressBar).toHaveClass('my-custom-progress');
    expect(progressBar.firstChild).toHaveClass('my-custom-indicator');
  });
});
