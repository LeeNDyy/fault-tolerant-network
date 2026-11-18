FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-15 patroni python3-etcd gosu curl && rm -rf /var/lib/apt/lists/*
COPY entrypoint /usr/local/bin/
ENTRYPOINT ["sh", "/usr/local/bin/entrypoint"]
