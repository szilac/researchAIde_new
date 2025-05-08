// Base URL for the API - assumes Vite proxy or full URL
// In development, Vite proxy is often set up in vite.config.js
// For example: server: { proxy: { '/api': 'http://localhost:8000' } }
const API_BASE_URL = '/api/v1'; 

/**
 * Fetches the current paper shortlist from the backend.
 * @returns {Promise<Array<Object>>} A promise that resolves to the array of paper objects.
 */
async function getPaperShortlist() {
  const response = await fetch(`${API_BASE_URL}/papers/shortlist`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({})); // Try to get error details
    throw new Error(`Failed to fetch shortlist: ${response.statusText} (${response.status}) ${errorData.detail || ''}`);
  }
  return response.json();
}

/**
 * Updates the paper shortlist on the backend.
 * Typically sends the list of selected paper IDs for further processing.
 * @param {Array<string>} selectedPaperIds - An array of selected paper IDs.
 * @returns {Promise<Object>} A promise that resolves to the backend response.
 */
async function updatePaperShortlist(selectedPaperIds) {
  const response = await fetch(`${API_BASE_URL}/papers/shortlist`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ paperIds: selectedPaperIds }),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({})); 
    throw new Error(`Failed to update shortlist: ${response.statusText} (${response.status}) ${errorData.detail || ''}`);
  }
  return response.json();
}

/**
 * Adds a custom paper to the shortlist via the backend.
 * @param {Object} paperData - Data for the custom paper (e.g., { arxivId: '...' } or manual fields).
 * @returns {Promise<Object>} A promise that resolves to the added paper object or backend response.
 */
async function addCustomPaper(paperData) {
  const response = await fetch(`${API_BASE_URL}/papers/shortlist/custom`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(paperData),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(`Failed to add custom paper: ${response.statusText} (${response.status}) ${errorData.detail || ''}`);
  }
  return response.json();
}

export const paperService = {
  getPaperShortlist,
  updatePaperShortlist,
  addCustomPaper,
};
