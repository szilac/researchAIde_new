import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Input } from './ui/Input';
import { Button } from './ui/Button';
import { Checkbox } from './ui/Checkbox';
// import Select from './ui/Select'; // If/when a Select component exists
import { cn } from '../utils/cn';

/**
 * Component providing controls for filtering, sorting, and selecting a list of papers.
 */
const PaperListControls = ({
  initialFilters = { searchTerm: '', sortBy: 'relevance', sortOrder: 'desc' },
  onFilterChange, // Callback: (filters) => void
  // Props for Select All functionality
  itemCount = 0, // Total number of items currently displayed/filterable
  selectedCount = 0, // Number of items currently selected
  onSelectAllChange, // Callback: (selectAll: boolean) => void
  className,
}) => {
  const [searchTerm, setSearchTerm] = useState(initialFilters.searchTerm);
  const [sortBy, setSortBy] = useState(initialFilters.sortBy);
  const [sortOrder, setSortOrder] = useState(initialFilters.sortOrder);

  // Debounce search term input (optional but good practice)
  useEffect(() => {
    const handler = setTimeout(() => {
      if (searchTerm !== initialFilters.searchTerm) { // Only trigger if changed
        onFilterChange && onFilterChange({ searchTerm, sortBy, sortOrder });
      }
    }, 300); // 300ms debounce

    return () => {
      clearTimeout(handler);
    };
    // Intentionally excluding onFilterChange, initialFilters from deps
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchTerm, sortBy, sortOrder]); 

  // Trigger immediate update for sort changes
  useEffect(() => {
    if (sortBy !== initialFilters.sortBy || sortOrder !== initialFilters.sortOrder) {
       onFilterChange && onFilterChange({ searchTerm, sortBy, sortOrder });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sortBy, sortOrder]);

  const handleSortChange = (newSortBy) => {
    if (newSortBy === sortBy) {
      // Toggle order if clicking the same sort key
      setSortOrder(prevOrder => (prevOrder === 'asc' ? 'desc' : 'asc'));
    } else {
      // Set new sort key, default to desc
      setSortBy(newSortBy);
      setSortOrder('desc');
    }
  };

  const handleSelectAll = (checked) => {
    onSelectAllChange && onSelectAllChange(checked);
  };

  const isSelectAllChecked = itemCount > 0 && selectedCount === itemCount;
  const isIndeterminate = selectedCount > 0 && selectedCount < itemCount;

  const sortOptions = [
    { key: 'relevance', label: 'Relevance' },
    { key: 'date', label: 'Date' },
    { key: 'title', label: 'Title' },
    // { key: 'authors', label: 'Authors' }, // Sorting by authors might be complex
  ];

  return (
    <div className={cn('flex flex-col sm:flex-row gap-4 p-4 border-b items-center', className)}>
      {/* Select All Checkbox */}
      {itemCount > 0 && (
        <div className="flex-shrink-0">
           <Checkbox 
             id="select-all-papers"
             checked={isSelectAllChecked}
             // indeterminate={isIndeterminate} // Need to handle indeterminate state visually if desired
             onChange={handleSelectAll}
             aria-label="Select all papers"
             title={isSelectAllChecked ? "Deselect all" : "Select all"}
           />
           {/* Optional: Display count e.g., {selectedCount}/{itemCount} */}
        </div>
      )}

      {/* Search Input */}
      <div className="flex-grow">
        <Input
          type="search"
          placeholder="Search papers (title, authors, abstract)..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full"
        />
      </div>

      {/* Sort Controls */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-sm font-medium text-muted-foreground">Sort by:</span>
        {sortOptions.map(option => (
          <Button
            key={option.key}
            variant={sortBy === option.key ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => handleSortChange(option.key)}
          >
            {option.label}
            {sortBy === option.key && (
              <span className="ml-1">{sortOrder === 'asc' ? '↑' : '↓'}</span>
            )}
          </Button>
        ))}
      </div>
       {/* TODO: Add Date Range Filter, Score Filter etc. here */}
    </div>
  );
};

PaperListControls.propTypes = {
  /** Initial filter/sort state */
  initialFilters: PropTypes.shape({
    searchTerm: PropTypes.string,
    sortBy: PropTypes.string,
    sortOrder: PropTypes.oneOf(['asc', 'desc']),
  }),
  /** Callback function when filters or sorting change */
  onFilterChange: PropTypes.func,
  /** Total number of items subject to selection */
  itemCount: PropTypes.number,
  /** Number of currently selected items */
  selectedCount: PropTypes.number,
  /** Callback function when select all state changes */
  onSelectAllChange: PropTypes.func,
  /** Additional classes for the container */
  className: PropTypes.string,
};

export { PaperListControls };
