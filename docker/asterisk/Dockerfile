FROM debian:bullseye-slim

LABEL maintainer="VoziPOmni Team"
LABEL description="Asterisk 21 LTS para VoziPOmni Contact Center"

# Instalar dependencias
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    git \
    libssl-dev \
    libncurses5-dev \
    libnewt-dev \
    libxml2-dev \
    libsqlite3-dev \
    uuid-dev \
    libjansson-dev \
    libedit-dev \
    libsrtp2-dev \
    libopus-dev \
    libspeex-dev \
    libspeexdsp-dev \
    libvorbis-dev \
    libogg-dev \
    libcodec2-dev \
    libgsm1-dev \
    curl \
    xmlstarlet \
    procps \
    bc \
    vim \
    nano \
    net-tools \
    tcpdump \
    sngrep \
    ngrep \
    tshark \
    && rm -rf /var/lib/apt/lists/*

# Descargar Asterisk desde Git (siempre disponible)
WORKDIR /tmp
RUN git clone --depth 1 --branch 21 https://github.com/asterisk/asterisk.git asterisk-src && \
    cd asterisk-src && \
    ./configure --with-jansson-bundled --with-pjproject-bundled && \
    make menuselect.makeopts && \
    menuselect/menuselect \
        --enable app_confbridge \
        --enable app_queue \
        --enable app_voicemail \
        --enable res_http_websocket \
        --enable res_ari \
        --enable res_pjsip \
        --enable res_pjsip_session \
        --enable chan_pjsip \
        --disable format_mp3 \
        menuselect.makeopts && \
    make -j$(nproc) && \
    make install && \
    make samples && \
    cd / && \
    rm -rf /tmp/asterisk-src

# Crear usuario asterisk y directorios
RUN useradd -m asterisk && \
    mkdir -p /var/log/asterisk && \
    mkdir -p /var/run/asterisk && \
    chown -R asterisk:asterisk /var/lib/asterisk && \
    chown -R asterisk:asterisk /var/spool/asterisk && \
    chown -R asterisk:asterisk /var/log/asterisk && \
    chown -R asterisk:asterisk /var/run/asterisk && \
    chown -R asterisk:asterisk /etc/asterisk

# Copiar configuraciones personalizadas
COPY --chown=asterisk:asterisk configs/*.conf /etc/asterisk/

# Copiar entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Exponer puertos
EXPOSE 5060/udp 5060/tcp 5061/tcp 5161/udp 5162/udp 8088 8089 10000-10100/udp

# Volúmenes
VOLUME ["/etc/asterisk", "/var/lib/asterisk", "/var/spool/asterisk/monitor", "/var/run/asterisk"]

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD su asterisk -c "/usr/sbin/asterisk -rx 'core show version'" || exit 1

# Entrypoint maneja permisos, placeholders, IP inyección y arranca asterisk
ENTRYPOINT ["/entrypoint.sh"]
