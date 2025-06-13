"""
Text chunking utilities for the embedder.

This module provides functionality to split text into smaller chunks for embedding.
It uses the same tokenizer as OpenAI's GPT models (tiktoken) to ensure consistent
tokenization across different models.

The chunking process:
1. Encodes text into tokens using tiktoken
2. Splits tokens into chunks of specified size
3. Decodes chunks back into text
4. Filters out empty chunks

Example:
    ```python
    chunker = TextChunker(max_tokens=512)
    
    # Chunk a single text
    chunks = chunker.chunk_text("This is a long text...")
    
    # Chunk multiple texts
    for chunk in chunker.chunk_texts(["Text 1...", "Text 2..."]):
        print(chunk)
    ```
"""
import tiktoken
from typing import List, Iterator
from src.config.settings import MODEL_CONFIG

class TextChunker:
    """
    Splits text into chunks of specified token length.
    
    This class uses tiktoken to tokenize text and split it into chunks
    that are suitable for embedding models. It ensures that chunks are
    tokenized consistently with OpenAI's models.
    
    Attributes:
        max_tokens: Maximum number of tokens per chunk
        encoder: The tiktoken encoder for tokenization
    """
    
    def __init__(self, max_tokens: int = MODEL_CONFIG["chunk_tokens"]):
        """
        Initialize the chunker with specified token limit.
        
        Args:
            max_tokens: Maximum number of tokens per chunk (default from MODEL_CONFIG)
            
        Example:
            >>> chunker = TextChunker(max_tokens=512)
            >>> chunker.max_tokens
            512
        """
        self.max_tokens = max_tokens
        self.encoder = tiktoken.get_encoding("cl100k_base")  # same as OpenAI tiktoken

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks of max_tokens length.
        
        This method:
        1. Encodes the text into tokens
        2. Splits tokens into chunks of max_tokens size
        3. Decodes chunks back into text
        4. Filters out empty chunks
        
        Args:
            text: The text to split into chunks
            
        Returns:
            List of text chunks, each containing at most max_tokens tokens
            
        Example:
            >>> chunker = TextChunker(max_tokens=5)
            >>> chunker.chunk_text("This is a longer text that will be split")
            ['This is a longer', 'text that will', 'be split']
        """
        if not text:
            return []
            
        ids = self.encoder.encode(text)
        chunks = []
        for i in range(0, len(ids), self.max_tokens):
            chunk = self.encoder.decode(ids[i : i + self.max_tokens]).strip()
            if chunk:  # Only add non-empty chunks
                chunks.append(chunk)
        return chunks

    def chunk_texts(self, texts: List[str]) -> Iterator[str]:
        """
        Split multiple texts into chunks.
        
        This method processes a list of texts and yields chunks one at a time.
        It's useful for processing large collections of texts efficiently.
        
        Args:
            texts: List of texts to split into chunks
            
        Yields:
            Individual text chunks
            
        Example:
            >>> chunker = TextChunker(max_tokens=5)
            >>> texts = ["First text", "Second text"]
            >>> list(chunker.chunk_texts(texts))
            ['First text', 'Second text']
        """
        for text in texts:
            yield from self.chunk_text(text) 