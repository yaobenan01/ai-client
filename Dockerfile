# 无头（headless）容器化运行 —— 对应 docker-headless 形态
FROM rust:1-slim AS build
WORKDIR /app
COPY core ./core
RUN cargo build --release --manifest-path core/Cargo.toml

FROM debian:bookworm-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build /app/core/target/release/ai-client /usr/local/bin/ai-client
VOLUME /data
EXPOSE 8787
ENTRYPOINT ["ai-client", "serve", "--data-dir", "/data", "--host", "0.0.0.0", "--port", "8787"]
