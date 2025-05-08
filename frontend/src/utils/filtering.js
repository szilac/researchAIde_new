/**
 * Filters an array of paper objects based on a search term.
 * The search term is matched against paper titles, authors, and abstracts (case-insensitive).
 * @param {Array<Object>} papers - The array of paper objects.
 * @param {string} searchTerm - The term to search for.
 * @returns {Array<Object>} The filtered array of papers.
 */
export function filterPapersByKeyword(papers, searchTerm) {
  if (!searchTerm) {
    return papers;
  }
  const lowerCaseSearchTerm = searchTerm.toLowerCase();
  return papers.filter(paper => {
    const titleMatch = paper.title?.toLowerCase().includes(lowerCaseSearchTerm);
    const authorsMatch = paper.authors?.some(author => author.toLowerCase().includes(lowerCaseSearchTerm));
    const abstractMatch = paper.abstract?.toLowerCase().includes(lowerCaseSearchTerm);
    return titleMatch || authorsMatch || abstractMatch;
  });
}

/**
 * Sorts an array of paper objects based on a specified key and order.
 * @param {Array<Object>} papers - The array of paper objects.
 * @param {string} sortBy - The key to sort by (e.g., 'title', 'date', 'relevance').
 * @param {'asc' | 'desc'} sortOrder - The order to sort in ('asc' or 'desc').
 * @returns {Array<Object>} The sorted array of papers.
 */
export function sortPapers(papers, sortBy, sortOrder) {
  if (!sortBy) {
    return papers;
  }

  return [...papers].sort((a, b) => {
    let valA = a[sortBy];
    let valB = b[sortBy];

    // Handle date sorting specifically if dates are strings
    if (sortBy === 'date') {
      valA = new Date(valA);
      valB = new Date(valB);
    }

    // Handle undefined or null values by pushing them to the end for both asc/desc
    if (valA == null && valB == null) return 0;
    if (valA == null) return 1; // a is null/undefined, comes after b
    if (valB == null) return -1; // b is null/undefined, comes after a

    let comparison = 0;
    if (typeof valA === 'string' && typeof valB === 'string') {
      comparison = valA.localeCompare(valB);
    } else if (valA < valB) {
      comparison = -1;
    } else if (valA > valB) {
      comparison = 1;
    }

    return sortOrder === 'desc' ? comparison * -1 : comparison;
  });
}
