import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getWorkflowStatus, submitShortlistReview } from '../services/apiClient';
import Button from '../components/form/Button';

const POLLING_INTERVAL = 3000; // 3 seconds

function WorkflowDisplayPage() {
  const { workflowId } = useParams();
  const navigate = useNavigate();
  const [workflowState, setWorkflowState] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pollingIntervalId, setPollingIntervalId] = useState(null);
  const [selectedPapers, setSelectedPapers] = useState({}); // For shortlist review

  const stopPolling = useCallback(() => {
    if (pollingIntervalId) {
      clearInterval(pollingIntervalId);
      setPollingIntervalId(null);
    }
  }, [pollingIntervalId]);

  const fetchStatus = useCallback(async () => {
    if (!workflowId) return;
    try {
      // setIsLoading(true); // Optionally set loading for each poll, or just initial
      const data = await getWorkflowStatus(workflowId);
      setWorkflowState(data);
      setError(null);

      if (data?.workflow_outcome === 'success' || 
          data?.workflow_outcome === 'error' || 
          data?.workflow_outcome === 'failure' || 
          data?.workflow_outcome === 'not_found') {
        stopPolling();
      } else if (data?.is_waiting_for_input && data?.current_step_name === 'request_shortlist_review') {
        stopPolling(); // Stop polling when HITL is active
        // Prepare for shortlist review if papers are present
        if (data.payload?.initial_paper_shortlist) {
          const initialSelection = {};
          data.payload.initial_paper_shortlist.forEach(paper => {
            initialSelection[paper.arxiv_id || paper.id] = true; // Default to select all
          });
          setSelectedPapers(initialSelection);
        }
      }
    } catch (err) {
      console.error('Error fetching workflow status:', err);
      setError(err.message || 'Failed to fetch workflow status.');
      stopPolling(); 
    } finally {
      setIsLoading(false);
    }
  }, [workflowId, stopPolling]);

  useEffect(() => {
    fetchStatus(); // Initial fetch
    const intervalId = setInterval(fetchStatus, POLLING_INTERVAL);
    setPollingIntervalId(intervalId);

    return () => {
      stopPolling(); // Cleanup on unmount
    };
  }, [workflowId, fetchStatus, stopPolling]); // fetchStatus and stopPolling are now dependencies

  const handlePaperSelectionChange = (paperId) => {
    setSelectedPapers(prev => ({
      ...prev,
      [paperId]: !prev[paperId],
    }));
  };

  const handleSubmitReview = async () => {
    if (!workflowState?.payload?.initial_paper_shortlist) return;
    
    const confirmedPapers = workflowState.payload.initial_paper_shortlist.filter(
      paper => selectedPapers[paper.arxiv_id || paper.id]
    );

    setIsLoading(true);
    setError(null);
    try {
      await submitShortlistReview(workflowId, confirmedPapers);
      // After submitting, restart polling or fetch status once to see update
      fetchStatus(); 
      const intervalId = setInterval(fetchStatus, POLLING_INTERVAL);
      setPollingIntervalId(intervalId);
    } catch (err) {
      console.error('Error submitting shortlist review:', err);
      setError(err.message || 'Failed to submit review.');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading && !workflowState) {
    return <div className="container mx-auto p-4 text-center">Loading workflow details...</div>;
  }

  if (error) {
    return (
      <div className="container mx-auto p-4 text-center text-red-600">
        <p>Error: {error}</p>
        <Button onClick={() => navigate('/setup')} variant="secondary">Go to Setup</Button>
      </div>
    );
  }

  if (!workflowState || workflowState.workflow_outcome === 'not_found') {
    return (
        <div className="container mx-auto p-4 text-center">
            <p>Workflow not found or an error occurred.</p>
            <Button onClick={() => navigate('/setup')} variant="secondary">Go to Setup</Button>
        </div>
    );
  }

  // Display Workflow Information
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Workflow Details (ID: {workflowId})</h1>
      
      <div className="bg-gray-100 p-4 rounded-lg shadow mb-6">
        <p><strong>Status:</strong> {workflowState.status}</p>
        <p><strong>Outcome:</strong> {workflowState.workflow_outcome || 'In Progress'}</p>
        <p><strong>Current Step:</strong> {workflowState.current_step_name || 'N/A'}</p>
        <p><strong>Waiting for Input:</strong> {workflowState.is_waiting_for_input ? 'Yes' : 'No'}</p>
        {workflowState.last_updated && <p><strong>Last Updated:</strong> {new Date(workflowState.last_updated).toLocaleString()}</p>}
      </div>

      {workflowState.is_waiting_for_input && workflowState.current_step_name === 'request_shortlist_review' && (
        <div className="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 mb-6" role="alert">
          <p className="font-bold">Action Required: Shortlist Review</p>
          <p>Please review the papers below and confirm your selection.</p>
          {workflowState.payload?.initial_paper_shortlist && workflowState.payload.initial_paper_shortlist.length > 0 ? (
            <div className="mt-4">
              {workflowState.payload.initial_paper_shortlist.map(paper => {
                const paperId = paper.arxiv_id || paper.id;
                return (
                  <div key={paperId} className="mb-2 p-2 border rounded bg-white">
                    <label className="flex items-center">
                      <input 
                        type="checkbox" 
                        checked={!!selectedPapers[paperId]}
                        onChange={() => handlePaperSelectionChange(paperId)}
                        className="mr-2"
                      />
                      <span>{paper.title} (ID: {paperId})</span>
                    </label>
                  </div>
                );
              })}
              <Button onClick={handleSubmitReview} disabled={isLoading} className="mt-4">
                {isLoading ? 'Submitting Review...' : 'Submit Confirmed Shortlist'}
              </Button>
            </div>
          ) : (
            <p className="mt-2">No papers in the initial shortlist to review.</p>
          )}
        </div>
      )}

      {workflowState.workflow_outcome === 'success' && workflowState.payload?.final_report && (
        <div className="bg-green-100 border-l-4 border-green-500 text-green-700 p-4 mb-6">
          <h2 className="text-xl font-semibold mb-2">Final Report</h2>
          <pre className="whitespace-pre-wrap bg-white p-3 rounded">{JSON.stringify(workflowState.payload.final_report, null, 2)}</pre>
        </div>
      )}

      <div className="mt-6">
        <h3 className="text-lg font-semibold mb-2">Raw Workflow State:</h3>
        <pre className="bg-gray-200 p-3 rounded-md text-sm overflow-x-auto">
          {JSON.stringify(workflowState, null, 2)}
        </pre>
      </div>
       <Button onClick={() => navigate('/setup')} variant="secondary" className="mt-6">Start New Research</Button>
    </div>
  );
}

export default WorkflowDisplayPage; 