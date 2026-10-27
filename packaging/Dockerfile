FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -o APT::Update::Error-Mode=any && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-dev binutils ca-certificates \
    libegl1 libgl1 libglib2.0-0t64 libfontconfig1 libdbus-1-3 libxkbcommon-x11-0 \
    libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
    libxcb-render-util0 libxcb-xinerama0 libxcb-shape0 libxcb-randr0 \
    libxcb-xfixes0 libxcb-sync1 libxcb-xkb1 libxcb-util1 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
RUN --mount=type=secret,id=environment_ca \
    if [ -f /run/secrets/environment_ca ]; then \
      cp /run/secrets/environment_ca /usr/local/share/ca-certificates/build-environment.crt; \
      update-ca-certificates; \
    fi
ENV UV_NATIVE_TLS=true PIP_CERT=/etc/ssl/certs/ca-certificates.crt
RUN python3 -m venv /tools && /tools/bin/pip install --no-cache-dir uv==0.12.23
ENV PATH="/tools/bin:${PATH}"
RUN apt-get update -o APT::Update::Error-Mode=any && apt-get install -y --no-install-recommends libgssapi-krb5-2 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . .
RUN uv sync --frozen --extra dev --extra build \
    && QT_QPA_PLATFORM=offscreen uv run --frozen pytest -q \
    && uv run --frozen python packaging/build_deb.py
RUN apt-get update -o APT::Update::Error-Mode=any && apt-get install -y ./dist/screendepresso_*_amd64.deb \
    && /usr/bin/screendepresso --version \
    && XDG_DATA_HOME=/tmp/screendepresso-smoke /usr/bin/screendepresso --smoke-test \
    && rm -rf /var/lib/apt/lists/* /tmp/screendepresso-smoke
CMD ["/usr/bin/screendepresso", "--version"]
