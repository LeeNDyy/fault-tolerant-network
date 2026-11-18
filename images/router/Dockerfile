FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends iproute2 keepalived isc-dhcp-relay iptables iputils-ping && rm -rf /var/lib/apt/lists/*
COPY entrypoint relay-state /usr/local/bin/
ENTRYPOINT ["sh", "/usr/local/bin/entrypoint"]
