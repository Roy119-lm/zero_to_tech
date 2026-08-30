import uuid
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pyiceberg.catalog import load_catalog
from pyiceberg.expressions import EqualTo, And, GreaterThanOrEqual, In, LessThan, LessThanOrEqual, Or
from dotenv import load_dotenv
from pyiceberg.table import ALWAYS_TRUE
from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional, cast
import asyncio
import logging
import pandas as pd
import shutil
import subprocess
import os
import duckdb

logger = logging.getLogger("uvicorn.error")

load_dotenv()
# 1. 初始化 PyIceberg 的 JDBC Catalog 配置
catalog = load_catalog(
    "iceberg_catalog",
    **{
        "type": "sql",
        "uri": "postgresql://iceberg_user:iceberg_password@localhost:5432/iceberg_catalog", # 数据库连接地址
        "warehouse": "s3://processed-data/warehouse",                  # 仓库根路径
        
        "s3.endpoint": f"{os.environ['S3_ENDPOINT']}",
        "s3.access-key-id": f"{os.environ['S3_ACCESS_KEY']}",
        "s3.secret-access-key": f"{os.environ['S3_ACCESS_KEY']}",
        "s3.region": "us-east-1",
        
        "s3.path-style-access": "false",
        "s3.proxy-host": "", # 确保不被系统代理干扰
        "s3.connect-timeout": "60",
    }
)
# 建立DuckDB数据库连接
duckdb_con = duckdb.connect()

# 设置 39GiB 磁盘保护开关（这个在本地部署时不需要，云环境的磁盘容量太小）
duckdb_con.execute(f"""
    SET temp_directory = './duckdb_temp';
    SET max_temp_directory_size = '39GB';
    SET memory_limit = '4GB';
""")

# 创建导入文件夹
UPLOAD_DIR = "../data/upload"
SPARK_UPLOAD_DIR = "/opt/spark/data/upload"
# SPARK_UPLOAD_DIR 在本地映射为 UPLOAD_DIR
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境请改为前端的具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

spark_queue_executor = ThreadPoolExecutor(max_workers=1)
spark_tasks_status = {}

@app.get("/api/v1/metrics/task/{task_id}")
async def get_task_status(task_id: str):
    return spark_tasks_status.get(task_id, {"status": "not_found"})

