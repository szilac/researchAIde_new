import React, { useState, useMemo, useCallback, useEffect } from 'react';
import { PaperListControls } from '../components/PaperListControls';
import { PaperCard } from '../components/PaperCard';
import { filterPapersByKeyword, sortPapers } from '../utils/filtering';
import { paperService } from '../services/paperService'; // Import the service
import { Spinner } from '../components/ui/Spinner'; // Import Spinner
// import { Alert, AlertDescription, AlertTitle } from '../components/ui/Alert'; // Commented out as component doesn't exist yet
import { Button } from '../components/ui/Button'; // Import Button
import { ConfirmationDialog } from '../components/ui/ConfirmationDialog'; // Import ConfirmationDialog
import { loadFromLocalStorage, saveToLocalStorage } from '../utils/localStorage'; // Import LS utils

// dnd-kit imports
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';

// Remove Mock Data
// const mockPapersData = [...];

const LOCAL_STORAGE_KEYS = {
  PAPERS: 'shortlistPapers',
  FILTERS: 'shortlistFilters',
  SELECTION: 'shortlistSelection',
};

/**
 * Temporary page for testing paper shortlist with local storage persistence.
 */
function ShortlistTestPage() {
  // Load initial data from LS or set defaults
  const [allPapers, setAllPapers] = useState(() => loadFromLocalStorage(LOCAL_STORAGE_KEYS.PAPERS, [])); 
  const [isLoading, setIsLoading] = useState(allPapers.length === 0); // Only show initial loading if no cache
  const [error, setError] = useState(null);
  
  const [filters, setFilters] = useState(() => 
    loadFromLocalStorage(LOCAL_STORAGE_KEYS.FILTERS, {
      searchTerm: '',
      sortBy: 'relevance', 
      sortOrder: 'desc',
    })
  );
  
  const [selectedPaperIds, setSelectedPaperIds] = useState(() => 
    new Set(loadFromLocalStorage(LOCAL_STORAGE_KEYS.SELECTION, []))
  );

  // Confirmation Dialog State
  const [isConfirmDialogOpen, setIsConfirmDialogOpen] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false); // For confirm loading state

  // --- dnd-kit Setup ---
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = useCallback((event) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      setAllPapers((papers) => {
        const oldIndex = papers.findIndex((p) => p.id === active.id);
        const newIndex = papers.findIndex((p) => p.id === over.id);
        
        if (oldIndex === -1 || newIndex === -1) return papers; // Should not happen

        return arrayMove(papers, oldIndex, newIndex);
      });
      // Note: If using filtering/sorting, you might need to adjust this
      // to reorder the original source list if `allPapers` represents the filtered list.
      // For now, assuming `allPapers` is the list being directly displayed and reordered.
    }
  }, []);
  // --- End dnd-kit Setup ---

  // Save state changes to Local Storage
  useEffect(() => {
    saveToLocalStorage(LOCAL_STORAGE_KEYS.FILTERS, filters);
  }, [filters]);

  useEffect(() => {
    // Convert Set to Array for storage
    saveToLocalStorage(LOCAL_STORAGE_KEYS.SELECTION, Array.from(selectedPaperIds));
  }, [selectedPaperIds]);

  useEffect(() => {
    // Save fetched papers (optional, overwrite existing cache)
    if (!isLoading && !error && allPapers.length > 0) {
        saveToLocalStorage(LOCAL_STORAGE_KEYS.PAPERS, allPapers);
    }
  }, [allPapers, isLoading, error]);

  // Fetch initial data (or refresh data)
  useEffect(() => {
    // Fetch even if cache exists, to get potential updates
    // Keep loading state minimal if cache existed
    // setIsLoading(true); // Re-enable if full loading state desired on refresh
    setError(null);
    paperService.getPaperShortlist()
      .then(data => {
        setAllPapers(data || []); 
      })
      .catch(err => {
        console.error("Error fetching shortlist:", err);
        setError(err.message || 'Failed to load paper shortlist.');
        // Don't clear papers if fetch fails, keep cached version if available
        // setAllPapers([]); 
      })
      .finally(() => {
        setIsLoading(false); // Always set loading false after attempt
      });
  }, []); // Fetch only once on mount

  const handleFilterChange = useCallback((newFilters) => {
    setFilters(newFilters);
  }, []);

  // Apply filtering and sorting to the fetched/cached data
  const filteredAndSortedPapers = useMemo(() => {
    if (!allPapers) return [];
    const filtered = filterPapersByKeyword(allPapers, filters.searchTerm);
    return sortPapers(filtered, filters.sortBy, filters.sortOrder);
  }, [filters, allPapers]);

  const handleSelectionChange = useCallback((paperId, isSelected) => {
    setSelectedPaperIds(prevSelectedIds => {
      const newSelectedIds = new Set(prevSelectedIds);
      if (isSelected) {
        newSelectedIds.add(paperId);
      } else {
        newSelectedIds.delete(paperId);
      }
      return newSelectedIds;
    });
  }, []);

  const handleSelectAllChange = useCallback((selectAll) => {
    setSelectedPaperIds(() => {
      if (selectAll) {
        // Select all *currently filtered* papers
        return new Set(filteredAndSortedPapers.map(p => p.id));
      } else {
        // Deselect all
        return new Set();
      }
    });
  }, [filteredAndSortedPapers]); 

  // Create items array for SortableContext (needs stable IDs)
  const paperIds = useMemo(() => filteredAndSortedPapers.map(p => p.id), [filteredAndSortedPapers]);

  const handleProcessSelected = async () => {
    setIsProcessing(true);
    console.log("Processing selected papers:", Array.from(selectedPaperIds));
    // Simulate API call
    try {
      // Replace with actual API call: await paperService.updatePaperShortlist(Array.from(selectedPaperIds));
      await new Promise(resolve => setTimeout(resolve, 1500)); // Simulate network delay
      console.log("Processing successful!");
      // Optionally clear selection or show success message
      // setSelectedPaperIds(new Set()); 
    } catch (err) {
       console.error("Processing failed:", err);
       // Show error message to user
       setError('Failed to process selected papers.'); // Basic error display
    } finally {
       setIsProcessing(false);
       setIsConfirmDialogOpen(false); // Close dialog after processing
    }
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Paper Shortlist (Test Page with LS Cache)</h1>
      
      <PaperListControls 
        // initialFilters={filters} // Controlled component, pass value directly
        // Pass state down to controls IF they need to display it, or manage internally
        // Let's assume PaperListControls manages its internal display state based on props potentially
        // Or, we modify PaperListControls to be fully controlled (pass value/onChange for search/sort)
        // For now, keeping PaperListControls as is, relying on its useEffect to call onFilterChange
        // Which updates the filters state here, which is saved to LS.
        // We load initial state FROM LS here.
        initialFilters={filters} // Keep passing initialFilters for initial setup inside controls
        onFilterChange={handleFilterChange}
        itemCount={filteredAndSortedPapers.length}
        selectedCount={selectedPaperIds.size}
        onSelectAllChange={handleSelectAllChange}
      />

      {/* Action Button Area */}
      <div className="my-4 flex justify-end">
         <Button 
           onClick={() => setIsConfirmDialogOpen(true)}
           disabled={selectedPaperIds.size === 0 || isLoading} // Disable if nothing selected or loading
         >
           Process {selectedPaperIds.size} Selected Papers
         </Button>
      </div>

      {/* Wrap list in DndContext and SortableContext */}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={paperIds} // Pass array of IDs
          strategy={verticalListSortingStrategy}
        >
          <div className="mt-4 space-y-4">
            {isLoading && (
              // Use Spinner for loading indicator
              <div className="flex justify-center items-center py-10">
                 <Spinner size="lg" />
              </div>
            )}

            {error && (
               <div className="text-center py-4 text-red-600 border border-red-600 p-4 rounded bg-red-100">
                 <p><strong>Error:</strong> {error}</p>
               </div>
               /* Optional: Use a dedicated Alert component if available */
               /* 
               <Alert variant="destructive">
                 <AlertTitle>Error</AlertTitle>
                 <AlertDescription>{error}</AlertDescription>
               </Alert>
               */
            )}

            {!isLoading && !error && filteredAndSortedPapers.length > 0 ? (
              filteredAndSortedPapers.map(paper => (
                <PaperCard 
                  key={paper.id} 
                  paper={paper}
                  isSelected={selectedPaperIds.has(paper.id)}
                  onSelectionChange={handleSelectionChange}
                  isDraggable={!filters.searchTerm} // Pass isDraggable prop
                  // id={paper.id} 
                />
              ))
            ) : null /* Handle empty state below */}

            {!isLoading && !error && filteredAndSortedPapers.length === 0 && allPapers.length > 0 && (
               <p className="text-center text-muted-foreground">No papers match the current filters.</p>
            )}

            {!isLoading && !error && allPapers.length === 0 && (
                 <p className="text-center text-muted-foreground">No papers found in the shortlist.</p>
            )}
          </div>
        </SortableContext>
      </DndContext>

      {/* Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={isConfirmDialogOpen}
        onClose={() => !isProcessing && setIsConfirmDialogOpen(false)} // Prevent closing if processing
        onConfirm={handleProcessSelected}
        title="Confirm Processing"
        description={`Are you sure you want to process the ${selectedPaperIds.size} selected papers? This action might be irreversible.`}
        confirmText="Process Papers"
        isConfirming={isProcessing}
      />

      {/* Debugging: Show selected IDs */}
      <div className="mt-6 p-4 border rounded bg-secondary/50">
        <h3 className="font-semibold">Selected IDs:</h3>
        <pre className="text-sm">{JSON.stringify(Array.from(selectedPaperIds))}</pre>
      </div>
    </div>
  );
}

export default ShortlistTestPage;
