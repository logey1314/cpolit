from datetime import datetime
from pathlib import Path

from openai import OpenAI
from pymilvus import DataType, MilvusClient

from backend.app.core.vector_config import (
    MILVUS_HOST,
    MILVUS_PORT,
    MILVUS_USER,
    MILVUS_PASSWORD,
    MILVUS_TLS,
    EMBEDDING_API_KEY,
    EMBEDDING_BASE_URL,
    EMBEDDING_MODEL,
)

DOC_DIR = Path(__file__).resolve().parents[1] / "rag" / "doc"

COLLECTION_CONFIGS = {
    "product_knowledge": {
        "file_name": "产品手册 v2.md",
        "knowledge_type": "product",
        "version": "v2",
    },
    "activity_rules": {
        "file_name": "活动说明-7月美妆节.md",
        "knowledge_type": "activity",
        "version": "2026-07",
    },
    "brand_guidelines": {
        "file_name": "品牌规范.md",
        "knowledge_type": "brand",
        "version": "current",
    },
    "operation_sop": {
        "file_name": "社群sop.md",
        "knowledge_type": "sop",
        "version": "current",
    },
}


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


def create_knowledge_collection(client: MilvusClient, collection_name: str, embedding_dim: int):
    if client.has_collection(collection_name):
        client.drop_collection(collection_name)

    schema = MilvusClient.create_schema(
        auto_id=True,
        enable_dynamic_field=False,
    )

    schema.add_field(
        field_name="id",
        datatype=DataType.INT64,
        is_primary=True,
        auto_id=True,
    )
    schema.add_field(
        field_name="doc_name",
        datatype=DataType.VARCHAR,
        max_length=128,
    )
    schema.add_field(
        field_name="knowledge_type",
        datatype=DataType.VARCHAR,
        max_length=32,
    )
    schema.add_field(
        field_name="chunk_title",
        datatype=DataType.VARCHAR,
        max_length=128,
    )
    schema.add_field(
        field_name="content",
        datatype=DataType.VARCHAR,
        max_length=4000,
    )
    schema.add_field(
        field_name="version",
        datatype=DataType.VARCHAR,
        max_length=32,
    )
    schema.add_field(
        field_name="source_path",
        datatype=DataType.VARCHAR,
        max_length=512,
    )
    schema.add_field(
        field_name="created_at",
        datatype=DataType.VARCHAR,
        max_length=32,
    )
    schema.add_field(
        field_name="embedding",
        datatype=DataType.FLOAT_VECTOR,
        dim=embedding_dim,
    )

    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="embedding",
        index_type="AUTOINDEX",
        metric_type="COSINE",
    )

    client.create_collection(
        collection_name=collection_name,
        schema=schema,
        index_params=index_params,
    )

    client.load_collection(collection_name)


def read_doc(file_name: str):
    file_path = DOC_DIR / file_name

    if not file_path.exists():
        raise FileNotFoundError(f"文档不存在: {file_path}")

    return file_path.read_text(encoding="utf-8")


def split_markdown_to_chunks(text: str):
    lines = text.splitlines()

    chunks = []
    current_title = "文档开头"
    current_lines = []

    for line in lines:
        clean_line = line.strip()

        if not clean_line:
            continue

        is_title = (
            clean_line.startswith("#")
            or clean_line.startswith("第")
            or clean_line.endswith("概述")
            or clean_line.endswith("规则")
            or clean_line.endswith("事项")
            or clean_line.endswith("流程")
            or clean_line.endswith("要求")
        )

        if is_title and current_lines:
            chunks.append(
                {
                    "title": current_title[:128],
                    "content": "\n".join(current_lines),
                }
            )
            current_title = clean_line.replace("#", "").strip()
            current_lines = [clean_line]
        else:
            if is_title:
                current_title = clean_line.replace("#", "").strip()
            current_lines.append(clean_line)

    if current_lines:
        chunks.append(
            {
                "title": current_title[:128],
                "content": "\n".join(current_lines),
            }
        )

    return [chunk for chunk in chunks if len(chunk["content"]) >= 10]


def ingest_one_collection(client: MilvusClient, collection_name: str, embedding_dim: int, config: dict):
    create_knowledge_collection(client, collection_name, embedding_dim)

    file_name = config["file_name"]
    text = read_doc(file_name)
    chunks = split_markdown_to_chunks(text)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rows = []
    for chunk in chunks:
        content = chunk["content"][:4000]

        rows.append(
            {
                "doc_name": file_name,
                "knowledge_type": config["knowledge_type"],
                "chunk_title": chunk["title"],
                "content": content,
                "version": config["version"],
                "source_path": str(DOC_DIR / file_name),
                "created_at": now,
                "embedding": embed_text(content),
            }
        )

    result = client.insert(
        collection_name=collection_name,
        data=rows,
    )

    print(f"{collection_name} inserted:", result["insert_count"])


def search_collection(client: MilvusClient, collection_name: str, query: str, limit: int = 3):
    query_vector = embed_text(query)

    results = client.search(
        collection_name=collection_name,
        data=[query_vector],
        anns_field="embedding",
        search_params={
            "metric_type": "COSINE",
            "params": {},
        },
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

    print()
    print(f"search {collection_name}: {query}")

    for hit in results[0]:
        entity = hit.get("entity", {})
        print("-" * 50)
        print("score:", hit.get("distance"))
        print("doc_name:", entity.get("doc_name"))
        print("version:", entity.get("version"))
        print("chunk_title:", entity.get("chunk_title"))
        print("content:", entity.get("content")[:200])


def main():
    test_vector = embed_text("测试向量维度")
    embedding_dim = len(test_vector)

    print("embedding dimension:", embedding_dim)
    print("doc dir:", DOC_DIR)

    client = get_milvus_client()

    for collection_name, config in COLLECTION_CONFIGS.items():
        ingest_one_collection(
            client=client,
            collection_name=collection_name,
            embedding_dim=embedding_dim,
            config=config,
        )

    search_collection(
        client=client,
        collection_name="product_knowledge",
        query="敏感肌 精华液 价格 使用方法",
    )
    search_collection(
        client=client,
        collection_name="activity_rules",
        query="7月美妆节 满减 活动 限量",
    )
    search_collection(
        client=client,
        collection_name="brand_guidelines",
        query="私聊话术 品牌语气 禁用词",
    )
    search_collection(
        client=client,
        collection_name="operation_sop",
        query="高意向用户 私聊跟进 社群运营",
    )

    print()
    print("collections:", client.list_collections())

    client.close()


if __name__ == "__main__":
    main()