"""
SeaTunnel 配置服务 API
基于 FastAPI 封装的 SeaTunnel 交互式配置工具
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid
import json
import os
from datetime import datetime
from pathlib import Path

app = FastAPI(
    title="SeaTunnel 配置服务",
    description="SeaTunnel 数据同步配置的生成、管理和执行服务",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SEATUNNEL_DIR = Path("d:/software/apache-seatunnel-2.3.5")
JOBS_DIR = SEATUNNEL_DIR / "jobs"
JOBS_DIR.mkdir(exist_ok=True)

class SourceType(str, Enum):
    MYSQL = "mysql"
    API = "api"
    TEST = "test"

class JobMode(str, Enum):
    STREAMING = "STREAMING"
    BATCH = "BATCH"

class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"

class FieldMappingItem(BaseModel):
    source: str
    target: str
    type: str = "STRING"

class MySQLConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 3306
    user: str
    password: str
    database: str
    table: str
    is_cdc: bool = False
    server_id: Optional[str] = None
    startup_mode: Optional[str] = "initial"

class APIConfig(BaseModel):
    url: str
    method: HttpMethod = HttpMethod.GET
    content_field: Optional[str] = ""
    returns_array: bool = True

class SinkConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 3306
    user: str
    password: str
    database: str
    table: str
    create_table_if_not_exists: bool = True

class ConfigGenerateRequest(BaseModel):
    source_type: SourceType
    source_config: Dict[str, Any]
    sink_config: SinkConfig
    field_mapping: Optional[List[FieldMappingItem]] = []
    job_mode: JobMode = JobMode.BATCH
    job_name: str = "DataSync"
    parallelism: int = 1

class ConfigSaveRequest(BaseModel):
    name: str
    source_type: SourceType
    source_config: Dict[str, Any]
    sink_config: SinkConfig
    field_mapping: Optional[List[FieldMappingItem]] = []
    job_mode: JobMode = JobMode.BATCH

class ConfigResponse(BaseModel):
    config_id: str
    config_content: str
    created_at: str

class JobSubmitRequest(BaseModel):
    config_id: Optional[str] = None
    config_content: Optional[str] = None

class JobStatus(BaseModel):
    job_id: str
    status: str
    config_id: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None

jobs_db: Dict[str, JobStatus] = {}
configs_db: Dict[str, Dict] = {}

def generate_mysql_config(request: ConfigGenerateRequest) -> str:
    source = request.source_config
    sink = request.sink_config
    field_mapping = request.field_mapping or []

    primary_keys = '"id"'
    if field_mapping:
        for col in field_mapping:
            if col.source == 'id':
                primary_keys = f'"{col.target}"'
                break
        if primary_keys == '"id"' and field_mapping:
            primary_keys = f'"{field_mapping[0].target}"'

    mapping_config = ""
    if field_mapping and request.source_type == SourceType.MYSQL:
        field_lines = []
        for col in field_mapping:
            field_lines.append(f'      "{col.target}" = "{col.source}"')
        mapping_config = f"\n\ntransform {{\n  FieldMapper {{\n    table_fields {{\n" + ",\n".join(field_lines) + "\n    }\n  }}\n}}"

    save_mode = "overwrite" if sink.create_table_if_not_exists else "append"

    if request.job_mode == JobMode.STREAMING and source.get("is_cdc"):
        config = f"""env {{
  job.mode = "STREAMING"
  job.name = "{request.job_name}"
  parallelism = {request.parallelism}
  checkpoint.interval = 10000
}}

source {{
  MySQL-CDC {{
    base-url = "jdbc:mysql://{source['host']}:{source['port']}/{source['database']}?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai"
    username = "{source['user']}"
    password = "{source['password']}"
    table-names = ["{source['database']}.{source['table']}"]
    startup.mode = "{source.get('startup_mode', 'initial')}"
    server-id = "{source.get('server_id', '100-200')}"
  }}
}}{mapping_config}

sink {{
  Jdbc {{
    url = "jdbc:mysql://{sink.host}:{sink.port}/{sink.database}?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai&rewriteBatchedStatements=true"
    driver = "com.mysql.cj.jdbc.Driver"
    user = "{sink.user}"
    password = "{sink.password}"
    database = "{sink.database}"
    table = "{sink.table}"
    batch_size = 100
    generate_sink_sql = true
    save_mode = "{save_mode}"
    primary_keys = [{primary_keys}]
  }}
}}"""
    else:
        config = f"""env {{
  job.mode = "{request.job_mode.value}"
  job.name = "{request.job_name}"
  parallelism = {request.parallelism}
}}

