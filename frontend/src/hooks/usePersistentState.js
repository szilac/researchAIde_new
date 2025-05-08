import { useState, useEffect } from 'react';

function usePersistentState(key, initialValue) {
  // Get initial state from localStorage or use the provided initialValue
  const [state, setState] = useState(() => {
    try {
      const storedValue = localStorage.getItem(key);
      return storedValue ? JSON.parse(storedValue) : initialValue;
    } catch (error) {
      console.error(`Error reading localStorage key \"${key}\":`, error);
      return initialValue;
    }
  });

  // Update localStorage whenever the state changes
  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(state));
    } catch (error) {
      console.error(`Error setting localStorage key \"${key}\":`, error);
    }
  }, [key, state]);

  return [state, setState];
}

export default usePersistentState; 