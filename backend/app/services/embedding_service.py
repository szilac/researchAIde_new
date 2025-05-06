import logging
from typing import List
from sentence_transformers import SentenceTransformer
import torch # Sentence Transformers often relies on torch

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Service responsible for generating text embeddings using local models.
    Currently uses Sentence Transformers library.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initializes the EmbeddingService.

        Args:
            model_name (str): The name of the Sentence Transformer model to load.
                                Defaults to a popular and efficient model.
        """
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Initializing EmbeddingService with model: {self.model_name} on device: {self.device}")
        try:
            # Load the Sentence Transformer model
            self.model = SentenceTransformer(self.model_name, device=self.device)
            logger.info(f"Successfully loaded Sentence Transformer model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load Sentence Transformer model '{self.model_name}': {e}", exc_info=True)
            # Depending on requirements, could raise exception or disable the service
            self.model = None

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generates embeddings for a list of text strings.

        Args:
            texts (List[str]): A list of texts to embed.

        Returns:
            List[List[float]]: A list of embedding vectors, where each vector
                               corresponds to the text at the same index.
                               Returns an empty list if the model failed to load
                               or an error occurs during encoding.
        """
        if not self.model:
            logger.error("Embedding model not loaded. Cannot generate embeddings.")
            return []
        if not texts:
            logger.warning("Received empty list of texts for embedding.")
            return []

        logger.info(f"Generating embeddings for {len(texts)} text chunk(s)...")
        try:
            # Use the model's encode method
            # normalize_embeddings=True is often recommended for cosine similarity search
            embeddings = self.model.encode(texts, convert_to_tensor=False, normalize_embeddings=True)
            logger.info(f"Successfully generated {len(embeddings)} embeddings.")
            # Convert numpy arrays to lists of floats if needed
            return [embedding.tolist() for embedding in embeddings]
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}", exc_info=True)
            return []

    # Placeholder for future expansion (e.g., supporting cloud models)
    # def _get_cloud_embeddings(self, texts: List[str]):
    #     pass

# Example usage (for testing)
# if __name__ == '__main__':
#     service = EmbeddingService()
#     sample_texts = [
#         "This is the first document.",
#         "This document is about vector embeddings.",
#         "Sentence Transformers make embedding easy."
#     ]
#     embeddings_result = service.generate_embeddings(sample_texts)
#     if embeddings_result:
#         print(f"Generated {len(embeddings_result)} embeddings.")
#         print(f"Dimension of first embedding: {len(embeddings_result[0])}")
#     else:
#         print("Failed to generate embeddings.") 