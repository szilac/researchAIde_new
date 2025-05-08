import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { PaperListControls } from './PaperListControls';
import '@testing-library/jest-dom';
import { vi } from 'vitest';

describe('PaperListControls component', () => {
  const mockOnFilterChange = vi.fn();

  beforeEach(() => {
    vi.useFakeTimers(); // Use fake timers for debounce
    mockOnFilterChange.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers(); // Restore real timers
  });

  test('renders search input and sort buttons', () => {
    render(<PaperListControls onFilterChange={mockOnFilterChange} />);

    expect(screen.getByPlaceholderText(/search papers/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /relevance ↓/i })).toBeInTheDocument(); // Default sort
    expect(screen.getByRole('button', { name: /date/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /title/i })).toBeInTheDocument();
  });

  test('calls onFilterChange with updated search term after debounce', async () => {
    render(<PaperListControls onFilterChange={mockOnFilterChange} />);
    const input = screen.getByPlaceholderText(/search papers/i);

    fireEvent.change(input, { target: { value: 'test search' } });

    // Should not have been called immediately
    expect(mockOnFilterChange).not.toHaveBeenCalled();

    // Fast-forward time
    act(() => {
       vi.advanceTimersByTime(300); // Advance past debounce timeout
    });
    
    await waitFor(() => {
        expect(mockOnFilterChange).toHaveBeenCalledTimes(1);
        expect(mockOnFilterChange).toHaveBeenCalledWith({ 
            searchTerm: 'test search', 
            sortBy: 'relevance', // Default
            sortOrder: 'desc' // Default
        });
    });
  });

  test('calls onFilterChange immediately when sort button is clicked', () => {
    render(<PaperListControls onFilterChange={mockOnFilterChange} />);
    const dateButton = screen.getByRole('button', { name: /date/i });

    fireEvent.click(dateButton);

    expect(mockOnFilterChange).toHaveBeenCalledTimes(1);
    expect(mockOnFilterChange).toHaveBeenCalledWith({ 
      searchTerm: '', 
      sortBy: 'date', 
      sortOrder: 'desc' // Defaults to desc on new sort key
    });
  });

   test('toggles sort order when the same sort button is clicked twice', () => {
    render(<PaperListControls onFilterChange={mockOnFilterChange} />);
    const relevanceButton = screen.getByRole('button', { name: /relevance ↓/i }); // Initially desc

    // First click (already default relevance, toggle to asc)
    fireEvent.click(relevanceButton);
    expect(mockOnFilterChange).toHaveBeenCalledTimes(1);
    expect(mockOnFilterChange).toHaveBeenCalledWith({ searchTerm: '', sortBy: 'relevance', sortOrder: 'asc' });

    // Component should re-render with new state, let's find the button again (now asc)
    const relevanceButtonAsc = screen.getByRole('button', { name: /relevance ↑/i });

    // Second click (toggle back to desc)
    fireEvent.click(relevanceButtonAsc);
    expect(mockOnFilterChange).toHaveBeenCalledTimes(2); 
    expect(mockOnFilterChange).toHaveBeenLastCalledWith({ searchTerm: '', sortBy: 'relevance', sortOrder: 'desc' });
  });

  test('renders with initialFilters', () => {
     render(
      <PaperListControls 
        initialFilters={{ searchTerm: 'init', sortBy: 'title', sortOrder: 'asc' }}
        onFilterChange={mockOnFilterChange} 
      />
    );

    expect(screen.getByPlaceholderText(/search papers/i)).toHaveValue('init');
    expect(screen.getByRole('button', { name: /title ↑/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /relevance/i })).toBeInTheDocument(); 
  });
});
