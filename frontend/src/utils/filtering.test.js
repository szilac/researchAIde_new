import { describe, it, expect } from 'vitest';
import { filterPapersByKeyword, sortPapers } from './filtering';

const mockPapers = [
  { id: '1', title: 'Paper A about AI', authors: ['Author X'], date: '2023-01-15', relevance: 90, abstract: 'An abstract discussing artificial intelligence.' },
  { id: '2', title: 'Paper B on Machine Learning', authors: ['Author Y', 'Author Z'], date: '2022-11-20', relevance: 85, abstract: 'Focuses on ML techniques.' },
  { id: '3', title: 'Another AI Paper', authors: ['Author X'], date: '2024-03-10', relevance: 95, abstract: 'More details on AI progress.' },
  { id: '4', title: 'Data Science Methods', authors: ['Author A'], date: '2023-05-01', relevance: 80, abstract: 'Discusses data analysis.' },
  { id: '5', title: 'Paper without Author', date: '2021-01-01', relevance: 70, abstract: 'Old paper.' },
  { id: '6', title: 'Machine Concepts', authors: ['Author B'], date: '2023-12-31', relevance: 88, abstract: 'Deep dive into machines.' },
];

describe('filterPapersByKeyword', () => {
  it('should return all papers if searchTerm is empty', () => {
    expect(filterPapersByKeyword(mockPapers, '')).toEqual(mockPapers);
  });

  it('should filter by title (case-insensitive)', () => {
    const result = filterPapersByKeyword(mockPapers, 'machine');
    expect(result).toHaveLength(2);
    expect(result.map(p => p.id)).toEqual(expect.arrayContaining(['2', '6']));
  });

  it('should filter by author (case-insensitive)', () => {
    const result = filterPapersByKeyword(mockPapers, 'author x');
    expect(result).toHaveLength(2);
    expect(result.map(p => p.id)).toEqual(expect.arrayContaining(['1', '3']));
  });

  it('should filter by abstract (case-insensitive)', () => {
    const result = filterPapersByKeyword(mockPapers, 'techniques');
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe('2');
  });

  it('should return multiple matches across fields', () => {
    const result = filterPapersByKeyword(mockPapers, 'ai');
    expect(result).toHaveLength(2);
    expect(result.map(p => p.id)).toEqual(expect.arrayContaining(['1', '3']));
  });

  it('should return empty array if no match', () => {
    const result = filterPapersByKeyword(mockPapers, 'nonexistent');
    expect(result).toHaveLength(0);
  });
  
  it('should handle papers without authors', () => {
    const result = filterPapersByKeyword(mockPapers, 'author'); // Should not crash
    expect(result.map(p => p.id)).toEqual(expect.arrayContaining(['1', '3', '4', '6']));
  });
});

describe('sortPapers', () => {
  it('should sort by title ascending', () => {
    const result = sortPapers(mockPapers, 'title', 'asc');
    expect(result.map(p => p.id)).toEqual(['3', '4', '6', '1', '2', '5']);
  });

  it('should sort by title descending', () => {
    const result = sortPapers(mockPapers, 'title', 'desc');
    expect(result.map(p => p.id)).toEqual(['5', '2', '1', '6', '4', '3']);
  });

  it('should sort by date ascending (oldest first)', () => {
    const result = sortPapers(mockPapers, 'date', 'asc');
    expect(result.map(p => p.id)).toEqual(['5', '2', '1', '4', '6', '3']);
  });

  it('should sort by date descending (newest first)', () => {
    const result = sortPapers(mockPapers, 'date', 'desc');
    expect(result.map(p => p.id)).toEqual(['3', '6', '4', '1', '2', '5']);
  });

  it('should sort by relevance ascending', () => {
    const result = sortPapers(mockPapers, 'relevance', 'asc');
    expect(result.map(p => p.id)).toEqual(['5', '4', '2', '6', '1', '3']);
  });

  it('should sort by relevance descending', () => {
    const result = sortPapers(mockPapers, 'relevance', 'desc');
    expect(result.map(p => p.id)).toEqual(['3', '1', '6', '2', '4', '5']);
  });

  it('should handle missing sort key gracefully (pushing null/undefined to end)', () => {
    const papersWithMissing = [
      ...mockPapers,
      { id: '7', title: 'Missing Relevance', date: '2020-01-01', abstract: '...' },
    ];
    const resultAsc = sortPapers(papersWithMissing, 'relevance', 'asc');
    expect(resultAsc.map(p => p.id)).toEqual(['5', '4', '2', '6', '1', '3', '7']);
    const resultDesc = sortPapers(papersWithMissing, 'relevance', 'desc');
    expect(resultDesc.map(p => p.id)).toEqual(['3', '1', '6', '2', '4', '5', '7']);
  });

  it('should return original array if sortBy is empty', () => {
    const result = sortPapers(mockPapers, '', 'asc');
    expect(result).toEqual(mockPapers); // Should be the original array reference if no sort performed
    expect(result === mockPapers).toBe(true); // Check reference equality
  });
});
