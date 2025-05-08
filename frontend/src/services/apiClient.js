const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'; // Default to /api if not set

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