source {{
  Jdbc {{
    url = "jdbc:mysql://{source['host']}:{source['port']}/{source['database']}?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai&rewriteBatchedStatements=true"
    driver = "com.mysql.cj.jdbc.Driver"
    user = "{source['user']}"
    password = "{source['password']}"
    database = "{source['database']}"
    table = "{source['table']}"
    query = "SELECT * FROM {source['table']}"
  }}
}}{mapping_config}

sink {{
  Jdbc {{
    url = "jdbc:mysql://{sink.host}:{sink.port}/{sink.database}?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai&rewriteBatchedStatements=true"
    driver = "com.mysql.cj.jdbc.Driver"
    user = "{sink.user}"
    password = "{sink.password}"
    database = "{sink.database}"
    table = "{sink.table}"
    batch_size = 100
    generate_sink_sql = true
    save_mode = "{save_mode}"
    primary_keys = [{primary_keys}]
  }}
}}"""
    return config

def generate_api_config(request: ConfigGenerateRequest) -> str:
    source = request.source_config
    sink = request.sink_config
    field_mapping = request.field_mapping or []

    primary_keys = '"id"'
    if field_mapping:
        for col in field_mapping:
            if col.source == 'id':
                primary_keys = f'"{col.target}"'
                break
        if primary_keys == '"id"' and field_mapping:
            primary_keys = f'"{field_mapping[0].target}"'

    json_field_lines = []
    schema_field_lines = []

    for col in field_mapping:
        source_field = col.source
        target_field = col.target
        field_type = col.type

        if source.get('content_field'):
            if source.get('returns_array'):
                json_path = f"$.{source['content_field']}[*].{source_field}"
            else:
                json_path = f"$.{source['content_field']}.{source_field}"
        else:
            if source.get('returns_array'):
                json_path = f"$[*].{source_field}"
            else:
                json_path = f"$.{source_field}"

        json_field_lines.append(f'      "{target_field}" = "{json_path}"')

        seatunnel_type = "STRING"
        if field_type == "INT":
            seatunnel_type = "INT"
        elif field_type == "BOOLEAN":
            seatunnel_type = "BOOLEAN"

        schema_field_lines.append(f'        {target_field} = "{seatunnel_type}"')

    json_field_section = "    json_field = {\n" + "\n".join(json_field_lines) + "\n    }"
    schema_section = "    schema = {\n      fields {\n" + "\n".join(schema_field_lines) + "\n      }\n    }"

    save_mode = "overwrite" if sink.create_table_if_not_exists else "append"

    config = f"""env {{
  job.mode = "{request.job_mode.value}"
  job.name = "{request.job_name}"
  parallelism = {request.parallelism}
}}

source {{
  Http {{
    url = "{source['url']}"
    method = "{source['method'].value}"
{json_field_section}
{schema_section}
    headers = {{
      "Content-Type" = "application/json"
      "User-Agent" = "SeaTunnel-HTTP-Source"
    }}
    batch_size = 100
    socket_timeout_ms = 30000
    connect_timeout_ms = 30000
  }}
}}

sink {{
  Jdbc {{
    url = "jdbc:mysql://{sink.host}:{sink.port}/{sink.database}?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai&rewriteBatchedStatements=true"
    driver = "com.mysql.cj.jdbc.Driver"
    user = "{sink.user}"
    password = "{sink.password}"
    database = "{sink.database}"
    table = "{sink.table}"
    batch_size = 100
    generate_sink_sql = true
    save_mode = "{save_mode}"
    primary_keys = [{primary_keys}]
  }}
}}"""
    return config

def generate_test_config(request: ConfigGenerateRequest) -> str:
    sink = request.sink_config

    save_mode = "overwrite" if sink.create_table_if_not_exists else "append"

    config = f"""env {{
  job.mode = "{request.job_mode.value}"
  job.name = "{request.job_name}"
  parallelism = {request.parallelism}
}}

source {{
  FakeSource {{
    result = {{
      name = "test"
      age = 18
    }}
    count = 10
  }}
}}

