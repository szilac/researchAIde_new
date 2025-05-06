"""
Service for text chunking operations.
"""

from typing import List
from langchain_text_splitters import CharacterTextSplitter

def chunk_text_fixed_size(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Chunks the input text into fixed-size segments with a specified overlap
    using Langchain's CharacterTextSplitter.

    Args:
        text: The input text to chunk.
        chunk_size: The desired size of each chunk (in characters).
        overlap: The number of characters to overlap between consecutive chunks.

    Returns:
        A list of text chunks.

    Raises:
        ValueError: If chunk_size is not positive or overlap is negative or
                    greater than or equal to chunk_size.
    """
    if chunk_size <= 0:
        raise ValueError("Chunk size must be positive.")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("Overlap must be non-negative and less than chunk size.")
    if not text: # Handle empty string case directly
        return []

    # Use Langchain's CharacterTextSplitter
    text_splitter = CharacterTextSplitter(
        separator="", # Split by character
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        length_function=len,
        is_separator_regex=False, # Treat separator literally
    )

    chunks = text_splitter.split_text(text)
    return chunks

# Example usage (optional, for testing)
if __name__ == '__main__':
    sample_text = "This is a sample text for testing the chunking function. It needs to be long enough to demonstrate overlap."
    size = 20
    ovlp = 5
    try:
        result_chunks = chunk_text_fixed_size(sample_text, size, ovlp)
        print(f"Chunk Size: {size}, Overlap: {ovlp}")
        for i, chunk in enumerate(result_chunks):
            print(f"Chunk {i+1}: '{chunk}'")

        print("\nTesting edge case: text shorter than chunk size")
        short_text = "Short text."
        result_chunks_short = chunk_text_fixed_size(short_text, size, ovlp)
        for i, chunk in enumerate(result_chunks_short):
            print(f"Chunk {i+1}: '{chunk}'")

        print("\nTesting edge case: zero overlap")
        result_chunks_zero = chunk_text_fixed_size(sample_text, size, 0)
        print(f"Chunk Size: {size}, Overlap: 0")
        for i, chunk in enumerate(result_chunks_zero):
            print(f"Chunk {i+1}: '{chunk}'")

        print("\nTesting edge case: exact multiple length")
        multiple_text = "abcdefghij" * 2 # 20 chars
        result_chunks_mult = chunk_text_fixed_size(multiple_text, 10, 2)
        print(f"Chunk Size: 10, Overlap: 2")
        for i, chunk in enumerate(result_chunks_mult):
             print(f"Chunk {i+1}: '{chunk}'") # Expecting 'abcdefghij', 'ijklmnopqr' -> 'abcdefghij', 'ijabcdefgh'


    except ValueError as e:
        print(f"Error: {e}") 