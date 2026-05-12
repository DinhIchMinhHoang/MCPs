RULES = [
  (r"sk-[a-zA-Z0-9]{20,}", "<REDACTED_TOKEN>"),
  (r"AIza[0-9A-Za-z-_]{35}", "<REDACTED_TOKEN>"),
  (r"(?i)api[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9-_]{8,}['\"]?", "<REDACTED_TOKEN>"),
  (r"(?i)token\s*[:=]\s*['\"]?[A-Za-z0-9-_]{8,}['\"]?", "<REDACTED_TOKEN>"),
  (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "<REDACTED_EMAIL>"),
  (r"\b\d{1,3}(?:\.\d{1,3}){3}\b", "<REDACTED_IP>"),
  (r"[A-Za-z]:\\[^\s]+", "<REDACTED_PATH>"),
  (r"/[A-Za-z0-9_\-./]+", "<REDACTED_PATH>")
]
