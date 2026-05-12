from dataclasses import dataclass
from typing import Iterable

import numpy as np

from forge.embeddings.model import get_model


@dataclass
class ArtifactInfo:
  name: str
  kind: str
  summary: str
  path: str


def _encode(texts: Iterable[str]) -> list[np.ndarray]:
  model = get_model()
  embeddings = model.encode(list(texts), normalize_embeddings=True)
  return [embedding for embedding in embeddings]


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
  return float(np.dot(a, b))


def find_similar(target: ArtifactInfo, candidates: list[ArtifactInfo]) -> tuple[ArtifactInfo | None, float]:
  if not candidates:
    return None, 0.0
  texts = [target.summary] + [c.summary for c in candidates]
  embeddings = _encode(texts)
  target_vec = embeddings[0]
  best_score = 0.0
  best_candidate: ArtifactInfo | None = None
  for idx, candidate in enumerate(candidates, start=1):
    score = _cosine(target_vec, embeddings[idx])
    if score > best_score:
      best_score = score
      best_candidate = candidate
  return best_candidate, best_score
