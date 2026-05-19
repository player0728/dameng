#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DataX + SeaTunnel 数据同步工具
支持 MySQL/API (SeaTunnel) + 达梦数据库 (DataX)
失败了
"""

import os
import sys
import subprocess
import getpass
import json
from datetime import datetime
from pathlib import Path
import socket
import re

try:
    import mysql.connector
except ImportError:
    mysql_connector_available = False
else:
    mysql_connector_available = True

try:
    import pyodbc
except ImportError:
    pyodbc_available = False
else:
    pyodbc_available = True

class Colors:
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BLUE}{'=' * 60}{Colors.NC}")
    print(f"{Colors.BLUE}  {text}{Colors.NC}")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.NC}\n")

def print_step(step_num, text):
    print(f"{Colors.YELLOW}【步骤 {step_num}/5】{text}{Colors.NC}\n")

def print_success(text):
    print(f"\n{Colors.GREEN}✓ {text}{Colors.NC}\n")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.NC}")

def get_input(prompt, default=None, required=False, hide=False):
    while True:
        if hide:
            value = getpass.getpass(prompt)
        else:
            value = input(prompt)

        if not value and default:
            return default

        if required and not value:
            print_error("此项不能为空")
            continue

        return value

def test_mysql_connection(host, port, user, password, database):
    """测试 MySQL 连接"""
    if not mysql_connector_available:
        print(f"{Colors.YELLOW}警告：未安装 mysql-connector-python，跳过连接测试{Colors.NC}")
        return True

    print(f"\n{Colors.BLUE}正在测试 MySQL 连接...{Colors.NC}")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, int(port)))
        sock.close()
        print(f"{Colors.GREEN}✓ 端口 {port} 可访问{Colors.NC}")

        conn = mysql.connector.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            database=database,
            connect_timeout=5
        )
        conn.close()
        print(f"{Colors.GREEN}✓ 数据库连接成功{Colors.NC}")
        return True
    except socket.error as e:
        print_error(f"连接失败：端口 {port} 不可达 - {e}")
        return False
    except mysql.connector.Error as e:
        print_error(f"连接失败：{e}")
        return False

def get_mysql_databases(host, port, user, password):
    """获取所有可用的 MySQL 数据库"""
    if not mysql_connector_available:
        print(f"{Colors.YELLOW}警告：未安装 mysql-connector-python，无法获取数据库列表{Colors.NC}")
        return None
    
    try:
        conn = mysql.connector.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            connect_timeout=5
        )
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES")
        databases = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return databases
    except mysql.connector.Error as e:
        print_error(f"获取数据库列表失败：{e}")
        return None

def get_mysql_database_tables(host, port, user, password, database):
    """获取 MySQL 数据库中的所有表"""
    if not mysql_connector_available:
        print(f"{Colors.YELLOW}警告：未安装 mysql-connector-python，无法获取表列表{Colors.NC}")
        return None
    
    try:
        conn = mysql.connector.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            database=database,
            connect_timeout=5
        )
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return tables
    except mysql.connector.Error as e:
        print_error(f"获取表列表失败：{e}")
        return None

def get_mysql_table_columns(host, port, user, password, database, table):
    """获取 MySQL 表的所有列名及类型"""
    if not mysql_connector_available:
        return None
    
    try:
        conn = mysql.connector.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            database=database,
            connect_timeout=5
        )
        cursor = conn.cursor()
        cursor.execute(f"DESCRIBE {table}")
        columns = []
        for row in cursor.fetchall():
            column_name = row[0]
            column_type = row[1]
            if 'int' in str(column_type).lower():
                mapped_type = 'INT'
            elif 'date' in str(column_type).lower() or 'time' in str(column_type).lower():
                mapped_type = 'DATETIME'
            elif 'char' in str(column_type).lower() or 'text' in str(column_type).lower() or 'varchar' in str(column_type).lower():
                mapped_type = 'STRING'
            else:
                mapped_type = 'STRING'
            columns.append({
                'source': column_name,
                'target': column_name,
                'type': mapped_type
            })
        cursor.close()
        conn.close()
        return columns
    except mysql.connector.Error as e:
        print_error(f"获取表结构失败：{e}")
        return None

def config_mysql_database(is_source=True):
    """配置 MySQL 数据库"""
    direction = "源" if is_source else "目标"
    print(f"{Colors.BLUE}--- 配置{direction}MySQL 数据库 ---{Colors.NC}\n")

    while True:
        host = get_input(f"{direction} MySQL 主机地址 [默认：127.0.0.1]: ", default="127.0.0.1")
        port = get_input(f"{direction} MySQL 端口 [默认：3306]: ", default="3306")
        user = get_input(f"{direction} MySQL 用户名 [默认：root]: ", default="root")
        password = get_input(f"{direction} MySQL 密码： ", required=True, hide=True)
        
        databases = get_mysql_databases(host, port, user, password)
        if databases and len(databases) > 0:
            print(f"\n{Colors.GREEN}可用的数据库：{Colors.NC}")
            for i, db in enumerate(databases, 1):
                print(f"  {i}) {db}")
            
            while True:
                db_choice = get_input(f"\n请选择数据库 [1-{len(databases)}] 或输入数据库名： ", required=True)
                
                if db_choice.isdigit():
                    idx = int(db_choice)
                    if 1 <= idx <= len(databases):
                        database = databases[idx - 1]
                        print(f"{Colors.GREEN}✓ 已选择数据库：{database}{Colors.NC}")
                        break
                    else:
                        print_error(f"请输入 1-{len(databases)} 之间的数字")
                else:
                    database = db_choice
                    print(f"{Colors.GREEN}✓ 已选择数据库：{database}{Colors.NC}")
                    break
        else:
            database = get_input(f"{direction} 数据库名： ", required=True)

        if not test_mysql_connection(host, port, user, password, database):
            retry = get_input("是否重新输入？[y/N]: ", default="y").lower()
            if retry != "y":
                print_error("操作已取消")
                sys.exit(1)
            continue
        
        tables = get_mysql_database_tables(host, port, user, password, database)
        
        if tables and len(tables) > 0:
            print(f"\n{Colors.GREEN}数据库 '{database}' 中的表：{Colors.NC}")
            for i, tbl in enumerate(tables, 1):
                print(f"  {i}) {tbl}")
            
            while True:
                table_choice = get_input(f"\n请选择表 [1-{len(tables)}] 或输入表名： ", required=True)
                
                if table_choice.isdigit():
                    idx = int(table_choice)
                    if 1 <= idx <= len(tables):
                        table = tables[idx - 1]
                        print(f"{Colors.GREEN}✓ 已选择表：{table}{Colors.NC}")
                        break
                    else:
                        print_error(f"请输入 1-{len(tables)} 之间的数字")
                else:
                    table = table_choice
                    if table in tables:
                        print(f"{Colors.GREEN}✓ 已选择表：{table}{Colors.NC}")
                        break
                    else:
                        print_error(f"表 '{table}' 不存在于数据库中")
                        if not is_source:
                            print(f"{Colors.YELLOW}表 '{table}' 将在执行时自动创建{Colors.NC}")
                            break
                        else:
                            retry = get_input("是否重新输入表名？[y/N]: ", default="y").lower()
                            if retry != "y":
                                print_error("操作已取消")
                                sys.exit(1)
        else:
            table = get_input(f"{direction} 表名： ", required=True)
        
        break

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
        "table": table
    }

def test_dameng_connection(host, port, user, password, database):
    """测试达梦数据库连接（使用 pyodbc）"""
    if not pyodbc_available:
        print(f"{Colors.YELLOW}警告：未安装 pyodbc，跳过连接测试{Colors.NC}")
        return True

    print(f"\n{Colors.BLUE}正在测试达梦连接...{Colors.NC}")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, int(port)))
        sock.close()
        print(f"{Colors.GREEN}✓ 端口 {port} 可访问{Colors.NC}")

        conn_str = f"DRIVER={{DM8 ODBC DRIVER}};SERVER={host};PORT={port};UID={user};PWD={password};DATABASE={database}"
        conn = pyodbc.connect(conn_str)
        conn.close()
        print(f"{Colors.GREEN}✓ 达梦数据库连接成功{Colors.NC}")
        return True
    except socket.error as e:
        print_error(f"连接失败：端口 {port} 不可达 - {e}")
        return False
    except Exception as e:
        print_error(f"连接失败：{e}")
        return False

def get_dameng_databases(host, port, user, password):
    """获取达梦数据库列表（使用 pyodbc）"""
    if not pyodbc_available:
        print(f"{Colors.YELLOW}警告：未安装 pyodbc，无法获取数据库列表{Colors.NC}")
        return None
    
    try:
        conn_str = f"DRIVER={{DM8 ODBC DRIVER}};SERVER={host};PORT={port};UID={user};PWD={password}"
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT OWNER FROM ALL_TABLES ORDER BY OWNER")
        databases = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return databases
    except Exception as e:
        print_error(f"获取达梦数据库列表失败：{e}")
        return None

def get_dameng_database_tables(host, port, user, password, database):
    """获取达梦数据库中的所有表（使用 pyodbc）"""
    if not pyodbc_available:
        print(f"{Colors.YELLOW}警告：未安装 pyodbc，无法获取表列表{Colors.NC}")
        return None
    
    try:
        conn_str = f"DRIVER={{DM8 ODBC DRIVER}};SERVER={host};PORT={port};UID={user};PWD={password};DATABASE={database}"
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute(f"SELECT TABLE_NAME FROM ALL_TABLES WHERE OWNER = '{database.upper()}' ORDER BY TABLE_NAME")
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return tables
    except Exception as e:
        print_error(f"获取达梦表列表失败：{e}")
        return None

def get_dameng_table_columns(host, port, user, password, database, table):
    """获取达梦表的所有列名及类型（使用 pyodbc）"""
    if not pyodbc_available:
        return None
    
    try:
        conn_str = f"DRIVER={{DM8 ODBC DRIVER}};SERVER={host};PORT={port};UID={user};PWD={password};DATABASE={database}"
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute(f"SELECT COLUMN_NAME, DATA_TYPE FROM ALL_TAB_COLUMNS WHERE OWNER = '{database.upper()}' AND TABLE_NAME = '{table.upper()}' ORDER BY COLUMN_ID")
        columns = []
        for row in cursor.fetchall():
            column_name = row[0]
            column_type = row[1]
            if 'INT' in str(column_type).upper():
                mapped_type = 'INT'
            elif 'DATE' in str(column_type).upper() or 'TIME' in str(column_type).upper():
                mapped_type = 'DATETIME'
            elif 'CHAR' in str(column_type).upper() or 'TEXT' in str(column_type).upper() or 'VARCHAR' in str(column_type).upper():
                mapped_type = 'STRING'
            else:
                mapped_type = 'STRING'
            columns.append({
                'source': column_name,
                'target': column_name,
                'type': mapped_type
            })
        cursor.close()
        conn.close()
        return columns
    except Exception as e:
        print_error(f"获取达梦表结构失败：{e}")
        return None

def config_dameng_database(is_source=True):
    """配置达梦数据库（支持自动获取数据库和表列表）"""
    direction = "源" if is_source else "目标"
    print(f"{Colors.BLUE}--- 配置{direction}达梦数据库 ---{Colors.NC}\n")

    while True:
        host = get_input(f"{direction} 达梦主机地址 [默认：127.0.0.1]: ", default="127.0.0.1")
        port = get_input(f"{direction} 达梦端口 [默认：5236]: ", default="5236")
        user = get_input(f"{direction} 达梦用户名 [默认：SYSDBA]: ", default="SYSDBA")
        password = get_input(f"{direction} 达梦密码： ", required=True, hide=True)
        
        databases = get_dameng_databases(host, port, user, password)
        if databases and len(databases) > 0:
            print(f"\n{Colors.GREEN}可用的数据库：{Colors.NC}")
            for i, db in enumerate(databases, 1):
                print(f"  {i}) {db}")
            
            while True:
                db_choice = get_input(f"\n请选择数据库 [1-{len(databases)}] 或输入数据库名： ", required=True)
                
                if db_choice.isdigit():
                    idx = int(db_choice)
                    if 1 <= idx <= len(databases):
                        database = databases[idx - 1]
                        print(f"{Colors.GREEN}✓ 已选择数据库：{database}{Colors.NC}")
                        break
                    else:
                        print_error(f"请输入 1-{len(databases)} 之间的数字")
                else:
                    database = db_choice
                    print(f"{Colors.GREEN}✓ 已选择数据库：{database}{Colors.NC}")
                    break
        else:
            database = get_input(f"{direction} 数据库名： ", required=True)

        if not test_dameng_connection(host, port, user, password, database):
            retry = get_input("是否重新输入？[y/N]: ", default="n").lower()
            if retry == "y":
                continue
            else:
                print_error("操作已取消")
                sys.exit(1)
        
        tables = get_dameng_database_tables(host, port, user, password, database)
        
        if tables and len(tables) > 0:
            print(f"\n{Colors.GREEN}数据库 '{database}' 中的表：{Colors.NC}")
            for i, tbl in enumerate(tables, 1):
                print(f"  {i}) {tbl}")
            
            while True:
                table_choice = get_input(f"\n请选择表 [1-{len(tables)}] 或输入表名： ", required=True)
                
                if table_choice.isdigit():
                    idx = int(table_choice)
                    if 1 <= idx <= len(tables):
                        table = tables[idx - 1]
                        print(f"{Colors.GREEN}✓ 已选择表：{table}{Colors.NC}")
                        break
                    else:
                        print_error(f"请输入 1-{len(tables)} 之间的数字")
                else:
                    table = table_choice
                    if table.upper() in [t.upper() for t in tables]:
                        print(f"{Colors.GREEN}✓ 已选择表：{table}{Colors.NC}")
                        break
                    else:
                        print_error(f"表 '{table}' 不存在于数据库中")
                        if not is_source:
                            print(f"{Colors.YELLOW}表 '{table}' 将在执行时自动创建{Colors.NC}")
                            break
                        else:
                            retry = get_input("是否重新输入表名？[y/N]: ", default="y").lower()
                            if retry == "y":
                                continue
                            else:
                                print_error("操作已取消")
                                sys.exit(1)
        else:
            table = get_input(f"{direction} 表名： ", required=True)
        
        break

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
        "table": table
    }

def configure_field_mapping(source_columns=None, show_step=True):
    """配置字段映射"""
    if show_step:
        print_step(3, "字段映射配置")
    
    field_mapping = []
    
    if source_columns:
        field_mapping = [col.copy() for col in source_columns]
    else:
        print(f"{Colors.YELLOW}提示：未获取到源表字段，请手动添加字段映射{Colors.NC}")
        while True:
            source_field = get_input("源字段名（回车结束）： ")
            if not source_field:
                break
            target_field = get_input(f"目标字段名 [默认：{source_field}]: ", default=source_field)
            field_type = get_input(f"字段类型 [STRING/INT/DATETIME/BOOLEAN，默认：STRING]: ", default="STRING")
            field_mapping.append({
                'source': source_field,
                'target': target_field,
                'type': field_type
            })
    
    if not field_mapping:
        print(f"{Colors.YELLOW}未配置字段映射，将使用 SELECT * 查询{Colors.NC}")
        return []
    
    while True:
        print("\n" + "="*60)
        print(f"{'序号':<6} {'源字段名':<15} {'目标字段名':<15} {'字段类型':<12}")
        print("="*60)
        for i, col in enumerate(field_mapping, 1):
            print(f"{i:<6} {col['source']:<15} {col['target']:<15} {col['type']:<12}")
        print("="*60)
        
        print("\n操作选项：")
        print("  1) 修改目标字段名")
        print("  2) 修改字段类型")
        print("  3) 删除字段")
        print("  4) 手动添加字段")
        print("  5) 完成映射")
        
        choice = get_input("请选择操作 [1-5]: ", default="5")
        
        if choice == "1":
            idx = int(get_input("请输入要修改的序号： ", required=True)) - 1
            if 0 <= idx < len(field_mapping):
                new_target = get_input(f"新的目标字段名 [当前：{field_mapping[idx]['target']}]: ", required=True)
                field_mapping[idx]['target'] = new_target
            else:
                print_error("序号无效")
        elif choice == "2":
            idx = int(get_input("请输入要修改的序号： ", required=True)) - 1
            if 0 <= idx < len(field_mapping):
                new_type = get_input(f"新的字段类型 [STRING/INT/DATETIME/BOOLEAN，当前：{field_mapping[idx]['type']}]: ", required=True)
                field_mapping[idx]['type'] = new_type
            else:
                print_error("序号无效")
        elif choice == "3":
            idx = int(get_input("请输入要删除的序号： ", required=True)) - 1
            if 0 <= idx < len(field_mapping):
                del field_mapping[idx]
            else:
                print_error("序号无效")
        elif choice == "4":
            source_field = get_input("源字段名： ", required=True)
            target_field = get_input(f"目标字段名 [默认：{source_field}]: ", default=source_field)
            field_type = get_input(f"字段类型 [STRING/INT/DATETIME/BOOLEAN，默认：STRING]: ", default="STRING")
            field_mapping.append({
                'source': source_field,
                'target': target_field,
                'type': field_type
            })
        elif choice == "5":
            break
    
    print_success("字段映射配置完成")
    return field_mapping

def generate_seatunnel_config(source_config, sink_config, field_mapping, job_name, job_mode, parallelism, source_type="mysql"):
    """生成 SeaTunnel 配置文件"""
    mapping_config = ""
    save_mode = "create"
    primary_keys = "\"id\""
    
    if field_mapping:
        has_mapping = any(col['source'] != col['target'] for col in field_mapping)
        if has_mapping:
            mapping_config = "\n\ntransform {\n  FieldMapper {\n    field_mapper = {"
            id_mapped = False
            for col in field_mapping:
                mapping_config += f"\n      {col['source']} = {col['target']},"
                if col['source'] == 'id':
                    primary_keys = f"\"{col['target']}\""
                    id_mapped = True
            mapping_config += "\n    }\n  }\n}\n"
            save_mode = "upsert"
            if not id_mapped and field_mapping:
                primary_keys = f"\"{field_mapping[0]['target']}\""
    
    if source_type == "mysql":
        config_content = f"""# ============================================
