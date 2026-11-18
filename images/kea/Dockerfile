FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl gnupg bash iproute2 postgresql-client python3 \
    && curl -fsSLo /tmp/kea-repo https://dl.cloudsmith.io/public/isc/kea-2-6/setup.deb.sh && bash /tmp/kea-repo \
    && curl -fsSLo /tmp/stork-repo https://dl.cloudsmith.io/public/isc/stork/setup.deb.sh && bash /tmp/stork-repo \
    && apt-get update && apt-get install -y --no-install-recommends isc-kea-dhcp4 isc-kea-ctrl-agent isc-kea-hooks isc-kea-admin isc-stork-agent \
    && rm -rf /var/lib/apt/lists/* /tmp/kea-repo /tmp/stork-repo
COPY entrypoint bootstrap render.py /usr/local/bin/
ENTRYPOINT ["bash", "/usr/local/bin/entrypoint"]
