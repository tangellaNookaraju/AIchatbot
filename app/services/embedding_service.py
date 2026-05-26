import os
import logging
from typing import List

logger = logging.getLogger("app.services.embedding_service")

class EmbeddingService:
    _model = None

    @classmethod
    def get_model(cls):
        """
        Lazily initialize the sentence-transformers model.
        """
        if cls._model is None:
            model_name = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
            logger.info(f"Initializing SentenceTransformer model: {model_name}...")
            try:
                # Import here to avoid loading it on startup if not used
                from sentence_transformers import SentenceTransformer
                cls._model = SentenceTransformer(model_name)
                logger.info("SentenceTransformer model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load SentenceTransformer model: {e}")
                raise e
        return cls._model

    @classmethod
    def get_embedding(cls, text: str) -> List[float]:
        """
        Generate embedding vector for the provided text.
        """
        try:
            model = cls.get_model()
            embedding = model.encode(text)
            # Ensure it is converted to a list of floats
            if hasattr(embedding, "tolist"):
                return embedding.tolist()
            return list(embedding)
        except Exception as e:
            logger.error(f"Error generating embedding for text: {e}")
            raise e
