from openai import OpenAI
from pymilvus import MilvusClient

from app.core.vector_config import (
    EMBEDDING_API_KEY,
    EMBEDDING_BASE_URL,
    EMBEDDING_MODEL,
    MILVUS_HOST,
    MILVUS_PASSWORD,
    MILVUS_PORT,
    MILVUS_TLS,
    MILVUS_USER,
)


KNOWLEDGE_COLLECTIONS = [
    "product_knowledge",
    "activity_rules",
    "brand_guidelines",
    "operation_sop",
]


def get_embedding_client():
    return OpenAI(
        api_key=EMBEDDING_API_KEY,
        base_url=EMBEDDING_BASE_URL,
    )


def get_milvus_client():
    protocol = "https" if MILVUS_TLS else "http"
    uri = f"{protocol}://{MILVUS_HOST}:{MILVUS_PORT}"

    return MilvusClient(
        uri=uri,
        token=f"{MILVUS_USER}:{MILVUS_PASSWORD}",
    )


def embed_text(text: str):
    client = get_embedding_client()
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


def search_knowledge_collection(
    client: MilvusClient,
    collection_name: str,
    query: str,
    limit: int = 3,
):
    if not client.has_collection(collection_name):
        return []

    results = client.search(
        collection_name=collection_name,
        data=[embed_text(query)],
        anns_field="embedding",
        search_params={"metric_type": "COSINE", "params": {}},
        limit=limit,
        output_fields=[
            "doc_name",
            "knowledge_type",
            "chunk_title",
            "content",
            "version",
            "source_path",
        ],
    )

    rows = []
    for hit in results[0]:
        entity = hit.get("entity", {})
        rows.append({
            "collection": collection_name,
            "score": hit.get("distance"),
            "doc_name": entity.get("doc_name"),
            "knowledge_type": entity.get("knowledge_type"),
            "chunk_title": entity.get("chunk_title"),
            "content": entity.get("content"),
            "version": entity.get("version"),
            "source_path": entity.get("source_path"),
        })

    return rows


def search_all_knowledge(query: str):
    client = get_milvus_client()

    try:
        result = {}
        for collection_name in KNOWLEDGE_COLLECTIONS:
            result[collection_name] = search_knowledge_collection(
                client=client,
                collection_name=collection_name,
                query=query,
                limit=3,
            )
        return result
    finally:
        client.close()


def search_content_examples(query: str, content_type: str, limit: int = 3):
    client = get_milvus_client()

    try:
        if not client.has_collection("content_examples"):
            return []

        results = client.search(
            collection_name="content_examples",
            data=[embed_text(query)],
            anns_field="embedding",
            search_params={"metric_type": "COSINE", "params": {}},
            filter=f'content_type == "{content_type}"',
            limit=limit,
            output_fields=[
                "content_text",
                "content_type",
                "segment_type",
                "source",
                "created_at",
            ],
        )

        rows = []
        for hit in results[0]:
            entity = hit.get("entity", {})
            rows.append({
                "score": hit.get("distance"),
                "content_text": entity.get("content_text"),
                "content_type": entity.get("content_type"),
                "segment_type": entity.get("segment_type"),
                "source": entity.get("source"),
                "created_at": entity.get("created_at"),
            })

        return rows
    finally:
        client.close()
