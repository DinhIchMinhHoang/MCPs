import os
from functools import lru_cache
from sentence_transformers import SentenceTransformer


def _configure_cache() -> None:
  cache_path = "D:\\02_Data_Vault\\.cache\\huggingface"
  os.environ.setdefault("HF_HOME", cache_path)
  os.environ.setdefault("TRANSFORMERS_CACHE", cache_path)


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
  _configure_cache()
  return SentenceTransformer("all-MiniLM-L6-v2")
