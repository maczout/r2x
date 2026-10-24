# r2x server image: Response-2000 under Wine on a virtual display.
#
#   docker build -t r2x-server .
#
# Response-2000 is not included: put its program folder in ./Response before building.

ARG BASE=ubuntu:24.04

# --- helper.exe: the Win32 program that drives Response from inside the Wine prefix -----------
FROM ${BASE} AS helper
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends gcc-mingw-w64-i686 \
 && rm -rf /var/lib/apt/lists/*
COPY src/r2x/worker/helper.c /build/helper.c
RUN i686-w64-mingw32-gcc -O2 -o /build/helper.exe /build/helper.c -luser32

# --- runtime ----------------------------------------------------------------------------------
FROM ${BASE}

# Verified versions. Exports are only known to match Windows for these.
ARG WINE_VERSION=9.0~repack-4build3
ARG R2K_SHA256=bbf4bc595ee80167ea73a76d597b2223cbc5e9c47d97d452025cde4bb85e4e74
ARG RESPONSE_DIR=Response

ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 TZ=UTC
RUN dpkg --add-architecture i386 \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
      wine=${WINE_VERSION} wine64=${WINE_VERSION} wine32:i386=${WINE_VERSION} \
      libwine=${WINE_VERSION} libwine:i386=${WINE_VERSION} \
      xvfb xauth python3 python3-venv ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Response-2000, checked against the verified r2k.exe.
COPY ${RESPONSE_DIR}/ /opt/response/
RUN echo "${R2K_SHA256}  /opt/response/r2k.exe" | sha256sum -c - \
 && rm -f /opt/response/Response.ini

COPY --from=helper /build/helper.exe /opt/r2x/helper.exe

# r2x itself.
COPY pyproject.toml README.md LICENSE /opt/r2x/src/
COPY src /opt/r2x/src/src
RUN python3 -m venv /opt/r2x/venv \
 && /opt/r2x/venv/bin/pip install --no-cache-dir /opt/r2x/src \
 && rm -rf /opt/r2x/src

# The official ubuntu image ships a user 'ubuntu' with UID 1000; r2x takes that UID instead.
RUN (userdel --remove ubuntu 2>/dev/null || true) && useradd --create-home --uid 1000 r2x
USER r2x
ENV PATH=/opt/r2x/venv/bin:$PATH \
    R2X_RESPONSE_DIR=/opt/response \
    R2X_HELPER=/opt/r2x/helper.exe \
    R2X_WINEPREFIX=/home/r2x/prefix \
    WINEARCH=win32 WINEDEBUG=-all

# Create the 32-bit Wine prefix now so jobs don't wait for it. Mono and Gecko are not needed.
RUN WINEPREFIX=$R2X_WINEPREFIX WINEDLLOVERRIDES="mscoree,mshtml=" xvfb-run -a wineboot -i \
 && WINEPREFIX=$R2X_WINEPREFIX wineserver -w

WORKDIR /home/r2x
CMD ["python", "-m", "r2x.worker", "--help"]
