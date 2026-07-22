import os
from dotenv import load_dotenv

load_dotenv()

MILVUS_HOST = os.getenv("MILVUS_HOST")
MILVUS_PORT = os.getenv("MILVUS_PORT")
MILVUS_USER = os.getenv("MILVUS_USER")
MILVUS_PASSWORD = os.getenv("MILVUS_PASSWORD")
MILVUS_TLS = os.getenv("MILVUS_TLS", "false").lower() == "true"

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL")