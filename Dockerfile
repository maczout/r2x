# r2x image: Wine on a virtual display, ready to run Response-2000.
#
#   docker build -t ghcr.io/maczout/r2x:VERSION .
#
# Response-2000 is not in the image: each user links their own copy (r2x setup), and every run
# mounts its program folder read-only at /opt/response. So the image holds nothing of Response's
# and can be published.

ARG BASE=ubuntu:24.04

# --- helper.exe: the Win32 program that drives Response from inside the Wine prefix -----------
FROM ${BASE} AS helper
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends gcc-mingw-w64-i686 \
 && rm -rf /var/lib/apt/lists/*
COPY src/r2x/worker/helper.c /build/helper.c
RUN i686-w64-mingw32-gcc -O2 -o /build/helper.exe /build/helper.c -luser32 -lgdi32

# --- runtime ----------------------------------------------------------------------------------
FROM ${BASE}

LABEL org.opencontainers.image.source=https://github.com/maczout/r2x \
      org.opencontainers.image.description="r2x: Response-2000 under Wine, from the command line. Response-2000 itself is not included." \
      org.opencontainers.image.licenses=MIT

# The verified Wine. Exports are only known to match Windows for it; the verified builds of
# Response's r2k.exe are in src/r2x/response.py.
ARG WINE_VERSION=9.0~repack-4build3

ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 TZ=UTC
RUN dpkg --add-architecture i386 \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
      wine=${WINE_VERSION} wine64=${WINE_VERSION} wine32:i386=${WINE_VERSION} \
      libwine=${WINE_VERSION} libwine:i386=${WINE_VERSION} \
      fonts-wine=${WINE_VERSION} fonts-liberation \
      xvfb xauth python3 python3-venv ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Where each run mounts the user's own Response-2000 (read-only).
RUN mkdir /opt/response

COPY --from=helper /build/helper.exe /opt/r2x/helper.exe

# r2x itself.
COPY pyproject.toml README.md LICENSE /opt/r2x/src/
COPY src /opt/r2x/src/src
RUN python3 -m venv /opt/r2x/venv \
 && /opt/r2x/venv/bin/pip install --no-cache-dir "/opt/r2x/src[server]" \
 && rm -rf /opt/r2x/src

# The official ubuntu image ships a user 'ubuntu' with UID 1000; r2x takes that UID instead.
RUN (userdel --remove ubuntu 2>/dev/null || true) && useradd --create-home --uid 1000 r2x
USER r2x
ENV PATH=/opt/r2x/venv/bin:$PATH \
    R2X_RESPONSE_DIR=/opt/response \
    R2X_HELPER=/opt/r2x/helper.exe \
    R2X_WINEPREFIX=/home/r2x/prefix \
    R2X_DATA=/home/r2x/data \
    WINEARCH=win32 WINEDEBUG=-all

# Create the 32-bit Wine prefix now so jobs don't wait for it (src/r2x/worker/prefix.py: windows
# unmanaged, and a Symbol font Response's Greek letters can use). Mono and Gecko are not needed.
# The fonts above only change how the report's pictures look: fonts-wine has Wine's own fonts
# (Symbol among them), fonts-liberation has fonts with Arial's metrics.
RUN WINEDLLOVERRIDES="mscoree,mshtml=" xvfb-run -a python -m r2x.worker.prefix

WORKDIR /home/r2x
CMD ["python", "-m", "r2x.worker", "--help"]
