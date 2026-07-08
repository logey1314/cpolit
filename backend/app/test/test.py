import redis


def main():
    client = redis.Redis(
        host="82.156.215.91",
        port=63368,
        password=None,
        db=0,
        socket_connect_timeout=5,
        socket_timeout=5,
        decode_responses=True
    )

    pong = client.ping()
    print("PING:", pong)

    client.set("test:redis:conn", "ok", ex=60)
    value = client.get("test:redis:conn")
    print("GET:", value)


if __name__ == "__main__":
    main()