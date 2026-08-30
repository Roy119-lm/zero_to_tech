# 数据中台数据查询API

## 数据写入

使用Spark创建任务的方式写入，这样可以保证写入时的强一致性。

## 数据读取

由于iceberg的协议支持DuckDB直接查询，所以纯粹用于查询的API可以由DuckDB接入PyIceberg实现，并可以多任务完全并行执行。

相比于使用Spark、Trino等计算引擎用于查询，这种PyIceberg查询的方式减轻了计算任务冷启动的延迟，极大降低了API请求的响应延迟。

因此，本项目实现的API可以在Nginx代理中实现超高并发度的请求。

## 运行

请按照下面的要求逐步进行项目配置/运行。

- 本项目依赖于uv作为python的包管理器。请[确保uv被正确安装](https://docs.astral.sh/uv/getting-started/installation/#__tabbed_1_1)。
- 执行同步包的命令。

```bash
uv sync
```

- 执行main.py，该服务器会创建对端口

```bash
uv run fastapi run main.py
```
