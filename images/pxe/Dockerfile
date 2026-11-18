FROM debian:bookworm-slim
ARG ALPINE_RELEASE=3.22.8
RUN apt-get update && apt-get install -y --no-install-recommends bash ca-certificates curl iproute2 nginx-light tftpd-hpa \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /var/www/html/alpine
RUN set -eu; mkdir -p /srv/tftp; \
    for file in vmlinuz-virt initramfs-virt modloop-virt; do \
      curl -fsSLO "https://dl-cdn.alpinelinux.org/alpine/v3.22/releases/x86_64/netboot-${ALPINE_RELEASE}/${file}"; \
    done; \
    curl -fsSLo /srv/tftp/undionly.kpxe https://boot.ipxe.org/undionly.kpxe; \
    curl -fsSLo /srv/tftp/ipxe.efi https://boot.ipxe.org/ipxe.efi
COPY boot.ipxe answers ./
COPY install.start /tmp/install.start
RUN set -eu; mkdir -p /tmp/overlay/etc/local.d /tmp/overlay/etc/runlevels/default; \
    install -m 0755 /tmp/install.start /tmp/overlay/etc/local.d/install.start; \
    ln -s /etc/init.d/local /tmp/overlay/etc/runlevels/default/local; \
    tar -C /tmp/overlay -czf install.apkovl.tar.gz etc; \
    rm -r /tmp/overlay /tmp/install.start
COPY nginx.conf /etc/nginx/nginx.conf
COPY entrypoint /usr/local/bin/
ENTRYPOINT ["bash", "/usr/local/bin/entrypoint"]
