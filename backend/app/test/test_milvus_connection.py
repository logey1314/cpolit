from pymilvus import connections, utility

from backend.app.core.vector_config import (
    MILVUS_HOST,
    MILVUS_PORT,
    MILVUS_USER,
    MILVUS_PASSWORD,
    MILVUS_TLS,
)


def test_milvus_connection():
    connections.connect(
        alias="default",
        host=MILVUS_HOST,
        port=MILVUS_PORT,
        user=MILVUS_USER,
        password=MILVUS_PASSWORD,
        secure=MILVUS_TLS,
    )

    collections = utility.list_collections()

    print("Milvus connected successfully")
    print("collections:", collections)

    connections.disconnect("default")


if __name__ == "__main__":
    test_milvus_connection()