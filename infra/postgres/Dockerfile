# ============================================================
# 融合镜像：pgvector + TimescaleDB（双引擎数据库）
# 基于 pgvector/pgvector:pg15，保留原有数据卷路径不变
# 数据目录依旧是 /var/lib/postgresql/data，无需改动任何配置
# ============================================================
FROM pgvector/pgvector:pg15

USER root

# 安装 TimescaleDB 官方 apt 源并安装扩展包
# 针对 Debian Bookworm (pg15) 采用更稳健的手动源配置
RUN apt-get update && apt-get install -y --no-install-recommends \
    gnupg \
    lsb-release \
    curl \
    ca-certificates && \
    curl -fsSL https://packagecloud.io/timescale/timescaledb/gpgkey | gpg --dearmor -o /usr/share/keyrings/timescaledb.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/timescaledb.gpg] https://packagecloud.io/timescale/timescaledb/debian/ $(lsb_release -c -s) main" > /etc/apt/sources.list.d/timescaledb.list && \
    apt-get update && \
    apt-get install -y timescaledb-2-postgresql-15 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 在默认配置模板中预加载 TimescaleDB 动态库
# 这样无论新旧数据卷，都会自动加载 TimescaleDB
RUN echo "shared_preload_libraries = 'timescaledb'" >> /usr/share/postgresql/postgresql.conf.sample

# 拷贝初始化脚本，数据库首次启动时自动建立两个扩展
COPY init_extensions.sql /docker-entrypoint-initdb.d/

USER postgres
