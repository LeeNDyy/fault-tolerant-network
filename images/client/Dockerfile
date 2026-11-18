FROM alpine:3.22
RUN apk add --no-cache iproute2 curl tftp-hpa
COPY entrypoint lease pxe-check /usr/local/bin/
RUN chmod +x /usr/local/bin/lease /usr/local/bin/pxe-check
ENTRYPOINT ["sh", "/usr/local/bin/entrypoint"]
