from datetime import datetime

from openai import OpenAI
from pymilvus import MilvusClient, DataType

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

COLLECTION_NAME = "content_examples"


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


def recreate_collection(client: MilvusClient, embedding_dim: int):
    if client.has_collection(COLLECTION_NAME):
        client.drop_collection(COLLECTION_NAME)

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
        field_name="content_text",
        datatype=DataType.VARCHAR,
        max_length=2000,
    )
    schema.add_field(
        field_name="content_type",
        datatype=DataType.VARCHAR,
        max_length=32,
    )
    schema.add_field(
        field_name="segment_type",
        datatype=DataType.VARCHAR,
        max_length=32,
    )
    schema.add_field(
        field_name="source",
        datatype=DataType.VARCHAR,
        max_length=64,
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
        collection_name=COLLECTION_NAME,
        schema=schema,
        index_params=index_params,
    )

    client.load_collection(COLLECTION_NAME)


def insert_mock_examples(client: MilvusClient):
    mock_examples = [
        {
            "content_text": "您好，看到您最近比较关注价格和活动，我这边可以帮您整理一下当前优惠和适合您的组合。",
            "content_type": "私聊话术",
            "segment_type": "高意向",
            "source": "模拟导入",
        },
        {
            "content_text": "最近很多朋友都在问敏感肌怎么选护肤品，大家可以聊聊自己更关注成分、价格还是使用感。",
            "content_type": "社群话题",
            "segment_type": "活动关注",
            "source": "模拟导入",
        },
        {
            "content_text": "您之前购买过这个系列，如果用完感觉合适，现在可以关注一下复购活动。",
            "content_type": "私聊话术",
            "segment_type": "已购",
            "source": "模拟导入",
        },
        {
            "content_text": "今天有一个限时活动提醒，适合之前咨询过但还没下单的朋友了解一下。",
            "content_type": "活动提醒",
            "segment_type": "待培育",
            "source": "模拟导入",
        },
        {
            "content_text": "近期先不主动打扰您，如果后面有需要，我再帮您整理资料。",
            "content_type": "私聊话术",
            "segment_type": "暂缓触达",
            "source": "模拟导入",
        },
    ]

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rows = []
    for item in mock_examples:
        rows.append(
            {
                "content_text": item["content_text"],
                "content_type": item["content_type"],
                "segment_type": item["segment_type"],
                "source": item["source"],
                "created_at": now,
                "embedding": embed_text(item["content_text"]),
            }
        )

    result = client.insert(
        collection_name=COLLECTION_NAME,
        data=rows,
    )

    print("insert result:", result)


def search_examples(client: MilvusClient):
    query = "用户咨询价格，近期有购买意向，适合私聊跟进"
    query_vector = embed_text(query)

    results = client.search(
        collection_name=COLLECTION_NAME,
        data=[query_vector],
        anns_field="embedding",
        search_params={
            "metric_type": "COSINE",
            "params": {},
        },
        limit=3,
        output_fields=[
            "content_text",
            "content_type",
            "segment_type",
            "source",
            "created_at",
        ],
    )

    print("query:", query)
    print("search results:")

    for hit in results[0]:
        entity = hit.get("entity", {})
        print("-" * 50)
        print("score:", hit.get("distance"))
        print("content_type:", entity.get("content_type"))
        print("segment_type:", entity.get("segment_type"))
        print("content_text:", entity.get("content_text"))
        print("source:", entity.get("source"))


def main():
    test_vector = embed_text("测试向量维度")
    embedding_dim = len(test_vector)

    print("embedding dimension:", embedding_dim)

    client = get_milvus_client()

    recreate_collection(client, embedding_dim)
    print("collection created:", COLLECTION_NAME)

    insert_mock_examples(client)
    print("mock examples inserted")

    search_examples(client)

    client.close()


if __name__ == "__main__":
    main()