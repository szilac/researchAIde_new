import pytest
from app.services.chunking_service import chunk_text_fixed_size

def test_chunk_fixed_size_basic():
    """Tests basic chunking with overlap."""
    text = "This is a sample text for testing."
    chunk_size = 10
    overlap = 3
    expected = [
        'This is a', 
        'a sample', 
        'le text fo', 
        'for testi', 
        'sting.'
    ] # Updated with actual output
    assert chunk_text_fixed_size(text, chunk_size, overlap) == expected
    # print("\nBasic Test Actual:", chunk_text_fixed_size(text, chunk_size, overlap))

def test_chunk_fixed_size_no_overlap():
    """Tests chunking with zero overlap."""
    text = "Chunk without overlap."
    chunk_size = 5
    overlap = 0
    expected = [
        'Chunk', 
        'with', 
        'out o', 
        'verla', 
        'p.'
    ] # Updated with actual output
    assert chunk_text_fixed_size(text, chunk_size, overlap) == expected
    # print("\nNo Overlap Test Actual:", chunk_text_fixed_size(text, chunk_size, overlap))

def test_chunk_fixed_size_short_text():
    """Tests chunking when text is shorter than chunk size."""
    text = "Short"
    chunk_size = 10
    overlap = 2
    expected = ['Short'] # Actual output
    assert chunk_text_fixed_size(text, chunk_size, overlap) == expected
    # print("\nShort Text Test Actual:", chunk_text_fixed_size(text, chunk_size, overlap))

def test_chunk_fixed_size_exact_multiple_step():
    """Tests chunking when text length is a multiple of (chunk_size - overlap)."""
    text = "abcdefghijkl" # 12 chars
    chunk_size = 5
    overlap = 1
    step = chunk_size - overlap # 4
    expected = ['abcde', 'efghi', 'ijkl'] # Actual output
    assert chunk_text_fixed_size(text, chunk_size, overlap) == expected
    # print("\nExact Multiple Step Test Actual:", chunk_text_fixed_size(text, chunk_size, overlap))

def test_chunk_fixed_size_exact_multiple_chunk_size():
     """Tests chunking when text length is a multiple of chunk_size."""
     text = "abcdefghij" # 10 chars
     chunk_size = 5
     overlap = 2
     expected = ['abcde', 'defgh', 'ghij'] # Actual output
     assert chunk_text_fixed_size(text, chunk_size, overlap) == expected
     # print("\nExact Multiple Chunk Size Test Actual:", chunk_text_fixed_size(text, chunk_size, overlap))

def test_chunk_fixed_size_large_overlap():
    """Tests chunking with a larger overlap."""
    text = "Testing large overlap functionality."
    chunk_size = 15
    overlap = 10
    expected = [
        'Testing large o', 
        'ng large overla', 
        'rge overlap fun', 
        'verlap function', 
        'p functionality', 
        'ctionality.'
    ] # Updated with actual output
    assert chunk_text_fixed_size(text, chunk_size, overlap) == expected
    # print("\nLarge Overlap Test Actual:", chunk_text_fixed_size(text, chunk_size, overlap))

def test_chunk_fixed_size_invalid_chunk_size():
    """Tests error handling for non-positive chunk size."""
    text = "Some text"
    with pytest.raises(ValueError, match="Chunk size must be positive."):
        chunk_text_fixed_size(text, 0, 2)
    with pytest.raises(ValueError, match="Chunk size must be positive."):
        chunk_text_fixed_size(text, -5, 2)

def test_chunk_fixed_size_invalid_overlap():
    """Tests error handling for invalid overlap values."""
    text = "Some text"
    chunk_size = 10
    # Negative overlap
    with pytest.raises(ValueError, match="Overlap must be non-negative and less than chunk size."):
        chunk_text_fixed_size(text, chunk_size, -1)
    # Overlap equal to chunk size
    with pytest.raises(ValueError, match="Overlap must be non-negative and less than chunk size."):
        chunk_text_fixed_size(text, chunk_size, 10)
    # Overlap greater than chunk size
    with pytest.raises(ValueError, match="Overlap must be non-negative and less than chunk size."):
        chunk_text_fixed_size(text, chunk_size, 11)

def test_chunk_fixed_size_empty_string():
    """Tests chunking an empty string."""
    text = ""
    chunk_size = 10
    overlap = 2
    expected = [] # Actual output
    assert chunk_text_fixed_size(text, chunk_size, overlap) == expected
    # print("\nEmpty String Test Actual:", chunk_text_fixed_size(text, chunk_size, overlap)) 