# SeaTunnel MySQL->MySQL 同步配置（自动生成）
# 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# ============================================

env {{
  job.mode = "{job_mode}"
  job.name = "{job_name}"
  parallelism = {parallelism}
}}

source {{
  Jdbc {{
    driver = "com.mysql.cj.jdbc.Driver"
    url = "jdbc:mysql://{source_config['host']}:{source_config['port']}/{source_config['database']}?useSSL=false&serverTimezone=UTC&allowPublicKeyRetrieval=true"
    user = "{source_config['user']}"
    password = "{source_config['password']}"
    database = "{source_config['database']}"
    table = "{source_config['table']}"
    query = "SELECT * FROM {source_config['table']}"
  }}
}}{mapping_config}

sink {{
  Jdbc {{
    driver = "com.mysql.cj.jdbc.Driver"
    url = "jdbc:mysql://{sink_config['host']}:{sink_config['port']}/{sink_config['database']}?useSSL=false&serverTimezone=UTC&allowPublicKeyRetrieval=true"
    user = "{sink_config['user']}"
    password = "{sink_config['password']}"
    database = "{sink_config['database']}"
    table = "{sink_config['table']}"
    batch_size = 100
    generate_sink_sql = true
    save_mode = "{save_mode}"
    primary_keys = [{primary_keys}]
  }}
}}
"""
    elif source_type == "api":
        json_field = field_mapping[0]['source'] if field_mapping else "results"
        config_content = f"""# ============================================
