import React from 'react';
import PropTypes from 'prop-types';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical } from 'lucide-react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  // CardFooter, // Not used in this basic version
} from './ui/Card';
import { Checkbox } from './ui/Checkbox';
import { cn } from '../utils/cn';

/**
 * Displays information about a single paper, including selection controls.
 */
const PaperCard = ({ 
  paper, 
  isSelected, 
  onSelectionChange, 
  className, 
  isDraggable = true,
  ...props 
}) => {
  const { id, title, authors, date, relevance, abstract } = paper;

  // dnd-kit sortable hook
  const { 
    attributes, 
    listeners, 
    setNodeRef, 
    transform, 
    transition, 
    isDragging // Can be used for styling while dragging
  } = useSortable({ id: id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1, // Example: reduce opacity while dragging
    zIndex: isDragging ? 10 : undefined, // Ensure dragging item is on top
  };

  const handleCheckboxChange = (checked) => {
    onSelectionChange(id, checked);
  };

  // Simple author formatting
  const authorString = authors?.join(', ') || 'N/A';
  // Simple date formatting
  const displayDate = date ? new Date(date).toLocaleDateString() : 'N/A';

  return (
    // Apply dnd-kit attributes and styles to the main Card element
    <Card 
      ref={setNodeRef} 
      style={style} 
      {...attributes} // Apply attributes for dnd-kit
      // {...listeners} // Apply listeners to the whole card - OR apply to a specific drag handle element
      className={cn(
        'flex flex-row items-start gap-4 p-4 relative touch-none', // touch-none can help prevent scrolling issues on touch devices
        isSelected && 'bg-accent', 
        isDragging && 'shadow-xl', // Add extra shadow while dragging
        className
      )}
      {...props}
    >
      {/* Optional: Drag Handle */}
      {isDraggable && ( // Conditionally render handle
        <div {...listeners} className="cursor-grab touch-none pt-1 pr-2">
            <GripVertical className="h-5 w-5 text-muted-foreground hover:text-foreground" />
        </div>
      )}
      {!isDraggable && ( // Placeholder to maintain layout if handle is hidden
        <div className="pt-1 pr-2 w-[calc(1.25rem+0.5rem)]"> {/* Width of icon + padding */} </div>
      )}

      {/* Checkbox positioned top-left or alongside content */}
      <div className="pt-1"> 
        <Checkbox
          id={`select-paper-${id}`}
          checked={isSelected}
          onChange={handleCheckboxChange}
          aria-label={`Select paper titled ${title}`}
        />
      </div>
      
      {/* Paper Content */}
      <div className="flex-grow">
        <CardHeader className="p-0 mb-2">
          <CardTitle className="text-lg">{title || 'Untitled Paper'}</CardTitle>
          <CardDescription>
            By: {authorString} | Published: {displayDate} | Relevance: {relevance ?? 'N/A'}
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {/* Basic abstract display, could add expand/collapse later */}
          <p className="text-sm text-muted-foreground line-clamp-3">
            {abstract || 'No abstract available.'}
          </p>
        </CardContent>
         {/* Optional Footer can be added here if needed */}
      </div>
    </Card>
  );
};

PaperCard.propTypes = {
  /** The paper data object */
  paper: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    title: PropTypes.string,
    authors: PropTypes.arrayOf(PropTypes.string),
    date: PropTypes.string, // Assuming ISO date string
    relevance: PropTypes.number,
    abstract: PropTypes.string,
  }).isRequired,
  /** Whether the paper is currently selected */
  isSelected: PropTypes.bool.isRequired,
  /** Function called when selection state changes: (paperId, isSelected) => void */
  onSelectionChange: PropTypes.func.isRequired,
  /** Additional classes for the card */
  className: PropTypes.string,
  /** Whether the card should be draggable */
  isDraggable: PropTypes.bool,
};

export { PaperCard };
