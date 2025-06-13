"""
Encoder interface for the webscraper project.

This module defines the interface for encoding text into vector embeddings
in the crawler. It provides a protocol for implementing different encoding
strategies (e.g., sentence-transformers, OpenAI embeddings) while maintaining
a consistent interface.

Example:
    ```python
    class SentenceTransformerEncoder(Encoder):
        dim = 768  # BERT base dimension
        
        def encode(self, texts: List[str], normalize: bool = True) -> List[List[float]]:
            # Implementation here
            return [[0.1, 0.2, ...], [0.3, 0.4, ...]]
    ```
"""
from typing import Protocol, List

class Encoder(Protocol):
    """
    Interface for encoding text into vectors.
    
    This protocol defines the interface that all encoder implementations
    must follow. It allows for different embedding models while
    maintaining a consistent interface for text encoding.
    
    Attributes:
        dim: The dimensionality of the output vectors
        
    Example:
        ```python
        class OpenAIEncoder(Encoder):
            dim = 1536  # OpenAI ada-002 dimension
            
            def __init__(self, api_key: str):
                self.client = OpenAI(api_key=api_key)
                
            def encode(self, texts: List[str], normalize: bool = True) -> List[List[float]]:
                embeddings = self.client.embeddings.create(
                    input=texts,
                    model="text-embedding-ada-002"
                )
                return [e.embedding for e in embeddings.data]
        ```
    """
    dim: int  # vector length
    
    def encode(self, texts: List[str], normalize: bool = True) -> List[List[float]]:
        """
        Encode texts into vectors.
        
        This method should be implemented to convert a list of texts
        into their vector representations using the chosen embedding model.
        
        Args:
            texts: List of texts to encode
            normalize: Whether to normalize the output vectors to unit length
            
        Returns:
            List of vectors, where each vector is a list of floats
            
        Example:
            >>> encoder = MyEncoder()
            >>> texts = ["Hello world", "How are you"]
            >>> vectors = encoder.encode(texts)
            >>> len(vectors)
            2
            >>> len(vectors[0])
            768  # or whatever dim is set to
            >>> all(len(v) == encoder.dim for v in vectors)
            True
        """
        ... 