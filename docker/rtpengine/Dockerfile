# Dockerfile para RTPEngine - WebRTC to VoIP Media Bridge
FROM debian:bullseye-slim

ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias
RUN apt-get update && apt-get install -y \
    gnupg2 \
    wget \
    lsb-release \
    && wget -qO- https://deb.sipwise.com/spce/mr10.5/pool/main/s/sipwise-keyring/sipwise-keyring_3.0_all.deb > /tmp/keyring.deb \
    && dpkg -i /tmp/keyring.deb \
    && echo "deb https://deb.sipwise.com/spce/mr10.5/ bullseye main" > /etc/apt/sources.list.d/sipwise.list \
    && apt-get update \
    && apt-get install -y \
        ngcp-rtpengine-daemon \
        ngcp-rtpengine-kernel-dkms \
        iptables \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/keyring.deb

# Crear directorios
RUN mkdir -p /var/run/rtpengine

# Copiar configuración
COPY rtpengine.conf /etc/rtpengine/rtpengine.conf

EXPOSE 22222/udp 23000-23100/udp

CMD ["rtpengine", "--config-file=/etc/rtpengine/rtpengine.conf", "--foreground"]