# SeaTunnel API->MySQL 同步配置（自动生成）
# 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# ============================================

env {{
  job.mode = "BATCH"
  job.name = "{job_name}"
  parallelism = {parallelism}
}}

source {{
  HttpSource {{
    url = "{source_config['url']}"
    method = "{source_config['method']}"
    format = "json"
    json_field = "{json_field}"
  }}
}}{mapping_config}

sink {{
  Jdbc {{
    driver = "com.mysql.cj.jdbc.Driver"
    url = "jdbc:mysql://{sink_config['host']}:{sink_config['port']}/{sink_config['database']}?useSSL=false&serverTimezone=UTC&allowPublicKeyRetrieval=true"
    user = "{sink_config['user']}"
    password = "{sink_config['password']}"
    database = "{sink_config['database']}"
    table = "{sink_config['table']}"
    batch_size = 100
    generate_sink_sql = true
    save_mode = "{save_mode}"
    primary_keys = [{primary_keys}]
  }}
}}
"""
    
    return config_content

def generate_datax_config(source_config, sink_config, field_mapping, channel=3):
    """生成 DataX 达梦同步配置文件（使用 rdbmsreader/rdbmswriter 通用 JDBC 插件）"""
    if field_mapping:
        columns = [col['source'] for col in field_mapping]
        sink_columns = [col['target'] for col in field_mapping]
    else:
        columns = ["*"]
        sink_columns = ["*"]
    
    # 达梦数据库使用 SCHEMA.TABLE 格式（不使用引号，让 JDBC 驱动处理）
    source_table = f'{source_config["database"].upper()}.{source_config["table"].upper()}'
    sink_table = f'{sink_config["database"].upper()}.{sink_config["table"].upper()}'
    
    # 构建 reader 参数（不包含 splitPk，让 DataX 自动处理）
    # 注意：jdbcUrl 必须是数组格式
    reader_param = {
        "username": source_config['user'],
        "password": source_config['password'],
        "column": columns,
        "connection": [
            {
                "jdbcUrl": [f"jdbc:dm://{source_config['host']}:{source_config['port']}/{source_config['database']}"],
                "driverClass": "dm.jdbc.driver.DmDriver",
                "table": [source_table]
            }
        ]
    }
    
    datax_config = {
        "job": {
            "content": [
                {
                    "reader": {
                        "name": "rdbmsreader",
                        "parameter": reader_param
                    },
                    "writer": {
                        "name": "rdbmswriter",
                        "parameter": {
                            "username": sink_config['user'],
                            "password": sink_config['password'],
                            "column": sink_columns,
                            "connection": [
                                {
                                    "jdbcUrl": [f"jdbc:dm://{sink_config['host']}:{sink_config['port']}/{sink_config['database']}"],
                                    "driverClass": "dm.jdbc.driver.DmDriver",
                                    "table": [sink_table]
                                }
                            ],
                            "preSql": [],
                            "postSql": []
                        }
                    }
                }
            ],
            "setting": {
                "speed": {
                    "channel": int(channel)
                }
            }
        }
    }
    
    return json.dumps(datax_config, indent=2, ensure_ascii=False)

def execute_seatunnel(config_content):
    """执行 SeaTunnel 任务"""
    workspace = Path(os.environ.get('TEMP', '/tmp')) / "seatunnel"
    workspace.mkdir(parents=True, exist_ok=True)
    output_config = workspace / "generated_config.conf"
    
    with open(output_config, 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    print(f"\n{Colors.BLUE}生成配置文件：{output_config}{Colors.NC}")
    
    seatunnel_home = os.environ.get('SEATUNNEL_HOME', '.')
    run_command = f"{seatunnel_home}/bin/seatunnel.sh --config {output_config}"
    
    print(f"\n{Colors.BLUE}正在执行 SeaTunnel 任务...{Colors.NC}")
    print(f"{Colors.YELLOW}命令：{run_command}{Colors.NC}")
    
    try:
        result = subprocess.run(run_command, shell=True, capture_output=True, text=True, encoding='utf-8')
        print(f"\n{Colors.BLUE}执行结果：{Colors.NC}")
        if result.stdout:
            print(f"{Colors.GREEN}标准输出：\n{result.stdout}{Colors.NC}")
        if result.stderr:
            print(f"{Colors.RED}错误输出：\n{result.stderr}{Colors.NC}")
        
        if result.returncode == 0:
            print_success("SeaTunnel 任务执行成功")
            return True
        else:
            print_error(f"SeaTunnel 任务执行失败（退出码：{result.returncode}）")
            return False
    except Exception as e:
        print_error(f"执行失败：{e}")
        return False

def execute_datax(config_content):
    """执行 DataX 任务"""
    workspace = Path(os.environ.get('TEMP', '/tmp')) / "datax"
    workspace.mkdir(parents=True, exist_ok=True)
    output_config = workspace / "dm_sync_job.json"
    
    with open(output_config, 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    print(f"\n{Colors.BLUE}生成配置文件：{output_config}{Colors.NC}")
    
    # 获取 DataX 路径
    datax_home = os.environ.get('DATAX_HOME')
    
    # 如果环境变量未设置或路径不存在，提示用户输入
    if not datax_home or not os.path.exists(datax_home):
        print(f"{Colors.YELLOW}警告：DATAX_HOME 环境变量未设置或路径不存在{Colors.NC}")
        default_path = 'D:/software/DataX/datax' if os.path.exists('D:/software/DataX/datax') else '/opt/datax'
        datax_home = get_input(f"请输入 DataX 安装目录 [默认：{default_path}]: ", default=default_path)
        
        if not os.path.exists(datax_home):
            print_error(f"DataX 安装目录不存在：{datax_home}")
            return False
    
    run_command = f"python {datax_home}/bin/datax.py {output_config}"
    
    print(f"\n{Colors.BLUE}正在执行 DataX 任务...{Colors.NC}")
    print(f"{Colors.YELLOW}命令：{run_command}{Colors.NC}")
    
    try:
        result = subprocess.run(run_command, shell=True, capture_output=True, text=True, encoding='utf-8')
        print(f"\n{Colors.BLUE}执行结果：{Colors.NC}")
        if result.stdout:
            print(f"{Colors.GREEN}标准输出：\n{result.stdout}{Colors.NC}")
        if result.stderr:
            print(f"{Colors.RED}错误输出：\n{result.stderr}{Colors.NC}")
        
        if result.returncode == 0:
            print_success("DataX 任务执行成功")
            return True
        else:
            print_error(f"DataX 任务执行失败（退出码：{result.returncode}）")
            return False
    except Exception as e:
        print_error(f"执行失败：{e}")
        return False

def main():
    print_header("DataX + SeaTunnel 数据同步工具")
    
    print("选择数据源类型:")
    print("  1) MySQL 数据库")
    print("  2) 达梦数据库")
    print("  3) HTTP API")
    print("  4) 测试模式")
    
    source_choice = get_input("请选择 [1-4] [默认：1]: ", default="1")
    
    if source_choice == "1":
        print_success("数据源：MySQL 数据库")
        
        print_step(1, "配置作业信息")
        job_name = get_input("作业名称 [默认：MySQL_to_MySQL_Sync]: ", default="MySQL_to_MySQL_Sync")
        
        print("选择作业模式:")
        print("  1) STREAMING (CDC 实时同步)")
        print("  2) BATCH (批量同步)")
        mode_choice = get_input("请选择 [1-2] [默认：1]: ", default="1")
        job_mode = "STREAMING" if mode_choice == "1" else "BATCH"
        parallelism = get_input("并行度 [默认：1]: ", default="1")
        
        print_step(2, "配置源 MySQL 数据库")
        source_config = config_mysql_database(is_source=True)
        
        source_columns = get_mysql_table_columns(
            source_config['host'],
            source_config['port'],
            source_config['user'],
            source_config['password'],
            source_config['database'],
            source_config['table']
        )
        
        field_mapping = configure_field_mapping(source_columns, show_step=True)
        
        print_step(4, "配置目标 MySQL 数据库")
        sink_config = config_mysql_database(is_source=False)
        
        print_step(5, "确认并执行")
        print(f"\n{Colors.BLUE}任务摘要：{Colors.NC}")
        print(f"  作业名称：{job_name}")
        print(f"  同步模式：{job_mode}")
        print(f"  并行度：{parallelism}")
        print(f"  源数据库：MySQL {source_config['host']}:{source_config['port']}/{source_config['database']}.{source_config['table']}")
        print(f"  目标数据库：MySQL {sink_config['host']}:{sink_config['port']}/{sink_config['database']}.{sink_config['table']}")
        
        confirm = get_input("\n确认执行？[Y/n]: ", default="Y").upper()
        if confirm == "Y":
            config_content = generate_seatunnel_config(source_config, sink_config, field_mapping, job_name, job_mode, parallelism, source_type="mysql")
            execute_seatunnel(config_content)
        else:
            print_error("操作已取消")
    
    elif source_choice == "2":
        print_success("数据源：达梦数据库")
        
        print_step(1, "配置作业信息")
        job_name = get_input("作业名称 [默认：Dameng_to_Dameng_Sync]: ", default="Dameng_to_Dameng_Sync")
        parallelism = get_input("并行度/通道数 [默认：3]: ", default="3")
        
        print_step(2, "配置源达梦数据库")
        source_config = config_dameng_database(is_source=True)
        
        source_columns = get_dameng_table_columns(
            source_config['host'],
            source_config['port'],
            source_config['user'],
            source_config['password'],
            source_config['database'],
            source_config['table']
        )
        
        print_step(3, "字段映射配置")
        field_mapping = configure_field_mapping(source_columns, show_step=True)
        
        print_step(4, "配置目标达梦数据库")
        sink_config = config_dameng_database(is_source=False)
        
        print_step(5, "确认并执行")
        print(f"\n{Colors.BLUE}任务摘要：{Colors.NC}")
        print(f"  作业名称：{job_name}")
        print(f"  同步模式：BATCH (DataX)")
        print(f"  通道数：{parallelism}")
        print(f"  源数据库：达梦 {source_config['host']}:{source_config['port']}/{source_config['database']}.{source_config['table']}")
        print(f"  目标数据库：达梦 {sink_config['host']}:{sink_config['port']}/{sink_config['database']}.{sink_config['table']}")
        
        confirm = get_input("\n确认执行？[Y/n]: ", default="Y").upper()
        if confirm == "Y":
            config_content = generate_datax_config(source_config, sink_config, field_mapping, parallelism)
            execute_datax(config_content)
        else:
            print_error("操作已取消")
    
    elif source_choice == "3":
        print_success("数据源：HTTP API")
        
        print_step(1, "配置作业信息")
        job_name = get_input("作业名称 [默认：API_to_MySQL_Sync]: ", default="API_to_MySQL_Sync")
        parallelism = get_input("并行度 [默认：1]: ", default="1")
        
        print_step(2, "配置源 API")
        print("选择 API 类型:")
        print("  1) Random User Generator API (https://randomuser.me/)")
        print("  2) 自定义 API")
        api_choice = get_input("请选择 [1-2] [默认：1]: ", default="1")
        
        if api_choice == "1":
            source_config = {
                "url": "https://randomuser.me/api/",
                "method": "GET",
                "json_field": "results"
            }
            print(f"{Colors.GREEN}✓ 已选择 Random User Generator API{Colors.NC}")
        else:
            url = get_input("API URL: ", required=True)
            method = get_input("HTTP 方法 [默认：GET]: ", default="GET")
            json_field = get_input("JSON 内容字段 [默认：results]: ", default="results")
            source_config = {
                "url": url,
                "method": method,
                "json_field": json_field
            }
        
        print_step(3, "字段映射配置")
        field_mapping = configure_field_mapping(None, show_step=False)
        
        print_step(4, "配置目标 MySQL 数据库")
        sink_config = config_mysql_database(is_source=False)
        
        print_step(5, "确认并执行")
        print(f"\n{Colors.BLUE}任务摘要：{Colors.NC}")
        print(f"  作业名称：{job_name}")
        print(f"  同步模式：BATCH")
        print(f"  并行度：{parallelism}")
        print(f"  源 API：{source_config['url']}")
        print(f"  目标数据库：MySQL {sink_config['host']}:{sink_config['port']}/{sink_config['database']}.{sink_config['table']}")
        
        confirm = get_input("\n确认执行？[Y/n]: ", default="Y").upper()
        if confirm == "Y":
            config_content = generate_seatunnel_config(source_config, sink_config, field_mapping, job_name, "BATCH", parallelism, source_type="api")
            execute_seatunnel(config_content)
        else:
            print_error("操作已取消")
    
    elif source_choice == "4":
        print_success("使用测试模式")
        print(f"{Colors.YELLOW}测试模式仅用于验证配置流程，不执行实际同步{Colors.NC}")

if __name__ == "__main__":
    main()