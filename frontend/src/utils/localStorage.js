/**
 * Saves a value to local storage after converting it to JSON.
 * @param {string} key The key under which to store the value.
 * @param {*} value The value to store (will be JSON.stringify'd).
 */
export function saveToLocalStorage(key, value) {
  try {
    const serializedValue = JSON.stringify(value);
    localStorage.setItem(key, serializedValue);
  } catch (error) {
    console.error(`Error saving key "${key}" to localStorage:`, error);
  }
}

/**
 * Loads a value from local storage.
 * @param {string} key The key of the item to retrieve.
 * @param {*} defaultValue The default value to return if the key is not found or parsing fails.
 * @returns {*} The retrieved value, parsed from JSON, or the defaultValue.
 */
export function loadFromLocalStorage(key, defaultValue = null) {
  try {
    const serializedValue = localStorage.getItem(key);
    if (serializedValue === null) {
      return defaultValue;
    }
    return JSON.parse(serializedValue);
  } catch (error) {
    console.error(`Error loading key "${key}" from localStorage:`, error);
    return defaultValue;
  }
}
