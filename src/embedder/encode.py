"""
Minimal embed pass that uses Storage + Encoder interfaces.
"""
from tqdm import tqdm
from src.config import STORAGE_CLS, ENCODER_CLS, DB

BATCH = 64
storage = STORAGE_CLS(DB)
encoder = ENCODER_CLS()

# 1️⃣ pages needing vectors
targets = storage.pages_for_embedding()   # you'll add this method next

for url, clean_texts in tqdm(targets, desc="Pages"):
    if clean_texts is None:
        continue
    chunks = [clean_texts[i:i+500] for i in range(0, len(clean_texts), 500)]
    vecs   = encoder.encode(chunks)
    storage.save_vectors(url, vecs)       # to implement next