sink {{
  Jdbc {{
    url = "jdbc:mysql://{sink.host}:{sink.port}/{sink.database}?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai&rewriteBatchedStatements=true"
    driver = "com.mysql.cj.jdbc.Driver"
    user = "{sink.user}"
    password = "{sink.password}"
    database = "{sink.database}"
    table = "{sink.table}"
    batch_size = 100
    generate_sink_sql = true
    save_mode = "{save_mode}"
    primary_keys = ["id"]
  }}
}}"""
    return config

def generate_config(request: ConfigGenerateRequest) -> str:
    if request.source_type == SourceType.MYSQL:
        return generate_mysql_config(request)
    elif request.source_type == SourceType.API:
        return generate_api_config(request)
    elif request.source_type == SourceType.TEST:
        return generate_test_config(request)
    else:
        raise ValueError(f"不支持的数据源类型: {request.source_type}")

@app.get("/")
def root():
    return {
        "service": "SeaTunnel 配置服务",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.post("/config/generate", response_model=ConfigResponse)
def api_generate_config(request: ConfigGenerateRequest):
    try:
        config_content = generate_config(request)
        config_id = str(uuid.uuid4())[:8]

        return ConfigResponse(
            config_id=config_id,
            config_content=config_content,
            created_at=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/config/save")
def api_save_config(request: ConfigSaveRequest):
    config_id = str(uuid.uuid4())[:8]
    configs_db[config_id] = {
        "id": config_id,
        "name": request.name,
        "source_type": request.source_type,
        "source_config": request.source_config,
        "sink_config": request.sink_config,
        "field_mapping": [m.model_dump() for m in request.field_mapping] if request.field_mapping else [],
        "job_mode": request.job_mode,
        "created_at": datetime.now().isoformat()
    }
    return {"config_id": config_id, "message": "配置已保存"}

@app.get("/config/{config_id}")
def api_get_config(config_id: str):
    if config_id not in configs_db:
        raise HTTPException(status_code=404, detail="配置不存在")
    return configs_db[config_id]

@app.get("/configs")
def api_list_configs():
    return [
        {"id": k, "name": v["name"], "source_type": v["source_type"], "created_at": v["created_at"]}
        for k, v in configs_db.items()
    ]

@app.delete("/config/{config_id}")
def api_delete_config(config_id: str):
    if config_id not in configs_db:
        raise HTTPException(status_code=404, detail="配置不存在")
    del configs_db[config_id]
    return {"message": "配置已删除"}

def execute_seatunnel_job(job_id: str, config_content: str, config_id: Optional[str]):
    import subprocess

    job_file = JOBS_DIR / f"job_{job_id}.conf"
    job_file.write_text(config_content, encoding='utf-8')

    jobs_db[job_id] = JobStatus(
        job_id=job_id,
        status="RUNNING",
        config_id=config_id,
        start_time=datetime.now().isoformat()
    )

    try:
        result = subprocess.run(
            ["bin\\seatunnel.cmd", "--config", str(job_file), "-m", "local"],
            cwd=str(SEATUNNEL_DIR),
            capture_output=True,
            text=True,
            timeout=300
        )

        jobs_db[job_id].status = "COMPLETED" if result.returncode == 0 else "FAILED"
        jobs_db[job_id].end_time = datetime.now().isoformat()
        jobs_db[job_id].output = result.stdout[-5000:] if len(result.stdout) > 5000 else result.stdout
        if result.returncode != 0:
            jobs_db[job_id].error = result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr
    except subprocess.TimeoutExpired:
        jobs_db[job_id].status = "TIMEOUT"
        jobs_db[job_id].end_time = datetime.now().isoformat()
        jobs_db[job_id].error = "任务执行超时（5分钟）"
    except Exception as e:
        jobs_db[job_id].status = "ERROR"
        jobs_db[job_id].end_time = datetime.now().isoformat()
        jobs_db[job_id].error = str(e)

@app.post("/job/run")
def api_run_job(request: JobSubmitRequest, background_tasks: BackgroundTasks):
    if not request.config_id and not request.config_content:
        raise HTTPException(status_code=400, detail="必须提供 config_id 或 config_content")

    job_id = str(uuid.uuid4())[:8]

    if request.config_id:
        if request.config_id not in configs_db:
            raise HTTPException(status_code=404, detail="配置不存在")
        config_data = configs_db[request.config_id]

        config_request = ConfigGenerateRequest(
            source_type=SourceType(config_data["source_type"]),
            source_config=config_data["source_config"],
            sink_config=SinkConfig(**config_data["sink_config"]),
            field_mapping=[FieldMappingItem(**m) for m in config_data["field_mapping"]],
            job_mode=JobMode(config_data["job_mode"])
        )
        config_content = generate_config(config_request)
    else:
        config_content = request.config_content

    background_tasks.add_task(execute_seatunnel_job, job_id, config_content, request.config_id)

    return {"job_id": job_id, "message": "任务已提交"}

@app.get("/job/{job_id}/status", response_model=JobStatus)
def api_get_job_status(job_id: str):
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="任务不存在")
    return jobs_db[job_id]

@app.get("/jobs")
def api_list_jobs():
    return list(jobs_db.values())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