@app.post("/api/v1/metrics/data")
async def set_data(
    file: UploadFile = File(...),
    coarse_data_mode: Literal["equal", "divide"] = Query("divide", description="年度粗数据分割为季度数据模式：恒等变换或均匀分配"),
    insert_mode: Literal["append", "overwrite"] = Query("append", description="写入模式：追加或覆写")
):
    """
    upload xlsx or csv
    """
    filename = file.filename
    if (filename is None) or (not filename.endswith((".xlsx", ".xls", ".csv"))):
        raise HTTPException(status_code=400, detail="only support .xlsx, .xls or .csv files")
    
    # 为了防止上传多个相同名字的文件，通过UUID命名文件
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(filename)[1]
    upload_file_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")
    spark_upload_file_path = os.path.join(SPARK_UPLOAD_DIR, f"{file_id}{ext}")

    try:
        with open(upload_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        def run_spark_insert(
            task_id: str,
            file_path: str,
            coarse_data_mode: Literal["equal", "divide"],
            insert_mode: Literal["append", "overwrite"]
        ):
            spark_tasks_status[task_id] = {"status": "running"}
            try:
                cmd = [
                    # 降低Spark应用的IO优先级
                    "ionice", "-c", "3", "nice", "-n", "10",
                    "../run.sh", "scripts/insert.py",
                    "--path", file_path,
                    "--coarse_data_mode", coarse_data_mode,
                    "--insert_mode", insert_mode
                ]
                process = subprocess.run(cmd, capture_output=True, text=True)
                if process.returncode == 0:
                    spark_tasks_status[task_id] = {"status": "completed"}
                    logger.info(f"Spark Success for {filename}({task_id}).")
                else:
                    logger.error(f"Spark Error for {filename}({task_id}).\n {process.stderr or process.stdout}")
            except Exception as e:
                spark_tasks_status[task_id] = {"status": "failed", "error": str(e)}

        loop = asyncio.get_event_loop()
        loop.run_in_executor(
            spark_queue_executor,
            run_spark_insert,
            file_id,
            spark_upload_file_path,
            coarse_data_mode,
            insert_mode,
        )
        return {"task_id": file_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    finally:
        await file.close()

def indicators_dictionary(l1_name: str, l2_name: str, l3_name: str, l4_name: str) -> pd.DataFrame:
    # 加载目标表
    table = catalog.load_table("indicators.dictionary")

    # 使用 PyIceberg 进行高效扫描 (元数据裁剪)
    # 这一步只读取必要的 Manifest，不会拉取实际数据
    filters = []
    if l1_name: filters.append(EqualTo("l1_name", l1_name))
    if l2_name: filters.append(EqualTo("l2_name", l2_name))
    if l3_name: filters.append(EqualTo("l3_name", l3_name))
    if l4_name: filters.append(EqualTo("l4_name", l4_name))
    final_filter = None
    if filters:
        final_filter = filters[0]
        for f in filters[1:]:
            final_filter = And(final_filter, f)

    scan = table.scan(
        row_filter=final_filter if final_filter is not None else ALWAYS_TRUE,
        selected_fields=("l1_name", "l2_name", "l3_name", "l4_name", "data_type")
    )

    # 转化为 Arrow Table
    arrow_table = scan.to_arrow()

    # 直接对变量 arrow_table 进行 SQL 查询
    query_sql = """
        SELECT l1_name, l2_name, l3_name, l4_name, data_type
        FROM arrow_table 
    """

    return duckdb_con.execute(query_sql).df()

@app.get("/api/v1/metrics/data")
async def get_data(
    l1_name: str = Query(
        "", description="一级指标名称（可选）", examples=["公共服务智慧化"]
    ),
    l2_name: str = Query(
        "", description="二级指标名称（可选）", examples=["老有所养智慧化"]
    ),
    l3_name: str = Query(
        "", description="三级指标名称（可选）", examples=["老年人健康监测"]
    ),
    l4_name: str = Query(
        "", description="四级指标名称（可选）", examples=["老年人健康档案电子化率"]
    ),
    start_ts: Optional[datetime] = Query(
        None, description="RFC3339 UTC timestamp", examples=["2025-02-09T00:00:00Z"]
    ),
    end_ts: Optional[datetime] = Query(
        None, description="RFC3339 UTC timestamp", examples=["2025-02-09T00:00:01Z"]
    ),
    region: Optional[int]=None,
):
    def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
        if dt is None:
            return None
        if dt.tzinfo is None:
            raise HTTPException(
                status_code=400,
                detail="timestamp must include timezone (RFC3339, e.g. 2025-02-09T00:00:00Z)"
            )
        return dt.astimezone(timezone.utc)

    try:
        start_ts = ensure_utc(start_ts)
        end_ts = ensure_utc(end_ts)
        if start_ts and end_ts and start_ts > end_ts:
            raise HTTPException(400, "start_ts must be earlier than or equal to end_ts")

        result_df = indicators_dictionary(l1_name, l2_name, l3_name, l4_name)

        indicator_names: List[str] = []
        datatype_dict: Dict[str, str] = {}

        for _, row in result_df.iterrows():
            indicator_names.append(cast(str, row["l4_name"]))
            datatype_dict[cast(str, row["l4_name"])] = cast(str, row["data_type"])

        data_table = catalog.load_table("indicators.data")
        and_filters = []
        if start_ts is not None:
            and_filters.append(GreaterThanOrEqual("ts", start_ts))
        if end_ts is not None:
            and_filters.append(LessThanOrEqual("ts", end_ts)) 
        if region is not None:
            cnt = 0
            _region = region
            while _region % 10 == 0:
                cnt += 1
                _region //= 10
            and_filters.append(GreaterThanOrEqual("region_code", _region * 10 ** cnt))
            and_filters.append(LessThan("region_code", (_region + 1) * 10 ** cnt))

        final_filter = ALWAYS_TRUE
        if indicator_names:
            final_filter = In("indicator_name", indicator_names)

        if and_filters:
            for f in and_filters:
                final_filter = And(final_filter, f)

        scan = data_table.scan(
            row_filter=final_filter if final_filter is not None else ALWAYS_TRUE,
        )

        arrow_table = scan.to_arrow()

        query_sql = """
            SELECT *
            FROM arrow_table 
        """
        result_df = duckdb_con.execute(query_sql).df()

        return result_df.to_dict(orient='records')

    except Exception as e:
        logger.error(f"Get Data Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/metrics/dictionary")
async def get_dictionary(
    l1_name: str = Query(
        "", description="一级指标名称（可选）", examples=["公共服务智慧化"]
    ),
    l2_name: str = Query(
        "", description="二级指标名称（可选）", examples=["老有所养智慧化"]
    ),
    l3_name: str = Query(
        "", description="三级指标名称（可选）", examples=["老年人健康监测"]
    ),
    l4_name: str = Query(
        "", description="四级指标名称（可选）", examples=["老年人健康档案电子化率"]
    ),
):
    try:
        result_df = indicators_dictionary(l1_name, l2_name, l3_name, l4_name)
        return result_df.to_dict(orient='records')

    except Exception as e:
        logger.warning(f"Get Dictionary Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
