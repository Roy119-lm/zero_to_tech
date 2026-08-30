# Spark + Iceberg + MinIO 数据平台

基于 Apache Spark、Apache Iceberg 和 MinIO 构建的数据平台，提供完整的 ETL 和查询能力。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                           用户访问                                │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌─────────┐    ┌───────────┐    ┌─────────────┐
        │   UI    │    │   API     │    │  Spark UI   │
        │ (Nginx) │    │ (FastAPI) │    │  (Web UI)   │
        └────┬────┘    └─────┬─────┘    └──────┬──────┘
             │               │                 │
             └───────────────┼─────────────────┘
                             ▼
              ┌──────────────────────────────┐
              │     Spark Cluster             │
              │  ┌─────────┐  ┌──────────┐   │
              │  │  Master │  │  Worker  │   │
              │  └─────────┘  └──────────┘   │
              └──────────────┬───────────────┘
                             │
              ┌──────────────┼───────────────┐
              ▼              ▼               ▼
        ┌─────────┐   ┌───────────┐   ┌────────────┐
        │ MinIO   │   │ PostgreSQL│   │   Scripts  │
        │ (S3)    │   │ (Catalog) │   │ (PySpark)  │
        └─────────┘   └───────────┘   └────────────┘
```

## 组件介绍

| 组件 | 说明 |
|------|------|
| **UI** | 前端界面，SolidJS + Vite 开发，Nginx 部署 |
| **API** | 数据查询 API，FastAPI + PyIceberg/DuckDB 实现 |
| **Iceberg 存储** | Spark 作为计算引擎，MinIO 作为对象存储，PostgreSQL 作为元数据目录 |

## 环境要求

- Debian/Ubuntu 系统
- Docker 20.10+
- Docker Compose v2+
- Make
- 至少 4GB 可用内存

### 安装依赖

```bash
# 安装 Docker
sudo apt update
sudo apt install -y docker.io docker-compose-v2

# 安装 Make
sudo apt install -y make

# 安装 uv (Python 包管理器)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装 npm (Node.js 包管理器)
sudo apt install -y npm

# 安装 Nginx
sudo apt install -y nginx
```

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd spark-iceberg-minio
```

### 2. 配置环境变量

```bash
cp .env.template .env
```

默认配置可直接使用，主要配置项：

```bash
# MinIO S3 配置
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_ENDPOINT=http://localhost:9000
S3_BUCKET=iceberg-warehouse

# PostgreSQL 配置
DB_HOST=postgres
DB_PORT=5432
DB_USER=iceberg_user
DB_PASSWORD=iceberg_password
```

### 3. 启动集群

```bash
make up
```

首次启动会：
- 构建包含 Iceberg 的 Spark Docker 镜像
- 启动 PostgreSQL 并等待就绪
- 启动 MinIO 并创建默认 bucket
- 启动 Spark Master 和 Worker
- 部署前端 UI
- 启动后端 API

### 4. 访问服务

| 服务 | 地址 | 说明 |
|------|------|------|
| Web UI | http://localhost | 主界面 |
| Spark Master | http://localhost:8080 | 集群状态 |
| Spark Worker | http://localhost:8081 | Worker 状态 |
| MinIO Console | http://localhost:9001 | 对象存储管理 |
| API | http://localhost:8000 | 数据查询接口 |

MinIO 登录凭据：`minioadmin` / `minioadmin`

## 常用命令

```bash
make help       # 查看所有可用命令
make up         # 启动集群
make down       # 停止集群
make restart    # 重启集群
make logs       # 查看日志
make shell      # 进入 Master 容器
make sql        # 启动 Spark SQL Shell
make pyspark    # 启动 PySpark Shell
make clean      # 清理所有资源
```

## 项目结构

```
.
├── api/                    # FastAPI 后端
│   ├── main.py            # API 入口
│   └── pyproject.toml     # Python 依赖
├── ui/                     # SolidJS 前端
│   ├── src/               # 源代码
│   ├── dist/              # 构建产物
│   └── nginx.conf.template # Nginx 配置
├── conf/                  # 配置文件
│   ├── spark-defaults.conf
│   └── log4j2.properties
├── scripts/               # PySpark 脚本
├── docker-compose.yml     # 容器编排
├── Dockerfile             # Spark 镜像
└── Makefile              # 构建命令
```

## License

Apache License 2.0
