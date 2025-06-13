"""
MPNet-based implementation of the Encoder interface.

This module provides a text encoder implementation using the MPNet model
from sentence-transformers. MPNet is a pre-trained language model that
produces high-quality sentence embeddings.

Example:
    ```python
    # Create an encoder with default MPNet model
    encoder = MpnetEncoder()
    
    # Encode some texts
    texts = ["Hello world", "How are you"]
    vectors = encoder.encode(texts)
    
    # Each vector will be 768-dimensional
    assert len(vectors[0]) == 768
    ```
"""
from sentence_transformers import SentenceTransformer
from src.core.interfaces.encoder import Encoder
from typing import List

class MpnetEncoder(Encoder):
    """
    MPNet-based text encoder.
    
    This implementation uses the MPNet model from sentence-transformers
    to convert text into fixed-dimensional vectors. MPNet is particularly
    good at capturing semantic meaning in text.
    
    Attributes:
        dim: The dimensionality of the output vectors (768 for MPNet base)
        _model: The underlying sentence-transformers model
        
    Example:
        ```python
        # Create encoder with custom model
        encoder = MpnetEncoder("sentence-transformers/all-mpnet-base-v2")
        
        # Encode a single text
        vector = encoder.encode(["Hello world"])[0]
        print(f"Vector dimension: {len(vector)}")  # 768
        ```
    """
    dim = 768
    
    def __init__(self, model_name: str = "sentence-transformers/all-mpnet-base-v2"):
        """
        Initialize the MPNet encoder.
        
        Args:
            model_name: Name of the sentence-transformers model to use
                       (default: all-mpnet-base-v2)
                       
        Example:
            >>> encoder = MpnetEncoder()
            >>> encoder.dim
            768
        """
        self._model = SentenceTransformer(model_name)
        
    def encode(self, texts: List[str], normalize: bool = True) -> List[List[float]]:
        """
        Encode texts into vectors using MPNet.
        
        This method:
        1. Takes a list of texts
        2. Encodes them using the MPNet model
        3. Optionally normalizes the vectors
        4. Returns them as a list of lists
        
        Args:
            texts: List of texts to encode
            normalize: Whether to normalize vectors to unit length (default: True)
            
        Returns:
            List of 768-dimensional vectors
            
        Example:
            >>> encoder = MpnetEncoder()
            >>> texts = ["Hello world", "How are you"]
            >>> vectors = encoder.encode(texts)
            >>> len(vectors)
            2
            >>> len(vectors[0])
            768
            >>> # Vectors are normalized by default
            >>> sum(x*x for x in vectors[0])
            1.0
        """
        return self._model.encode(
            texts,
            normalize_embeddings=normalize,
            show_progress_bar=False
        ).tolist() 