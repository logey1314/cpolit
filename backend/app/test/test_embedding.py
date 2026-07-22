from openai import OpenAI

from backend.app.core.vector_config import (
    EMBEDDING_API_KEY,
    EMBEDDING_BASE_URL,
    EMBEDDING_MODEL,
)


def test_embedding():
    client = OpenAI(
        api_key=EMBEDDING_API_KEY,
        base_url=EMBEDDING_BASE_URL,
    )

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input="这是一条私域运营内容生成测试文本",
    )

    vector = response.data[0].embedding

    print("embedding success")
    print("dimension:", len(vector))
    print("first_5:", vector[:5])


if __name__ == "__main__":
    test_embedding()