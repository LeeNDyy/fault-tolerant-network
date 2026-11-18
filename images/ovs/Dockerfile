FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends openvswitch-switch iproute2 isc-dhcp-client iputils-ping && rm -rf /var/lib/apt/lists/*
COPY entrypoint /usr/local/bin/
ENTRYPOINT ["sh", "/usr/local/bin/entrypoint"]
