const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'; // Default to /api/v1 if not set

async function request(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  const defaultHeaders = {
    'Content-Type': 'application/json',
    // Add other default headers here, like Authorization if needed
  };

  const config = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  };

  try {
    const response = await fetch(url, config);
    if (!response.ok) {
      // Try to parse error response, otherwise use statusText
      let errorData;
      try {
        errorData = await response.json();
      } catch (e) {
        // Ignore if error response is not JSON
      }
      const errorMessage = errorData?.message || errorData?.error || response.statusText;
      const error = new Error(`API Error (${response.status}): ${errorMessage}`);
      error.status = response.status;
      error.data = errorData; 
      throw error;
    }
    // If response is OK but has no content (e.g., 204 No Content)
    if (response.status === 204 || response.headers.get('content-length') === '0') {
      return null; // Or undefined, or an empty object, depending on preference
    }
    return response.json();
  } catch (error) {
    console.error('API request failed:', error);
    // Re-throw the error so it can be caught by the calling function
    // This allows for specific error handling in components/hooks
    throw error;
  }
}

export const apiClient = {
  get: (endpoint, options) => request(endpoint, { ...options, method: 'GET' }),
  post: (endpoint, body, options) => request(endpoint, { ...options, method: 'POST', body: JSON.stringify(body) }),
  put: (endpoint, body, options) => request(endpoint, { ...options, method: 'PUT', body: JSON.stringify(body) }),
  delete: (endpoint, options) => request(endpoint, { ...options, method: 'DELETE' }),
  patch: (endpoint, body, options) => request(endpoint, { ...options, method: 'PATCH', body: JSON.stringify(body) }),
};

// Example usage (can be removed or kept for reference):
/*
async function fetchExampleData() {
  try {
    const data = await apiClient.get('/example-endpoint');
    console.log('Fetched data:', data);
  } catch (error) {
    console.error('Failed to fetch example data:', error.message, error.status, error.data);
  }
}

async function postExampleData() {
  try {
    const newData = { name: 'Test Item', value: 123 };
    const createdData = await apiClient.post('/example-endpoint', newData);
    console.log('Created data:', createdData);
  } catch (error) {
    console.error('Failed to post example data:', error.message, error.status, error.data);
  }
}
*/

// --- Orchestration Workflow Endpoints ---

/**
 * Starts a new research workflow.
 * @param {string} researchQuery - The main research topic.
 * @param {string|null} initialPrompt - Optional initial prompt for PhD agent.
 * @param {string|null} userId - Optional user identifier.
 * @param {string|null} sessionId - Optional session UUID to use; one will be generated if null.
 * @param {Object|null} configParameters - Optional configuration parameters (e.g., { hitl_shortlist_review_active: true }).
 * @returns {Promise<Object>} - The initial response containing workflow_id.
 */
export const startWorkflow = async (researchQuery, initialPrompt = null, userId = null, sessionId = null, configParameters = null) => {
  const payload = {
    research_query: researchQuery,
    initial_phd_prompt: initialPrompt,
    user_id: userId,
    session_id: sessionId, // Backend handles null and generates if needed
    config_parameters: configParameters,
  };
  // Filter out null values from payload if needed by backend (assuming backend handles nulls)
  // Object.keys(payload).forEach(key => payload[key] == null && delete payload[key]);

  try {
    const response = await apiClient.post('/orchestration/workflows/', payload);
    // Expects 202 Accepted
    if (response.status !== 202) {
      console.error('Error starting workflow:', response.status, response.data);
      throw new Error(`Failed to start workflow: ${response.status}`);
    }
    return response.data; // { workflow_id, status, message }
  } catch (error) {
    console.error('API Error starting workflow:', error.response?.data || error.message);
    throw error;
  }
};

/**
 * Gets the current status of a workflow.
 * @param {string} workflowId - The UUID of the workflow.
 * @returns {Promise<Object>} - The workflow status response.
 */
export const getWorkflowStatus = async (workflowId) => {
  if (!workflowId) throw new Error('Workflow ID is required');
  try {
    const response = await apiClient.get(`/orchestration/workflows/${workflowId}`);
    return response.data; // WorkflowStatusResponse
  } catch (error) {
    if (error.response?.status === 404) {
       console.log(`Workflow ${workflowId} not found.`);
       // Return a specific structure or re-throw a typed error for handling
       return { workflow_outcome: 'not_found' }; 
    } 
    console.error(`API Error fetching status for workflow ${workflowId}:`, error.response?.data || error.message);
    throw error;
  }
};

/**
 * Submits the confirmed papers for shortlist review.
 * @param {string} workflowId - The UUID of the workflow.
 * @param {Array<Object>} confirmedPapers - List of confirmed paper objects.
 * @returns {Promise<Object>} - The response indicating review submission.
 */
export const submitShortlistReview = async (workflowId, confirmedPapers) => {
  if (!workflowId) throw new Error('Workflow ID is required');
  if (!Array.isArray(confirmedPapers)) throw new Error('confirmedPapers must be an array');
  try {
    const payload = { confirmed_papers: confirmedPapers };
    const response = await apiClient.post(`/orchestration/workflows/${workflowId}/shortlist_review`, payload);
    return response.data; // { workflow_id, workflow_outcome: 'resuming_after_review', ... }
  } catch (error) {
    console.error(`API Error submitting review for workflow ${workflowId}:`, error.response?.data || error.message);
    throw error;
  }
};

/**
 * Gets the final results of a completed workflow.
 * Note: This currently calls the same endpoint as getWorkflowStatus.
 * The calling code should check the workflow_outcome.
 * @param {string} workflowId - The UUID of the workflow.
 * @returns {Promise<Object>} - The workflow status response, potentially containing final results.
 */
export const getWorkflowResults = async (workflowId) => {
  // Currently identical to getWorkflowStatus, as the results endpoint returns the status response
  // Frontend logic will need to check response.workflow_outcome === 'success' and access payload.final_report
  return getWorkflowStatus(workflowId);
};

// Make sure to export the new functions if this is a module
// export { fetchPapers, ..., startWorkflow, getWorkflowStatus, submitShortlistReview, getWorkflowResults }; 