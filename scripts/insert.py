#将datafrmae导入数据库
#equal函数将年度数据直接赋给4个季度数据
#divide函数将年度数据除以4后再赋给季度
from decimal import Decimal, getcontext
from enum import Enum
from pyspark.sql import SparkSession
import pandas as pd
from china_division import search_division
spark = SparkSession.builder \
    .appName("IcebergExample") \
    .getOrCreate()

spark.conf.set("spark.sql.iceberg.handle-timestamp-without-timezone", "true")

class InsertMode(Enum):
    APPEND = 1
    OVERWRITE = 2

class CoarseDataMode(Enum):
    EQUAL = 1   # 将年度数据直接置为四个季度的数据
    DIVIDE = 2  # 将年度数据平均分为四个季度的数据

# 全局设置定点数精度，保证DECIMAL(20, 8)能够正确计算
getcontext().prec = 28

def insert(
    file_path: str,
    coarse_data_mode: CoarseDataMode=CoarseDataMode.DIVIDE,
    insert_mode: InsertMode=InsertMode.APPEND
):
    df = pd.read_excel(file_path, header=0, engine="openpyxl")

    processed_records = []

    indicator_name = df.columns[4]

    for _, row in df.iterrows():
        # 提取基础数据
        prov = str(row.iloc[3]) if not pd.isnull(row.iloc[3]) else ''
        city = str(row.iloc[2]) if not pd.isnull(row.iloc[2]) else ''
        coun = str(row.iloc[1]) if not pd.isnull(row.iloc[1]) else ''
        if pd.isnull(row.iloc[4]):
            continue    # 空值，继续提取其他行数据
        val = Decimal(row.iloc[4])
        extra_info = str(row.iloc[5]) if len(row) > 5 and not pd.isnull(row.iloc[5]) else ''

        # 行政区划查询
        reg_code = 0
        search_str = prov + city + coun
        code_res = search_division(search_str)
        if code_res != '未找到对应的行政区划信息':
            code = int(code_res.split("|")[0].split(":")[0])
            if prov:
                reg_code += code // 10000 * 10000
            if city:
                reg_code += (code % 10000) // 100 * 100
            if coun:
                reg_code += code % 100
        elif not prov:
            print("Error:", code_res)
            return
        
        time_str = str(row.iloc[0])

        time_list = time_str.split('/')
        if len(time_list) >= 1 and len(time_list[0]) == 4:
            # 构建时间戳（用于时间只有年份的数据表）
            year = int(time_list[0])
            ts = pd.to_datetime(time_str).to_pydatetime()

            if len(time_list) == 1:
                season_val = val / Decimal(4) if coarse_data_mode == CoarseDataMode.DIVIDE else val
                for s in range(1, 5):
                    processed_records.append({
                        "timestamp": ts, "region_code": reg_code,
                        "province": prov, "city": city, "county": coun,
                        "year": year, "season": s, "indicator": indicator_name,
                        "data": season_val, "extra_info": extra_info
                    })
            else:
                season = int(time_list[1]) // 3 + 1
                processed_records.append({
                    "timestamp": ts, "region_code": reg_code,
                    "province": prov, "city": city, "county": coun,
                    "year": year, "season": season, "indicator": indicator_name,
                    "data": val, "extra_info": extra_info
                })

    spark_df = spark.createDataFrame(processed_records)
    spark_df.createOrReplaceTempView("process_data")

    if insert_mode == InsertMode.OVERWRITE:
        ddl = '''
        MERGE INTO indicators.data t
        USING process_data s
        ON t.region_code = s.region_code 
           AND t.year = s.year 
           AND t.season = s.season 
           AND t.indicator_name = s.indicator  -- 注意：源表列名是 indicator
           AND t.extra_info = s.extra_info     -- 如果 extra_info 为空字符串也需要匹配
        WHEN MATCHED THEN
          UPDATE SET 
            t.indicator_value = CAST(s.data AS DECIMAL(20, 8)),
            t.ts = s.timestamp,
            t.province = s.province,
            t.city = s.city,
            t.county = s.county
        WHEN NOT MATCHED THEN
          INSERT (ts, region_code, province, city, county, year, season, indicator_name, indicator_value, extra_info)
          VALUES (s.timestamp, s.region_code, s.province, s.city, s.county, s.year, s.season, s.indicator, CAST(s.data AS DECIMAL(20, 8)), s.extra_info)
        '''
    else:
        ddl = '''
        INSERT INTO indicators.data (
            ts, region_code, province, city, county,
            year, season, indicator_name, indicator_value, extra_info
        )
        SELECT
            timestamp,
            region_code,
            province,
            city,
            county,
            year,
            season,
            indicator,
            CAST(data AS DECIMAL(20, 8)),
            extra_info
        FROM process_data;
        '''
    spark.sql(ddl).show()

    ddl = 'select * from indicators.data'
    spark.sql(ddl).show()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=str, required=True, help="输入文件的路径")
    parser.add_argument("--coarse_data_mode", type=str, choices=["equal", "divide"], default="divide", help="年度粗数据分割为季度数据模式：恒等变换或均匀分配")
    parser.add_argument("--insert_mode", type=str, choices=["append", "overwrite"], default="append", help="写入模式：追加或覆写")

    args = parser.parse_args()
    if args.coarse_data_mode == "equal":
        coarse_data_mode = CoarseDataMode.EQUAL
    else:
        coarse_data_mode = CoarseDataMode.DIVIDE

    if args.insert_mode == "overwrite":
        insert_mode = InsertMode.OVERWRITE
    else:
        insert_mode = InsertMode.APPEND

    insert(args.path, coarse_data_mode, insert_mode)

