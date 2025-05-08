import { apiClient } from './apiClient';

const SESSION_ENDPOINT = '/v1/sessions'; // Assuming v1 endpoint under /api base

/**
 * Creates a new research session on the backend.
 * 
 * @param {object} sessionData - The data for the new session.
 * @param {string} sessionData.llmProvider - The selected LLM provider.
 * @param {string} sessionData.llmModelId - The selected LLM model ID.
 * @param {string} sessionData.researchArea - General research area.
 * @param {string} sessionData.researchTopic - Focused research topic.
 * @param {string} [sessionData.researchContext] - Optional additional context.
 * @returns {Promise<object>} - A promise that resolves to the created session data (e.g., { sessionId: '123', ... }).
 * @throws {Error} - Throws an error if the API call fails.
 */
const createSession = async (sessionData) => {
  try {
    console.log('Creating session with data:', sessionData);
    // Adapt the payload structure if needed based on actual backend requirements
    const payload = {
      llm_provider: sessionData.llmProvider,
      llm_model_id: sessionData.llmModelId,
      research_area: sessionData.researchArea,
      research_topic: sessionData.researchTopic,
      research_context: sessionData.researchContext,
      // Add any other required fields like user ID if applicable
    };
    const createdSession = await apiClient.post(SESSION_ENDPOINT, payload);
    console.log('Session created successfully:', createdSession);
    return createdSession; // Should contain sessionId, etc.
  } catch (error) {
    console.error('Failed to create session:', error);
    // Re-throw the error to be handled by the calling component
    throw new Error(error.message || 'Failed to create research session. Please try again.');
  }
};

// Add other session-related service functions here later
// e.g., getSessionStatus, updateSessionTopic, etc.

export const SessionService = {
  createSession,
}; 