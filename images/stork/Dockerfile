FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && curl -fsSLo /tmp/stork-repo https://dl.cloudsmith.io/public/isc/stork/setup.deb.sh && bash /tmp/stork-repo \
    && apt-get update && apt-get install -y --no-install-recommends isc-stork-server \
    && rm -rf /var/lib/apt/lists/* /tmp/stork-repo
ENTRYPOINT ["stork-server"]
