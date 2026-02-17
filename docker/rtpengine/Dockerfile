# Dockerfile para RTPEngine - WebRTC to VoIP Media Bridge
FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias y RTPEngine desde paquetes Debian/Sipwise
RUN apt-get update && apt-get install -y --no-install-recommends \
    gnupg2 \
    wget \
    ca-certificates \
    lsb-release \
    iptables \
    && wget -qO /tmp/keyring.deb https://deb.sipwise.com/spce/mr12.0/pool/main/s/sipwise-keyring/sipwise-keyring_3.0_all.deb \
    && dpkg -i /tmp/keyring.deb || true \
    && echo "deb http://deb.sipwise.com/spce/mr12.0/ bookworm main" > /etc/apt/sources.list.d/sipwise.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends ngcp-rtpengine-daemon \
    || ( \
        echo "Sipwise repo failed, building rtpengine from source..." \
        && apt-get install -y --no-install-recommends \
            build-essential dpkg-dev debhelper \
            libcurl4-openssl-dev libglib2.0-dev libavcodec-dev \
            libavformat-dev libavutil-dev libswresample-dev \
            libpcap-dev libssl-dev libevent-dev libhiredis-dev \
            libjson-glib-dev libpcre3-dev libiptc-dev libmosquitto-dev \
            libwebsockets-dev libspandsp-dev libopus-dev \
            libxmlrpc-core-c3-dev markdown gperf libavfilter-dev \
            libmariadb-dev libmariadb-dev-compat \
            libnftnl-dev libmnl-dev \
            default-libmysqlclient-dev \
            pkg-config git \
        && cd /tmp && git clone --depth 1 --branch mr12.0 https://github.com/sipwise/rtpengine.git \
        && cd /tmp/rtpengine/daemon && make rtpengine && cp rtpengine /usr/local/bin/ \
        && cd / && rm -rf /tmp/rtpengine \
    ) \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/keyring.deb

# Crear directorios
RUN mkdir -p /var/run/rtpengine

# Copiar configuración
COPY rtpengine.conf /etc/rtpengine/rtpengine.conf

# Copiar entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 22222/udp 23000-23100/udp

# Usar entrypoint
ENTRYPOINT ["/entrypoint.sh"]
