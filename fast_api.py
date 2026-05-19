#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SeaTunnel 交互式配置工具（增强版）
更友好的终端交互体验
支持 MySQL->MySQL (CDC/batch)、API->MySQL、达梦数据库直接同步、Git仓库同步
在data_sync_tool_plus.py基础上新增了获取schema
在dameng_test.py基础上新增了实时同步功能
在dameng_new.py基础上新增了自动拉取和手动拉取功能
在git_new.py基础上新增了保存配置记录功能，字段映射不需要重复配置
成功
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
import threading
import time
from typing import Optional, List, Dict, Any
from enum import Enum

try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse
    from pydantic import BaseModel, Field
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    print_warning("FastAPI 未安装，部分功能将不可用。请运行: pip install fastapi uvicorn pydantic")

try:
    import mysql.connector
except ImportError:
    mysql_connector_available = False
else:
    mysql_connector_available = True

# 达梦 ODBC 连接器
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

def print_info(text):
    print(f"{Colors.BLUE}ℹ {text}{Colors.NC}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.NC}")

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

# ==================== MySQL 数据库相关函数 ====================

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
        if "Access denied" in str(e):
            print_error(f"连接失败：用户名或密码错误")
        elif "Unknown database" in str(e):
            print_error(f"连接失败：数据库 '{database}' 不存在")
        else:
            print_error(f"连接失败：{e}")
        return False

def create_database(host, port, user, password, database):
    """创建数据库"""
    if not mysql_connector_available:
        print(f"{Colors.YELLOW}警告：未安装 mysql-connector-python，无法创建数据库{Colors.NC}")
        return False
    
    try:
        conn = mysql.connector.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            connect_timeout=5
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.close()
        conn.close()
        print(f"{Colors.GREEN}✓ 数据库 '{database}' 创建成功{Colors.NC}")
        return True
    except mysql.connector.Error as e:
        print_error(f"创建数据库失败：{e}")
        return False

def verify_table_exists(host, port, user, password, database, table):
    """验证表是否存在"""
    if not mysql_connector_available:
        print(f"{Colors.YELLOW}警告：未安装 mysql-connector-python，跳过表验证{Colors.NC}")
        return True
    
    print(f"{Colors.BLUE}正在验证表 '{table}' 是否存在...{Colors.NC}")
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
        cursor.execute(f"SHOW TABLES LIKE '{table}'")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            print(f"{Colors.GREEN}✓ 表 '{table}' 存在{Colors.NC}")
            return True
        else:
            print_error(f"表 '{table}' 不存在")
            return False
    except mysql.connector.Error as e:
        print_error(f"验证表失败：{e}")
        return False

def get_databases(host, port, user, password):
    """获取所有可用的数据库"""
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
        system_dbs = ['information_schema', 'mysql', 'performance_schema', 'sys']
        databases = [db for db in databases if db not in system_dbs]
        cursor.close()
        conn.close()
        return databases
    except mysql.connector.Error as e:
        print_error(f"获取数据库列表失败：{e}")
        return None

def get_database_tables(host, port, user, password, database):
    """获取数据库中的所有表"""
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

def get_table_columns(host, port, user, password, database, table):
    """获取表的所有列名及类型"""
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
        cursor.execute(f"DESCRIBE `{table}`")
        columns = []
        for row in cursor.fetchall():
            column_name = row[0]
            column_type = row[1]
            if 'int' in str(column_type).lower():
                mapped_type = 'INT'
            elif 'datetime' in str(column_type).lower() or 'date' in str(column_type).lower():
                mapped_type = 'DATETIME'
            elif 'bool' in str(column_type).lower():
                mapped_type = 'BOOLEAN'
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

def configure_field_mapping(source_columns, show_step=True):
    """配置字段映射"""
    if show_step:
        print_step(4, "字段映射配置")
    
    mapped_columns = source_columns.copy() if source_columns else []
    
    while True:
        print(f"\n{Colors.BLUE}当前字段映射：{Colors.NC}")
        print(f"{Colors.GREEN}{'='*60}{Colors.NC}")
        print(f"{Colors.GREEN}{'源字段名'.ljust(20)}{'目标字段名'.ljust(20)}{'字段类型'.ljust(10)}{'操作'}{Colors.NC}")
        print(f"{Colors.GREEN}{'='*60}{Colors.NC}")
        
        for i, col in enumerate(mapped_columns, 1):
            print(f"{str(i).ljust(5)} {col['source'].ljust(15)} → {col['target'].ljust(15)} → {col['type'].ljust(10)} [删除]")
        
        print(f"{Colors.GREEN}{'='*60}{Colors.NC}")
        
        print("\n操作选项：")
        print("  1) 修改目标字段名")
        print("  2) 修改字段类型")
        print("  3) 删除字段")
        print("  4) 手动添加字段")
        print("  5) 完成映射")
        
        choice = get_input("请选择操作 [1-5]: ", required=True)
        
        if choice == "1":
            idx = int(get_input("请输入字段序号： ", required=True)) - 1
            if 0 <= idx < len(mapped_columns):
                new_target = get_input(f"新的目标字段名 [{mapped_columns[idx]['target']}]: ", 
                                    default=mapped_columns[idx]['target'], required=True)
                mapped_columns[idx]['target'] = new_target
                print_success(f"已修改目标字段名为：{new_target}")
            else:
                print_error("无效的字段序号")
                
        elif choice == "2":
            idx = int(get_input("请输入字段序号： ", required=True)) - 1
            if 0 <= idx < len(mapped_columns):
                print("选择字段类型：")
                print("  1) STRING")
                print("  2) INT")
                print("  3) DATETIME")
                print("  4) BOOLEAN")
                type_choice = get_input("请选择 [1-4]: ", required=True)
                type_map = {"1": "STRING", "2": "INT", "3": "DATETIME", "4": "BOOLEAN"}
                if type_choice in type_map:
                    mapped_columns[idx]['type'] = type_map[type_choice]
                    print_success(f"已修改字段类型为：{type_map[type_choice]}")
                else:
                    print_error("无效的类型选择")
            else:
                print_error("无效的字段序号")
                
        elif choice == "3":
            idx = int(get_input("请输入字段序号： ", required=True)) - 1
            if 0 <= idx < len(mapped_columns):
                deleted_field = mapped_columns.pop(idx)
                print_success(f"已删除字段：{deleted_field['source']}")
            else:
                print_error("无效的字段序号")
                
        elif choice == "4":
            source_field = get_input("源字段名： ", required=True)
            target_field = get_input(f"目标字段名 [{source_field}]: ", default=source_field, required=True)
            print("选择字段类型：")
            print("  1) STRING")
            print("  2) INT")
            print("  3) DATETIME")
            print("  4) BOOLEAN")
            type_choice = get_input("请选择 [1-4]: ", required=True)
            type_map = {"1": "STRING", "2": "INT", "3": "DATETIME", "4": "BOOLEAN"}
            if type_choice in type_map:
                new_column = {
                    'source': source_field,
                    'target': target_field,
                    'type': type_map[type_choice]
                }
                mapped_columns.append(new_column)
                print_success(f"已添加字段：{source_field} → {target_field} ({type_map[type_choice]})")
            else:
                print_error("无效的类型选择")
                
        elif choice == "5":
            if not mapped_columns:
                print_error("至少需要保留一个字段")
                continue
            break
        else:
            print_error("无效的选择")
    
    return mapped_columns

def config_mysql_database(is_source=True, is_cdc=False):
    direction = "源" if is_source else "目标"
    print(f"{Colors.BLUE}--- 配置{direction}数据库 ---{Colors.NC}\n")

    while True:
        host = get_input(f"{direction} MySQL 主机地址 [默认：127.0.0.1]: ", default="127.0.0.1")
        port = get_input(f"{direction} MySQL 端口 [默认：3306]: ", default="3306")
        user = get_input(f"{direction} MySQL 用户名： ", required=True)
        password = get_input(f"{direction} MySQL 密码： ", required=True, hide=True)
        
        databases = get_databases(host, port, user, password)
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
            create_db = get_input("数据库不存在，是否创建？[y/N]: ", default="n").lower()
            if create_db == "y":
                if create_database(host, port, user, password, database):
                    break
                else:
                    retry = get_input("是否重新输入？[y/N]: ", default="y").lower()
                    if retry == "y":
                        continue
                    else:
                        print_error("操作已取消")
                        sys.exit(1)
            else:
                retry = get_input("是否重新输入？[y/N]: ", default="y").lower()
                if retry == "y":
                    continue
                else:
                    print_error("操作已取消")
                    sys.exit(1)
        
        tables = get_database_tables(host, port, user, password, database)
        
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
                            create_table = get_input("此表不存在，是否创建？[y/N]: ", default="n").lower()
                            if create_table == "y":
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
                            retry = get_input("是否重新输入表名？[y/N]: ", default="y").lower()
                            if retry == "y":
                                continue
                            else:
                                print_error("操作已取消")
                                sys.exit(1)
        else:
            table = get_input(f"{direction} 表名： ", required=True)
            if not verify_table_exists(host, port, user, password, database, table):
                if not is_source:
                    create_table = get_input("此表不存在，是否创建？[y/N]: ", default="n").lower()
                    if create_table == "y":
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
                    retry = get_input("是否重新输入表名？[y/N]: ", default="y").lower()
                    if retry == "y":
                        continue
                    else:
                        print_error("操作已取消")
                        sys.exit(1)
        
        break

    if is_source and is_cdc:
        server_id = get_input(f"CDC Server ID [默认：100-200]: ", default="100-200")
        startup_mode = get_input(f"启动模式 [initial/earliest/latest 默认：initial]: ", default="initial")
        return {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
            "table": table,
            "server_id": server_id,
            "startup_mode": startup_mode
        }

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
        "table": table
    }

# ==================== 达梦数据库相关函数 ====================

def test_dameng_connection(host, port, user, password, database):
    """测试达梦数据库连接"""
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
    """获取达梦数据库列表"""
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
        print_error(f"获取数据库列表失败：{e}")
        return None

def get_dameng_tables(host, port, user, password, database):
    """获取达梦数据库中的表"""
    try:
        conn_str = f"DRIVER={{DM8 ODBC DRIVER}};SERVER={host};PORT={port};UID={user};PWD={password};DATABASE={database}"
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute(f"SELECT TABLE_NAME FROM ALL_TABLES WHERE OWNER = '{database}' ORDER BY TABLE_NAME")
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return tables
    except Exception as e:
        print_error(f"获取表列表失败：{e}")
        return None

def get_dameng_table_columns(host, port, user, password, database, table):
    """获取达梦表的列信息"""
    try:
        conn_str = f"DRIVER={{DM8 ODBC DRIVER}};SERVER={host};PORT={port};UID={user};PWD={password};DATABASE={database}"
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT COLUMN_NAME, DATA_TYPE 
            FROM ALL_TAB_COLUMNS 
            WHERE OWNER = '{database}' AND TABLE_NAME = '{table}' 
            ORDER BY COLUMN_ID
        """)
        columns = []
        for row in cursor.fetchall():
            column_name = row[0]
            column_type = row[1]
            if 'INT' in str(column_type).upper():
                mapped_type = 'INT'
            elif 'DATE' in str(column_type).upper() or 'TIME' in str(column_type).upper():
                mapped_type = 'DATETIME'
            elif 'BOOL' in str(column_type).upper():
                mapped_type = 'BOOLEAN'
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
        print_error(f"获取表结构失败：{e}")
        return None

def get_dameng_primary_key(host, port, user, password, database, table):
    """获取达梦表的主键字段"""
    try:
        conn_str = f"DRIVER={{DM8 ODBC DRIVER}};SERVER={host};PORT={port};UID={user};PWD={password};DATABASE={database}"
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        cursor.execute(f"""
            SELECT a.COLUMN_NAME
            FROM ALL_CONS_COLUMNS a
            JOIN ALL_CONSTRAINTS b ON a.CONSTRAINT_NAME = b.CONSTRAINT_NAME
            WHERE b.OWNER = '{database}' 
              AND b.TABLE_NAME = '{table}'
              AND b.CONSTRAINT_TYPE = 'P'
            ORDER BY a.POSITION
        """)
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            return result[0]
        return None
    except Exception as e:
        print_error(f"获取主键失败：{e}")
        return None

def create_dameng_table(host, port, user, password, database, table_name, field_mapping):
    """根据字段映射创建达梦表
    
    Args:
        host: 主机地址
        port: 端口
        user: 用户名
        password: 密码
        database: 数据库名
        table_name: 表名
        field_mapping: 字段映射配置
        
    Returns:
        bool: 是否创建成功
    """
    print(f"\n{Colors.YELLOW}目标表不存在，根据字段映射创建表结构...{Colors.NC}")
    try:
        conn_str = f"DRIVER={{DM8 ODBC DRIVER}};SERVER={host};PORT={port};UID={user};PWD={password};DATABASE={database}"
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        create_table_sql = f'CREATE TABLE "{database}"."{table_name}" ('
        for i, col in enumerate(field_mapping):
            if i > 0:
                create_table_sql += ", "
            
            dameng_type = "VARCHAR(255)"
            if col['type'] == "INT":
                dameng_type = "INT"
            elif col['type'] == "DATETIME":
                dameng_type = "DATETIME"
            elif col['type'] == "BOOLEAN":
                dameng_type = "BOOLEAN"
            
            create_table_sql += f'"{col["target"]}" {dameng_type} NULL'
        create_table_sql += ");"
        
        print(f"{Colors.BLUE}执行建表SQL: {create_table_sql}{Colors.NC}")
        cursor.execute(create_table_sql)
        conn.commit()
        print(f"{Colors.GREEN}✓ 目标表创建成功{Colors.NC}")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print_error(f"创建目标表失败：{e}")
        return False

def config_dameng_database(is_source=True, allow_create=False, field_mapping=None):
    """配置达梦数据库连接
    
    Args:
        is_source: 是否为源数据库
        allow_create: 是否允许创建表（目标数据库时可能需要）
        field_mapping: 字段映射配置（创建表时使用）
    """
    direction = "源" if is_source else "目标"
    print(f"{Colors.BLUE}--- 配置{direction}达梦数据库 ---{Colors.NC}\n")

    while True:
        host = get_input(f"{direction}达梦主机地址 [默认：127.0.0.1]: ", default="127.0.0.1")
        port = get_input(f"{direction}达梦端口 [默认：5236]: ", default="5236")
        user = get_input(f"{direction}达梦用户名： ", required=True)
        password = get_input(f"{direction}达梦密码： ", required=True, hide=True)
        
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
            database = get_input(f"{direction}数据库名： ", required=True)

        if not test_dameng_connection(host, port, user, password, database):
            retry = get_input("连接失败，是否重新输入？[y/N]: ", default="y").lower()
            if retry == "y":
                continue
            else:
                print_error("操作已取消")
                sys.exit(1)
        
        tables = get_dameng_tables(host, port, user, password, database)
        
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
                        if allow_create and field_mapping:
                            create = get_input("是否根据字段映射创建此表？[Y/n]: ", default="y").lower()
                            if create == "y":
                                if create_dameng_table(host, port, user, password, database, table, field_mapping):
                                    break
                                else:
                                    retry = get_input("创建失败，是否重新输入表名？[y/N]: ", default="y").lower()
                                    if retry == "y":
                                        continue
                                    else:
                                        print_error("操作已取消")
                                        sys.exit(1)
                            else:
                                retry = get_input("是否重新输入表名？[y/N]: ", default="y").lower()
                                if retry == "y":
                                    continue
                                else:
                                    print_error("操作已取消")
                                    sys.exit(1)
                        else:
                            retry = get_input("是否重新输入表名？[y/N]: ", default="y").lower()
                            if retry == "y":
                                continue
                            else:
                                print_error("操作已取消")
                                sys.exit(1)
        else:
            table = get_input(f"{direction}表名： ", required=True)
        
        break

    columns = get_dameng_table_columns(host, port, user, password, database, table)
    
    if columns and len(columns) > 0:
        print(f"\n{Colors.GREEN}表 '{table}' 的字段结构：{Colors.NC}")
        print(f"{Colors.BLUE}{'='*60}{Colors.NC}")
        print(f"{Colors.BLUE}{'序号'.ljust(6)}{'字段名'.ljust(25)}{'类型'}{Colors.NC}")
        print(f"{Colors.BLUE}{'='*60}{Colors.NC}")
        for i, col in enumerate(columns, 1):
            print(f"{str(i).ljust(6)}{col['source'].ljust(25)}{col['type']}")
        print(f"{Colors.BLUE}{'='*60}{Colors.NC}")
        print(f"{Colors.GREEN}共 {len(columns)} 个字段{Colors.NC}")
    else:
        print(f"{Colors.YELLOW}警告：无法获取表 '{table}' 的字段信息{Colors.NC}")
        columns = []

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
        "table": table,
        "columns": columns
    }

def sync_dameng_data(source_config, sink_config, field_mapping=None):
    """执行达梦数据库数据同步"""
    print(f"\n{Colors.BLUE}开始执行达梦数据库同步...{Colors.NC}")
    
    try:
        source_conn_str = f"DRIVER={{DM8 ODBC DRIVER}};SERVER={source_config['host']};PORT={source_config['port']};UID={source_config['user']};PWD={source_config['password']};DATABASE={source_config['database']}"
        sink_conn_str = f"DRIVER={{DM8 ODBC DRIVER}};SERVER={sink_config['host']};PORT={sink_config['port']};UID={sink_config['user']};PWD={sink_config['password']};DATABASE={sink_config['database']}"
        
        source_conn = pyodbc.connect(source_conn_str)
        sink_conn = pyodbc.connect(sink_conn_str)
        
        source_cursor = source_conn.cursor()
        sink_cursor = sink_conn.cursor()
        
        source_cursor.execute(f"SELECT * FROM {source_config['database']}.{source_config['table']}")
        source_columns = [col[0] for col in source_cursor.description]
        
        sink_cursor.execute(f"SELECT * FROM {sink_config['database']}.{sink_config['table']} WHERE 1=0")
        sink_columns = [col[0] for col in sink_cursor.description]
        
        if field_mapping:
            mapped_source_cols = [m['source'] for m in field_mapping]
            mapped_sink_cols = [m['target'] for m in field_mapping]
            common_source = [col for col in mapped_source_cols if col in source_columns]
            common_sink = [mapped_sink_cols[mapped_source_cols.index(col)] for col in common_source]
            field_map = dict(zip(common_source, common_sink))
        else:
            common_source = [col for col in source_columns if col in sink_columns]
            common_sink = common_source
            field_map = dict(zip(common_source, common_sink))
        
        if not common_source:
            print_error("源表和目标表没有共同字段")
            return False
        
        insert_count = 0
        update_count = 0
        skip_count = 0
        
        print(f"\n{Colors.BLUE}正在同步数据...{Colors.NC}")
        
        for row in source_cursor.fetchall():
            row_dict = dict(zip(source_columns, row))
            
            pk_column = common_sink[0] if field_mapping else common_source[0]
            pk_source = common_source[0]
            pk_value = row_dict[pk_source]
            
            sink_cursor.execute(f"SELECT * FROM {sink_config['database']}.{sink_config['table']} WHERE {pk_column} = ?", (pk_value,))
            existing_row = sink_cursor.fetchone()
            
            if existing_row:
                existing_dict = dict(zip(sink_columns, existing_row))
                
                needs_update = False
                for src_col, tgt_col in zip(common_source, common_sink):
                    if row_dict.get(src_col) != existing_dict.get(tgt_col):
                        needs_update = True
                        break
                
                if needs_update:
                    set_clause = ", ".join([f"{tgt_col} = ?" for tgt_col in common_sink])
                    update_sql = f"UPDATE {sink_config['database']}.{sink_config['table']} SET {set_clause} WHERE {pk_column} = ?"
                    params = [row_dict[src_col] for src_col in common_source] + [pk_value]
                    sink_cursor.execute(update_sql, params)
                    update_count += 1
                else:
                    skip_count += 1
            else:
                columns_str = ", ".join(common_sink)
                placeholders = ", ".join(["?" for _ in common_sink])
                insert_sql = f"INSERT INTO {sink_config['database']}.{sink_config['table']} ({columns_str}) VALUES ({placeholders})"
                params = [row_dict[src_col] for src_col in common_source]
                sink_cursor.execute(insert_sql, params)
                insert_count += 1
        
        sink_conn.commit()
        
        source_cursor.close()
        sink_cursor.close()
        source_conn.close()
        sink_conn.close()
        
        print(f"\n{Colors.GREEN}同步完成！{Colors.NC}")
        print(f"  插入: {insert_count} 条")
        print(f"  更新: {update_count} 条")
        print(f"  跳过: {skip_count} 条")
        
        return True
        
    except Exception as e:
        print_error(f"同步失败：{e}")
        return False

# ==================== Git 仓库同步相关函数 ====================

def run_git_command(cmd, cwd=None):
    """执行 git 命令"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=120
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "命令执行超时"
    except Exception as e:
        return -1, "", str(e)

def check_git_installed():
    """检查 git 是否安装"""
    returncode, _, _ = run_git_command(["git", "--version"])
    return returncode == 0

def clone_repository(repo_url, local_path):
    """克隆远程仓库"""
    print(f"\n{Colors.BLUE}正在克隆仓库：{repo_url}{Colors.NC}")
    print(f"{Colors.BLUE}目标路径：{local_path}{Colors.NC}")
    
    if os.path.exists(local_path):
        print_error(f"错误：路径 '{local_path}' 已存在")
        return False
    
    cmd = ["git", "clone", repo_url, local_path]
    returncode, stdout, stderr = run_git_command(cmd)
    
    if returncode == 0:
        print_success("仓库克隆成功")
        print(f"\n{Colors.BLUE}克隆输出：{Colors.NC}")
        print(stdout)
        return True
    else:
        print_error(f"仓库克隆失败")
        if stderr:
            print(f"\n{Colors.RED}错误信息：{stderr}{Colors.NC}")
        return False

def check_updates(local_path):
    """检查远程是否有更新"""
    if not os.path.exists(local_path):
        print_error(f"错误：路径 '{local_path}' 不存在")
        return None
    
    returncode, current_branch, _ = run_git_command(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=local_path
    )
    if returncode != 0:
        print_error("无法获取当前分支")
        return None
    
    current_branch = current_branch.strip()
    print(f"\n{Colors.BLUE}当前分支：{current_branch}{Colors.NC}")
    
    returncode, local_commit, _ = run_git_command(
        ["git", "rev-parse", "HEAD"],
        cwd=local_path
    )
    if returncode != 0:
        print_error("无法获取本地提交")
        return None
    
    returncode, _, stderr = run_git_command(
        ["git", "fetch", "origin"],
        cwd=local_path
    )
    if returncode != 0:
        print_error(f"无法获取远程信息：{stderr}")
        return None
    
    returncode, remote_commit, _ = run_git_command(
        ["git", "rev-parse", f"origin/{current_branch}"],
        cwd=local_path
    )
    if returncode != 0:
        print_error("无法获取远程提交")
        return None
    
    local_commit = local_commit.strip()
    remote_commit = remote_commit.strip()
    
    print(f"本地提交：{local_commit[:7]}")
    print(f"远程提交：{remote_commit[:7]}")
    
    if local_commit == remote_commit:
        print_success("本地代码已是最新")
        return 0
    else:
        print(f"{Colors.YELLOW}发现新提交！{Colors.NC}")
        returncode, log, _ = run_git_command(
            ["git", "log", "--oneline", f"{local_commit}..{remote_commit}"],
            cwd=local_path
        )
        if returncode == 0 and log:
            print(f"\n{Colors.BLUE}更新日志：{Colors.NC}")
            print(log)
        return 1

def pull_updates(local_path):
    """拉取最新代码"""
    if not os.path.exists(local_path):
        print_error(f"错误：路径 '{local_path}' 不存在")
        return False
    
    print(f"\n{Colors.BLUE}正在拉取最新代码到：{local_path}{Colors.NC}")
    
    cmd = ["git", "pull", "origin"]
    returncode, stdout, stderr = run_git_command(cmd, cwd=local_path)
    
    if returncode == 0:
        print_success("代码拉取成功")
        if stdout:
            print(f"\n{Colors.BLUE}拉取输出：{Colors.NC}")
            print(stdout)
        return True
    else:
        print_error("代码拉取失败")
        if stderr:
            print(f"\n{Colors.RED}错误信息：{stderr}{Colors.NC}")
        return False

def get_repo_info(local_path):
    """获取仓库信息"""
    if not os.path.exists(local_path):
        print_error(f"错误：路径 '{local_path}' 不存在")
        return
    
    print(f"\n{Colors.BLUE}仓库信息：{Colors.NC}")
    
    returncode, remote_url, _ = run_git_command(
        ["git", "config", "--get", "remote.origin.url"],
        cwd=local_path
    )
    if returncode == 0:
        print(f"远程地址：{remote_url.strip()}")
    
    returncode, branch, _ = run_git_command(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=local_path
    )
    if returncode == 0:
        print(f"当前分支：{branch.strip()}")
    
    returncode, status, _ = run_git_command(
        ["git", "status", "--short"],
        cwd=local_path
    )
    if returncode == 0:
        if status.strip() == "":
            print_success("工作区干净")
        else:
            print(f"{Colors.YELLOW}工作区有修改：{Colors.NC}")
            print(status)

def get_git_configs_path():
    """获取 Git 配置文件路径"""
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    return os.path.join(config_dir, 'git_monitor_configs.json')

def load_git_configs():
    """加载 Git 监控配置"""
    config_path = get_git_configs_path()
    if not os.path.exists(config_path):
        return []
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_git_configs(configs):
    """保存 Git 监控配置"""
    config_path = get_git_configs_path()
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(configs, f, ensure_ascii=False, indent=2)

def config_git_monitor_task():
    """配置 Git 仓库监控任务"""
    print_header("配置 Git 监控任务")
    
    repo_url = get_input("仓库地址 (HTTPS/SSH): ", required=True)
    local_path = get_input("本地仓库路径: ", required=True)
    
    if not os.path.exists(local_path):
        print_error(f"错误：路径 '{local_path}' 不存在，请先克隆仓库")
        return None
    
    returncode, branch, _ = run_git_command(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=local_path
    )
    if returncode != 0:
        print_error("无法获取分支信息")
        return None
    
    branch = branch.strip()
    
    print(f"\n{Colors.BLUE}检测到信息：{Colors.NC}")
    print(f"  仓库：{repo_url}")
    print(f"  路径：{local_path}")
    print(f"  分支：{branch}")
    
    print(f"\n{Colors.BLUE}选择监控模式：{Colors.NC}")
    print("  1) 自动拉取（检测到更新后自动拉取）")
    print("  2) 手动拉取（检测到更新后通知，由用户决定是否拉取）")
    
    mode_choice = get_input("请选择模式 [1-2] [默认：2]: ", default="2")
    mode = "auto" if mode_choice == "1" else "manual"
    
    polling_interval = get_input("轮询间隔（秒）[默认：60]: ", default="60")
    
    git_config = {
        'repo_url': repo_url,
        'local_path': local_path,
        'branch': branch,
        'mode': mode,
        'polling_interval': int(polling_interval),
        'status': 'stopped'
    }
    
    configs = load_git_configs()
    configs.append(git_config)
    save_git_configs(configs)
    
    print_success("Git 监控任务配置完成！")
    return git_config

def start_git_monitor():
    """启动 Git 监控服务"""
    print_header("启动 Git 监控服务")
    
    configs = load_git_configs()
    if not configs:
        print_error("没有配置 Git 监控任务，请先配置")
        return
    
    print(f"\n{Colors.GREEN}已配置的 Git 监控任务：{Colors.NC}\n")
    for i, cfg in enumerate(configs, 1):
        status = cfg.get('status', 'stopped')
        mode = "自动拉取" if cfg.get('mode') == 'auto' else "手动拉取"
        status_color = Colors.GREEN if status == 'running' else Colors.YELLOW
        print(f"  {i}) {cfg['local_path']} [{status_color}{status}{Colors.NC}] ({mode})")
    
    task_choice = get_input(f"\n请选择要启动的任务 [1-{len(configs)}]： ", default="1")
    
    if task_choice.isdigit():
        idx = int(task_choice) - 1
        if 0 <= idx < len(configs):
            git_config = configs[idx]
        else:
            print_error("无效的选择")
            return
    else:
        print_error("无效的选择")
        return
    
    print_success(f"Git 监控已启动，正在监控：{git_config['local_path']}")
    print(f"\n{Colors.YELLOW}按 Ctrl+C 停止监控{Colors.NC}")
    
    try:
        git_monitor_loop(git_config)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}监控已停止{Colors.NC}")

def git_monitor_loop(git_config):
    """Git 监控循环"""
    import time
    
    local_path = git_config['local_path']
    mode = git_config.get('mode', 'manual')
    polling_interval = git_config.get('polling_interval', 60)
    
    while True:
        try:
            returncode, current_branch, _ = run_git_command(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=local_path
            )
            if returncode != 0:
                time.sleep(polling_interval)
                continue
            
            current_branch = current_branch.strip()
            
            returncode, local_commit, _ = run_git_command(
                ["git", "rev-parse", "HEAD"],
                cwd=local_path
            )
            if returncode != 0:
                time.sleep(polling_interval)
                continue
            
            returncode, _, stderr = run_git_command(
                ["git", "fetch", "origin"],
                cwd=local_path
            )
            if returncode != 0:
                print_error(f"获取远程信息失败：{stderr[:50]}")
                time.sleep(polling_interval)
                continue
            
            returncode, remote_commit, _ = run_git_command(
                ["git", "rev-parse", f"origin/{current_branch}"],
                cwd=local_path
            )
            if returncode != 0:
                time.sleep(polling_interval)
                continue
            
            local_commit = local_commit.strip()
            remote_commit = remote_commit.strip()
            
            if local_commit != remote_commit:
                print(f"\n{Colors.YELLOW}[{datetime.now().strftime('%H:%M:%S')}] 发现新提交：{remote_commit[:7]}{Colors.NC}")
                
                returncode, log, _ = run_git_command(
                    ["git", "log", "--oneline", f"{local_commit}..{remote_commit}"],
                    cwd=local_path
                )
                if returncode == 0 and log:
                    print(f"{Colors.BLUE}更新内容：{Colors.NC}")
                    print(log.strip())
                
                if mode == 'auto':
                    print_info("自动拉取中...")
                    returncode, stdout, stderr = run_git_command(
                        ["git", "pull", "origin"],
                        cwd=local_path
                    )
                    if returncode == 0:
                        print_success("自动拉取成功")
                        if stdout:
                            print(stdout.strip())
                    else:
                        print_error(f"自动拉取失败：{stderr[:100]}")
                else:
                    pull_now = get_input(f"\n{Colors.BLUE}是否立即拉取更新？[y/N]{Colors.NC}: ", default="n").lower()
                    if pull_now == "y":
                        print_info("正在拉取中...")
                        returncode, stdout, stderr = run_git_command(
                            ["git", "pull", "origin"],
                            cwd=local_path
                        )
                        if returncode == 0:
                            print_success("拉取成功")
                            if stdout:
                                print(stdout.strip())
                        else:
                            print_error(f"拉取失败：{stderr[:100]}")
            
            time.sleep(polling_interval)
            
        except Exception as e:
            print_error(f"监控错误：{e}")
            time.sleep(polling_interval)

def stop_git_monitor():
    """停止 Git 监控服务"""
    print_header("停止 Git 监控服务")
    print_success("Git 监控服务已停止")

def view_git_monitor_status():
    """查看 Git 监控状态"""
    print_header("查看 Git 监控状态")
    
    configs = load_git_configs()
    if not configs:
        print_error("没有配置 Git 监控任务")
        return
    
    print(f"\n{Colors.GREEN}已配置的 Git 监控任务：{Colors.NC}\n")
    for i, cfg in enumerate(configs, 1):
        status = cfg.get('status', 'stopped')
        mode = "自动拉取" if cfg.get('mode') == 'auto' else "手动拉取"
        interval = cfg.get('polling_interval', 60)
        status_color = Colors.GREEN if status == 'running' else Colors.YELLOW
        
        print(f"  {i}) {cfg['local_path']}")
        print(f"     仓库：{cfg['repo_url']}")
        print(f"     分支：{cfg['branch']}")
        print(f"     模式：{mode}")
        print(f"     轮询：{interval}秒")
        print(f"     状态：[{status_color}{status}{Colors.NC}]")
        print()

def delete_git_monitor_task():
    """删除 Git 监控任务"""
    print_header("删除 Git 监控任务")
    
    configs = load_git_configs()
    if not configs:
        print_error("没有配置 Git 监控任务")
        return
    
    print(f"\n{Colors.GREEN}已配置的 Git 监控任务：{Colors.NC}\n")
    for i, cfg in enumerate(configs, 1):
        status = cfg.get('status', 'stopped')
        status_color = Colors.GREEN if status == 'running' else Colors.YELLOW
        print(f"  {i}) {cfg['local_path']} [{status_color}{status}{Colors.NC}]")
    
    task_choice = get_input(f"\n请选择要删除的任务 [1-{len(configs)}]： ", default="1")
    
    if task_choice.isdigit():
        idx = int(task_choice) - 1
        if 0 <= idx < len(configs):
            removed = configs.pop(idx)
            save_git_configs(configs)
            print_success(f"监控任务已删除：{removed['local_path']}")
        else:
            print_error("无效的选择")
    else:
        print_error("无效的选择")

def commit_changes_menu(local_path=None):
    """提交更改菜单"""
    if not local_path:
        local_path = get_input("本地仓库路径: ", required=True)
    
    if not os.path.exists(local_path):
        print_error(f"错误：路径 '{local_path}' 不存在")
        return
    
    print(f"\n{Colors.BLUE}检查工作区状态...{Colors.NC}")
    
    returncode, status_output, _ = run_git_command(
        ["git", "status", "--porcelain"],
        cwd=local_path
    )
    
    if returncode != 0:
        print_error("无法获取 Git 状态")
        return
    
    if not status_output.strip():
        print_success("工作区干净，没有可提交的更改")
        return
    
    print(f"\n{Colors.YELLOW}有更改的文件：{Colors.NC}")
    print(status_output)
    
    returncode, diff_output, _ = run_git_command(
        ["git", "diff", "--stat"],
        cwd=local_path
    )
    if returncode == 0 and diff_output:
        print(f"\n{Colors.BLUE}更改统计：{Colors.NC}")
        print(diff_output)
    
    print(f"\n{Colors.BLUE}选择操作：{Colors.NC}")
    print("  1) 提交所有更改")
    print("  2) 选择要提交的文件")
    print("  3) 取消")
    
    choice = get_input("请选择 [1-3] [默认：3]: ", default="3")
    
    if choice == "1":
        stage_all = get_input("是否暂存所有文件？[y/N]: ", default="n").lower()
        if stage_all == "y":
            returncode, _, stderr = run_git_command(
                ["git", "add", "-A"],
                cwd=local_path
            )
            if returncode != 0:
                print_error(f"暂存文件失败：{stderr}")
                return
            print_success("已暂存所有文件")
        else:
            returncode, _, stderr = run_git_command(
                ["git", "add", "-u"],
                cwd=local_path
            )
            if returncode != 0:
                print_error(f"暂存文件失败：{stderr}")
                return
            print_success("已暂存已跟踪文件的更改")
    
    elif choice == "2":
        print_info("请输入要暂存的文件名（多个用空格分隔）：")
        files_input = get_input("文件名: ", required=True)
        files = files_input.split()
        for f in files:
            returncode, _, stderr = run_git_command(
                ["git", "add", f],
                cwd=local_path
            )
            if returncode != 0:
                print_error(f"暂存文件 '{f}' 失败：{stderr}")
        print_success("已暂存选择的文件")
    
    elif choice == "3":
        return
    else:
        print_error("无效的选择")
        return
    
    commit_message = get_input("\n提交信息: ", required=True)
    
    returncode, _, stderr = run_git_command(
        ["git", "commit", "-m", commit_message],
        cwd=local_path
    )
    
    if returncode == 0:
        print_success(f"提交成功：{commit_message}")
        
        returncode, log, _ = run_git_command(
            ["git", "log", "--oneline", "-1"],
            cwd=local_path
        )
        if returncode == 0 and log:
            print(f"提交 ID：{log.strip()}")
    else:
        print_error(f"提交失败：{stderr}")

def push_changes(local_path=None):
    """推送代码到远程仓库"""
    if not local_path:
        local_path = get_input("本地仓库路径: ", required=True)
    
    if not os.path.exists(local_path):
        print_error(f"错误：路径 '{local_path}' 不存在")
        return
    
    print(f"\n{Colors.BLUE}检查工作区状态...{Colors.NC}")
    
    returncode, status_output, _ = run_git_command(
        ["git", "status", "--porcelain"],
        cwd=local_path
    )
    
    if returncode != 0:
        print_error("无法获取 Git 状态")
        return
    
    if status_output.strip():
        print_error("工作区有未提交的更改，请先提交")
        print(status_output)
        return
    
    returncode, branch, _ = run_git_command(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=local_path
    )
    if returncode != 0:
        print_error("无法获取分支信息")
        return
    
    branch = branch.strip()
    print(f"当前分支：{branch}")
    
    returncode, remote_branch, _ = run_git_command(
        ["git", "rev-parse", f"origin/{branch}"],
        cwd=local_path
    )
    if returncode != 0:
        print_info("远程分支不存在，将推送并创建远程分支")
        remote_branch = None
    else:
        remote_branch = remote_branch.strip()
    
    returncode, local_commit, _ = run_git_command(
        ["git", "rev-parse", "HEAD"],
        cwd=local_path
    )
    if returncode != 0:
        print_error("无法获取本地提交")
        return
    
    local_commit = local_commit.strip()
    
    if remote_branch and local_commit == remote_branch:
        print_success("本地已是最新，无需推送")
        return
    
    print_info("正在推送代码...")
    
    returncode, stdout, stderr = run_git_command(
        ["git", "push", "origin", branch],
        cwd=local_path
    )
    
    if returncode == 0:
        print_success("推送成功！")
        if stdout:
            print(stdout.strip())
    else:
        print_error(f"推送失败：{stderr}")

def git_menu():
    """Git 功能菜单"""
    print_header("Git 仓库同步工具")
    
    if not check_git_installed():
        print_error("错误：未检测到 Git 安装")
        print_info("请先安装 Git：https://git-scm.com/downloads")
        return
    
    while True:
        print("\n请选择操作：")
        print("  1) 克隆远程仓库")
        print("  2) 检查更新")
        print("  3) 拉取最新代码")
        print("  4) 查看仓库信息")
        print("  5) 提交更改")
        print("  6) 推送代码")
        print("  7) Git 仓库监控")
        print("  8) 返回主菜单")
        
        choice = get_input("请选择 [1-8] [默认：8]: ", default="8")
        
        if choice == "1":
            print("\n【克隆远程仓库】")
            repo_url = get_input("仓库地址 (HTTPS/SSH): ", required=True)
            local_path = get_input("本地路径: ", required=True)
            clone_repository(repo_url, local_path)
        
        elif choice == "2":
            print("\n【检查更新】")
            local_path = get_input("本地仓库路径: ", required=True)
            result = check_updates(local_path)
            if result == 1:
                pull_now = get_input("是否立即拉取更新？[y/N]: ", default="n").lower()
                if pull_now == "y":
                    pull_updates(local_path)
        
        elif choice == "3":
            print("\n【拉取最新代码】")
            local_path = get_input("本地仓库路径: ", required=True)
            pull_updates(local_path)
        
        elif choice == "4":
            print("\n【查看仓库信息】")
            local_path = get_input("本地仓库路径: ", required=True)
            get_repo_info(local_path)
        
        elif choice == "5":
            print("\n【提交更改】")
            local_path = get_input("本地仓库路径: ", required=True)
            commit_changes_menu(local_path)
        
        elif choice == "6":
            print("\n【推送代码】")
            local_path = get_input("本地仓库路径: ", required=True)
            push_changes(local_path)
        
        elif choice == "7":
            git_monitor_menu()
        
        elif choice == "8":
            print("\n返回主菜单...")
            break
        
        else:
            print_error("无效的选择")

def git_monitor_menu():
    """Git 仓库监控子菜单"""
    while True:
        print("\n" + "="*60)
        print("  Git 仓库监控")
        print("="*60 + "\n")
        
        print("请选择操作：")
        print("  1) 配置监控任务")
        print("  2) 启动监控")
        print("  3) 查看监控状态")
        print("  4) 删除监控任务")
        print("  5) 返回")
        
        choice = get_input("请选择 [1-5] [默认：5]: ", default="5")
        
        if choice == "1":
            config_git_monitor_task()
        elif choice == "2":
            start_git_monitor()
        elif choice == "3":
            view_git_monitor_status()
        elif choice == "4":
            delete_git_monitor_task()
        elif choice == "5":
            break
        else:
            print_error("无效的选择")

# ==================== 数据同步主逻辑 ====================

def data_sync_menu():
    """数据同步功能菜单"""
    print_header("SeaTunnel 数据采集配置向导")

    print_step(1, "选择数据源类型")

    print("选择数据源类型:")
    print("  1) MySQL 数据库")
    print("  2) HTTP API")
    print("  3) 达梦数据库")
    print("  4) 测试模式 (使用 FakeSource)")

    source_choice = get_input("请选择 [1-4] [默认：1]: ", default="1")

    source_config = None
    sink_config = None
    api_config = None

    if source_choice == "1":
        print_success("数据源：MySQL 数据库")
        print_step(2, "配置源 MySQL 数据库")

        job_name = get_input("作业名称 [默认：MySQL_to_MySQL_Sync]: ", default="MySQL_to_MySQL_Sync")
        print("选择作业模式:")
        print("  1) STREAMING (实时同步)")
        print("  2) BATCH (批量同步)")
        mode_choice = get_input("请选择 [1-2] [默认：1]: ", default="1")
        if mode_choice == "1":
            job_mode = "STREAMING"
        else:
            job_mode = "BATCH"
        parallelism = get_input("并行度 [默认：1]: ", default="1")

        is_cdc = (job_mode == "STREAMING")
        source_config = config_mysql_database(is_source=True, is_cdc=is_cdc)

        print_step(3, "配置目标 MySQL 数据库")
        sink_config = config_mysql_database(is_source=False)

        # 检查是否有同步历史记录
        history_record = check_sync_history(
            source_config['database'],
            source_config['table'],
            sink_config['database'],
            sink_config['table']
        )
        
        if history_record:
            print(f"\n{Colors.YELLOW}发现同步历史记录！{Colors.NC}")
            print(f"上次同步配置：{history_record['id']}")
            use_history = get_input("是否使用上次的字段映射配置？[y/N]: ", default="N").upper()
            
            if use_history == "Y":
                print(f"{Colors.GREEN}✓ 使用历史字段映射配置{Colors.NC}")
                field_mapping = history_record['field_mapping']
            else:
                source_columns = get_table_columns(
                    source_config['host'],
                    source_config['port'],
                    source_config['user'],
                    source_config['password'],
                    source_config['database'],
                    source_config['table']
                )

                print_step(4, "字段映射配置")
                field_mapping = configure_field_mapping(source_columns, show_step=False)
                # 保存新的映射配置
                save_sync_history(
                    source_config['database'],
                    source_config['table'],
                    sink_config['database'],
                    sink_config['table'],
                    field_mapping
                )
        else:
            source_columns = get_table_columns(
                source_config['host'],
                source_config['port'],
                source_config['user'],
                source_config['password'],
                source_config['database'],
                source_config['table']
            )

            print_step(4, "字段映射配置")
            field_mapping = configure_field_mapping(source_columns, show_step=False)
            # 保存映射配置到历史
            save_sync_history(
                source_config['database'],
                source_config['table'],
                sink_config['database'],
                sink_config['table'],
                field_mapping
            )

        if field_mapping:
            print(f"\n{Colors.BLUE}验证目标表结构...{Colors.NC}")
            sink_columns = get_table_columns(
                sink_config['host'],
                sink_config['port'],
                sink_config['user'],
                sink_config['password'],
                sink_config['database'],
                sink_config['table']
            )
            
            if sink_columns:
                sink_field_names = [col['source'] for col in sink_columns]
                mapped_target_fields = [col['target'] for col in field_mapping]
                
                missing_fields = [field for field in mapped_target_fields if field not in sink_field_names]
                if missing_fields:
                    print(f"{Colors.YELLOW}警告：目标表中缺少以下字段：{', '.join(missing_fields)}{Colors.NC}")
                    print(f"{Colors.YELLOW}建议：在目标表中创建这些字段或修改字段映射{Colors.NC}")
                    
                    continue_anyway = get_input("是否继续执行？[y/N]: ", default="n").lower()
                    if continue_anyway != "y":
                        print_error("操作已取消")
                        sys.exit(1)
            else:
                print(f"{Colors.YELLOW}目标表不存在，根据字段映射创建表结构...{Colors.NC}")
                try:
                    conn = mysql.connector.connect(
                        host=sink_config['host'],
                        port=int(sink_config['port']),
                        user=sink_config['user'],
                        password=sink_config['password'],
                        database=sink_config['database'],
                        connect_timeout=5
                    )
                    cursor = conn.cursor()
                    
                    create_table_sql = f"CREATE TABLE `{sink_config['table']}` ("
                    for i, col in enumerate(field_mapping):
                        if i > 0:
                            create_table_sql += ", "
                        mysql_type = "VARCHAR(255)"
                        if col['type'] == "INT":
                            mysql_type = "INT"
                        elif col['type'] == "DATETIME":
                            mysql_type = "DATETIME"
                        elif col['type'] == "BOOLEAN":
                            mysql_type = "BOOLEAN"
                        create_table_sql += f"`{col['target']}` {mysql_type} NULL"
                    create_table_sql += ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"
                    
                    print(f"{Colors.BLUE}执行建表SQL: {create_table_sql}{Colors.NC}")
                    cursor.execute(create_table_sql)
                    conn.commit()
                    print(f"{Colors.GREEN}✓ 目标表创建成功{Colors.NC}")
                    
                    cursor.close()
                    conn.close()
                except mysql.connector.Error as e:
                    print_error(f"创建目标表失败：{e}")
                    print_error("请手动创建目标表后再执行")
                    sys.exit(1)

    elif source_choice == "2":
        print_success("数据源：HTTP API")
        print_step(2, "配置源 API")

        print("选择 API 类型:")
        print("  1) Random User Generator API (https://randomuser.me/)")
        print("  2) 自定义 API")

        api_type = get_input("请选择 [1-2] [默认：1]: ", default="1")

        if api_type == "1":
            api_url = "https://randomuser.me/api/"
            api_method = "GET"
            content_field = "results"
            api_returns_array = True
            print_success("使用 Random User Generator API")
        else:
            api_url = get_input("API URL: ", required=True)
            print("选择 HTTP 方法:")
            print("  1) GET")
            print("  2) POST")
            method_choice = get_input("请选择 [1-2] [默认：1]: ", default="1")
            if method_choice == "1":
                api_method = "GET"
            else:
                api_method = "POST"
            content_field = get_input("JSON 内容字段 [默认：results]: ", default="results")
            
            print(f"\n{Colors.BLUE}正在测试 API 连接并解析字段...{Colors.NC}")
            default_columns = []
            api_returns_array = False
            try:
                import requests
                import json
                
                if api_method == "GET":
                    response = requests.get(api_url, timeout=10)
                else:
                    response = requests.post(api_url, timeout=10)
                
                if 200 <= response.status_code < 300:
                    data = response.json()
                    
                    if isinstance(data, list):
                        content_field = ""
                        content = data
                        api_returns_array = True
                        print(f"{Colors.GREEN}✓ API 返回数组格式，无需设置 content_field{Colors.NC}")
                    elif isinstance(data, dict):
                        content = data
                        if content_field:
                            for part in content_field.split('.'):
                                if part in content:
                                    content = content[part]
                                else:
                                    print(f"{Colors.YELLOW}警告：未找到字段 '{part}'，使用完整响应{Colors.NC}")
                                    content_field = ""
                                    content = data
                                    break
                        api_returns_array = isinstance(content, list)
                        
                        if not api_returns_array and isinstance(content, dict):
                            if "data" in content:
                                content = content["data"]
                                content_field = "data"
                                api_returns_array = isinstance(content, list)
                            elif "json" in content and isinstance(content["json"], (dict, list)):
                                content = content["json"]
                                content_field = "json"
                                api_returns_array = isinstance(content, list)
                                print(f"{Colors.GREEN}✓ 检测到嵌套数据字段 'json'{Colors.NC}")
                    
                    def extract_top_fields(obj):
                        fields = []
                        if isinstance(obj, dict):
                            for key, value in obj.items():
                                field_type = "STRING"
                                if isinstance(value, int):
                                    field_type = "INT"
                                elif isinstance(value, bool):
                                    field_type = "BOOLEAN"
                                fields.append({
                                    'source': key,
                                    'target': key,
                                    'type': field_type
                                })
                        return fields
                    
                    if isinstance(content, list) and len(content) > 0:
                        sample_item = content[0]
                        default_columns = extract_top_fields(sample_item)
                        if default_columns:
                            print(f"{Colors.GREEN}✓ 成功解析 API 字段，共 {len(default_columns)} 个字段{Colors.NC}")
                        else:
                            print(f"{Colors.YELLOW}警告：无法从 API 响应中提取字段，使用默认字段{Colors.NC}")
                            default_columns = [
                                {'source': 'id', 'target': 'id', 'type': 'INT'},
                                {'source': 'name', 'target': 'name', 'type': 'STRING'},
                                {'source': 'value', 'target': 'value', 'type': 'STRING'}
                            ]
                    elif isinstance(content, dict):
                        api_returns_array = False
                        default_columns = extract_top_fields(content)
                        if default_columns:
                            print(f"{Colors.GREEN}✓ 成功解析 API 字段，共 {len(default_columns)} 个字段{Colors.NC}")
                        else:
                            print(f"{Colors.YELLOW}警告：无法从 API 响应中提取字段，使用默认字段{Colors.NC}")
                            default_columns = [
                                {'source': 'id', 'target': 'id', 'type': 'INT'},
                                {'source': 'name', 'target': 'name', 'type': 'STRING'},
                                {'source': 'value', 'target': 'value', 'type': 'STRING'}
                            ]
                    else:
                        print(f"{Colors.YELLOW}警告：API 响应格式不符合预期，使用默认字段{Colors.NC}")
                        default_columns = [
                            {'source': 'id', 'target': 'id', 'type': 'INT'},
                            {'source': 'name', 'target': 'name', 'type': 'STRING'},
                            {'source': 'value', 'target': 'value', 'type': 'STRING'}
                        ]
                else:
                    print(f"{Colors.YELLOW}警告：API 请求失败 (状态码: {response.status_code})，使用默认字段{Colors.NC}")
                    default_columns = [
                        {'source': 'id', 'target': 'id', 'type': 'INT'},
                        {'source': 'name', 'target': 'name', 'type': 'STRING'},
                        {'source': 'value', 'target': 'value', 'type': 'STRING'}
                    ]
            except Exception as e:
                print(f"{Colors.YELLOW}警告：无法连接到 API ({e})，使用默认字段{Colors.NC}")
                default_columns = [
                    {'source': 'id', 'target': 'id', 'type': 'INT'},
                    {'source': 'name', 'target': 'name', 'type': 'STRING'},
                    {'source': 'value', 'target': 'value', 'type': 'STRING'}
                ]
            
            print_success("自定义 API 配置完成")

        api_config = {
            "url": api_url,
            "method": api_method,
            "content_field": content_field,
            "returns_array": api_returns_array
        }

        if api_type == "1":
            default_columns = [
                {'source': 'name.first', 'target': 'first_name', 'type': 'STRING'},
                {'source': 'name.last', 'target': 'last_name', 'type': 'STRING'},
                {'source': 'email', 'target': 'email', 'type': 'STRING'},
                {'source': 'gender', 'target': 'gender', 'type': 'STRING'},
                {'source': 'dob.age', 'target': 'age', 'type': 'INT'},
                {'source': 'location.city', 'target': 'city', 'type': 'STRING'}
            ]

        print_step(3, "字段映射配置")
        field_mapping = configure_field_mapping(default_columns, show_step=False)

        print_step(4, "配置目标 MySQL 数据库")
        sink_config = config_mysql_database(is_source=False)

        if field_mapping:
            print(f"\n{Colors.BLUE}验证目标表结构...{Colors.NC}")
            sink_columns = get_table_columns(
                sink_config['host'],
                sink_config['port'],
                sink_config['user'],
                sink_config['password'],
                sink_config['database'],
                sink_config['table']
            )
            
            if sink_columns:
                sink_field_names = [col['source'] for col in sink_columns]
                mapped_target_fields = [col['target'] for col in field_mapping]
                
                missing_fields = [field for field in mapped_target_fields if field not in sink_field_names]
                if missing_fields:
                    print(f"{Colors.YELLOW}警告：目标表中缺少以下字段：{', '.join(missing_fields)}{Colors.NC}")
                    print(f"{Colors.YELLOW}建议：在目标表中创建这些字段或修改字段映射{Colors.NC}")
                    
                    continue_anyway = get_input("是否继续执行？[y/N]: ", default="n").lower()
                    if continue_anyway != "y":
                        print_error("操作已取消")
                        sys.exit(1)
            else:
                print(f"{Colors.YELLOW}目标表不存在，根据字段映射创建表结构...{Colors.NC}")
                try:
                    conn = mysql.connector.connect(
                        host=sink_config['host'],
                        port=int(sink_config['port']),
                        user=sink_config['user'],
                        password=sink_config['password'],
                        database=sink_config['database'],
                        connect_timeout=5
                    )
                    cursor = conn.cursor()
                    
                    create_table_sql = f"CREATE TABLE `{sink_config['table']}` ("
                    for i, col in enumerate(field_mapping):
                        if i > 0:
                            create_table_sql += ", "
                        mysql_type = "VARCHAR(255)"
                        if col['type'] == "INT":
                            mysql_type = "INT"
                        elif col['type'] == "DATETIME":
                            mysql_type = "DATETIME"
                        elif col['type'] == "BOOLEAN":
                            mysql_type = "BOOLEAN"
                        create_table_sql += f"`{col['target']}` {mysql_type} NULL"
                    create_table_sql += ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"
                    
                    print(f"{Colors.BLUE}执行建表SQL: {create_table_sql}{Colors.NC}")
                    cursor.execute(create_table_sql)
                    conn.commit()
                    print(f"{Colors.GREEN}✓ 目标表创建成功{Colors.NC}")
                    
                    cursor.close()
                    conn.close()
                except mysql.connector.Error as e:
                    print_error(f"创建目标表失败：{e}")
                    print_error("请手动创建目标表后再执行")
                    sys.exit(1)

        job_name = get_input("作业名称 [默认：API_to_MySQL_Sync]: ", default="API_to_MySQL_Sync")
        job_mode = get_input("作业模式 [STREAMING/BATCH 默认：BATCH]: ", default="BATCH").upper()
        parallelism = get_input("并行度 [默认：1]: ", default="1")

    elif source_choice == "3":
        print_success("数据源：达梦数据库")
        
        print("\n选择达梦数据同步模式:")
        print("  1) CDC 实时监控（基于触发器）")
        print("  2) 普通批量同步")
        
        dameng_mode = get_input("请选择 [1-2] [默认：1]: ", default="1")
        
        if dameng_mode == "1":
            dameng_cdc_menu()
            return
        
        print_step(2, "配置源达梦数据库")
        source_config = config_dameng_database(is_source=True)

        print_step(3, "配置目标达梦数据库")
        sink_config = config_dameng_database(is_source=False, allow_create=True)

        # 检查是否有同步历史记录
        history_record = check_sync_history(
            source_config['database'],
            source_config['table'],
            sink_config['database'],
            sink_config['table']
        )
        
        if history_record:
            print(f"\n{Colors.YELLOW}发现同步历史记录！{Colors.NC}")
            print(f"上次同步配置：{history_record['id']}")
            use_history = get_input("是否使用上次的字段映射配置？[y/N]: ", default="N").upper()
            
            if use_history == "Y":
                print(f"{Colors.GREEN}✓ 使用历史字段映射配置{Colors.NC}")
                field_mapping = history_record['field_mapping']
            else:
                print_step(4, "字段映射配置")
                source_columns = source_config.get('columns', [])
                if not source_columns:
                    source_columns = get_dameng_table_columns(
                        source_config['host'],
                        source_config['port'],
                        source_config['user'],
                        source_config['password'],
                        source_config['database'],
                        source_config['table']
                    )
                field_mapping = configure_field_mapping(source_columns, show_step=False)
                # 保存新的映射配置
                save_sync_history(
                    source_config['database'],
                    source_config['table'],
                    sink_config['database'],
                    sink_config['table'],
                    field_mapping
                )
        else:
            print_step(4, "字段映射配置")
            source_columns = source_config.get('columns', [])
            if not source_columns:
                source_columns = get_dameng_table_columns(
                    source_config['host'],
                    source_config['port'],
                    source_config['user'],
                    source_config['password'],
                    source_config['database'],
                    source_config['table']
                )
            field_mapping = configure_field_mapping(source_columns, show_step=False)
            # 保存映射配置到历史
            save_sync_history(
                source_config['database'],
                source_config['table'],
                sink_config['database'],
                sink_config['table'],
                field_mapping
            )

        job_name = get_input("作业名称 [默认：Dameng_to_Dameng_Sync]: ", default="Dameng_to_Dameng_Sync")
        job_mode = "BATCH"
        parallelism = "1"

    elif source_choice == "4":
        print_success("使用测试模式 (FakeSource)")
        print_step(2, "配置作业信息")
        job_name = get_input("作业名称 [默认：FakeSource_Test]: ", default="FakeSource_Test")
        job_mode = get_input("作业模式 [默认：BATCH]: ", default="BATCH").upper()
        parallelism = get_input("并行度 [默认：1]: ", default="1")

    else:
        print_error("无效的选择")
        sys.exit(1)

    print_step(5, "确认并执行")
    
    print(f"\n{Colors.BLUE}========== 配置确认 =========={Colors.NC}")
    print(f"作业名称: {job_name}")
    print(f"作业模式: {job_mode}")
    print(f"并行度: {parallelism}")
    
    if source_config:
        print(f"\n{Colors.BLUE}源数据源:{Colors.NC}")
        if source_choice == "3":
            print(f"  类型: 达梦数据库")
            print(f"  主机: {source_config['host']}:{source_config['port']}")
            print(f"  数据库: {source_config['database']}")
            print(f"  表: {source_config['table']}")
            if field_mapping:
                print(f"  字段数量: {len(field_mapping)}")
        else:
            print(f"  类型: MySQL 数据库")
            print(f"  主机: {source_config['host']}:{source_config['port']}")
            print(f"  数据库: {source_config['database']}")
            print(f"  表: {source_config['table']}")
    
    if api_config:
        print(f"\n{Colors.BLUE}API 配置:{Colors.NC}")
        print(f"  URL: {api_config['url']}")
        print(f"  方法: {api_config['method']}")
        print(f"  内容字段: {api_config['content_field']}")
    
    if sink_config:
        print(f"\n{Colors.BLUE}目标数据源:{Colors.NC}")
        if source_choice == "3":
            print(f"  类型: 达梦数据库")
            print(f"  主机: {sink_config['host']}:{sink_config['port']}")
            print(f"  数据库: {sink_config['database']}")
            print(f"  表: {sink_config['table']}")
        else:
            print(f"  类型: MySQL 数据库")
            print(f"  主机: {sink_config['host']}:{sink_config['port']}")
            print(f"  数据库: {sink_config['database']}")
            print(f"  表: {sink_config['table']}")
    
    print(f"{Colors.BLUE}==============================={Colors.NC}")
    
    confirm = get_input("\n确认以上配置并执行？[Y/n]: ", default="y").lower()
    if confirm != "y":
        print_error("操作已取消")
        sys.exit(0)

    output_dir = Path("config")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_config = output_dir / f"{job_name}.conf"

    if source_choice == "3":
        print(f"\n{Colors.BLUE}开始执行达梦数据库同步...{Colors.NC}")
        sync_dameng_data(source_config, sink_config, field_mapping)
        return
    
    primary_keys = ""
    source_query_fields = "*"
    transform_config = ""
    if field_mapping:
        # 分别处理BATCH和STREAMING模式
        if job_mode == "STREAMING":
            # STREAMING（CDC）模式：主键用目标字段名（因为FieldMapper会将字段映射为目标名）
            primary_keys = field_mapping[0]['target'] if field_mapping else ""
            # 构建transform的FieldMapper配置
            field_mapper_lines = '\n'.join([f'      {col["source"]} = {col["target"]}' for col in field_mapping])
            transform_config = f"""transform {{
  FieldMapper {{
    source_table_name = "default"
    target_table_name = "default"
    field_mapper = {{
{field_mapper_lines}
    }}
  }}
}}
"""
        else:
            # BATCH模式：主键用目标字段名，使用source query的SQL别名
            primary_keys = field_mapping[0]['target'] if field_mapping else ""
            transform_config = ""
        # 构建 source query 字段列表（使用别名，仅对BATCH模式有效）
        source_query_fields = ', '.join([f'"{col["source"]}" AS "{col["target"]}"' for col in field_mapping])

    if source_choice == "1":
        if job_mode == "STREAMING":
            config_content = f"""# ============================================
# SeaTunnel CDC 配置（自动生成）
# 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# ============================================

env {{
  job.mode = "STREAMING"
  job.name = "{job_name}"
  parallelism = {parallelism}
}}

source {{
  MySQL-CDC {{
    base-url = "jdbc:mysql://{source_config['host']}:{source_config['port']}/?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai"
    hostname = "{source_config['host']}"
    port = {source_config['port']}
    username = "{source_config['user']}"
    password = "{source_config['password']}"
    database-names = "{source_config['database']}"
    table-names = "{source_config['database']}.{source_config['table']}"
    server-id = {source_config['server_id']}
    startup.mode = "{source_config['startup_mode']}"
  }}
}}

{transform_config}

sink {{
  Jdbc {{
    url = "jdbc:mysql://{sink_config['host']}:{sink_config['port']}/{sink_config['database']}?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai&rewriteBatchedStatements=true"
    driver = "com.mysql.cj.jdbc.Driver"
    user = "{sink_config['user']}"
    password = "{sink_config['password']}"
    database = "{sink_config['database']}"
    table = "{sink_config['table']}"
    batch_size = 100
    generate_sink_sql = true
    save_mode = "upsert"
    primary_keys = "{primary_keys}"
  }}
}}
"""
        else:
            config_content = f"""# ============================================
# SeaTunnel 配置（自动生成）
# 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# ============================================

env {{
  job.mode = "BATCH"
  job.name = "{job_name}"
  parallelism = {parallelism}
}}

source {{
  Jdbc {{
    url = "jdbc:mysql://{source_config['host']}:{source_config['port']}/{source_config['database']}?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai"
    driver = "com.mysql.cj.jdbc.Driver"
    user = "{source_config['user']}"
    password = "{source_config['password']}"
    query = "SELECT {source_query_fields} FROM `{source_config['database']}`.`{source_config['table']}`"
  }}
}}

sink {{
  Jdbc {{
    url = "jdbc:mysql://{sink_config['host']}:{sink_config['port']}/{sink_config['database']}?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai&rewriteBatchedStatements=true"
    driver = "com.mysql.cj.jdbc.Driver"
    user = "{sink_config['user']}"
    password = "{sink_config['password']}"
    database = "{sink_config['database']}"
    table = "{sink_config['table']}"
    batch_size = 100
    generate_sink_sql = true
    save_mode = "upsert"
    primary_keys = "{primary_keys}"
  }}
}}
"""
    elif source_choice == "2":
        config_content = f"""# ============================================
# SeaTunnel API 配置（自动生成）
# 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# ============================================

env {{
  job.mode = "{job_mode}"
  job.name = "{job_name}"
  parallelism = {parallelism}
}}

source {{
  HttpSource {{
    url = "{api_config['url']}"
    method = "{api_config['method']}"
    format = "json"
    content_field = "{api_config['content_field']}"
  }}
}}

transform {{
  FieldMapper {{
    source_table_name = "default_http_source_table_name"
    target_table_name = "default_http_source_table_name"
    field_mapper = {{
{chr(10).join([f"      {col['source']} = {col['target']}" for col in field_mapping])}
    }}
  }}
}}

sink {{
  Jdbc {{
    url = "jdbc:mysql://{sink_config['host']}:{sink_config['port']}/{sink_config['database']}?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai&rewriteBatchedStatements=true"
    driver = "com.mysql.cj.jdbc.Driver"
    user = "{sink_config['user']}"
    password = "{sink_config['password']}"
    database = "{sink_config['database']}"
    table = "{sink_config['table']}"
    batch_size = 100
    generate_sink_sql = true
    save_mode = "upsert"
    primary_keys = [{primary_keys}]
  }}
}}
"""
    else:
        config_content = f"""# ============================================
# SeaTunnel 测试配置（自动生成）
# 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# ============================================

env {{
  job.mode = "{job_mode}"
  job.name = "{job_name}"
  parallelism = {parallelism}
}}

source {{
  FakeSource {{
    parallelism = {parallelism}
    schema = {{
      fields {{
        name = "string"
        age = "int"
        email = "string"
      }}
    }}
    row.num = 3
    result_table_name = "fake"
  }}
}}

sink {{
  Console {{
    parallelism = 1
  }}
}}
"""

    with open(output_config, 'w', encoding='utf-8') as f:
        f.write(config_content)

    print_success(f"配置文件已生成：{output_config}")

    print(f"\n{Colors.BLUE}========== 生成的配置文件内容 =========={Colors.NC}")
    print(config_content)
    print(f"{Colors.BLUE}==========================================={Colors.NC}\n")

    if job_mode == "STREAMING" and source_choice == "1":
        print(f"{Colors.YELLOW}注意：CDC 模式会持续监听 MySQL binlog，任务不会自动结束{Colors.NC}")
        print(f"{Colors.YELLOW}按 Ctrl+C 可以停止任务{Colors.NC}\n")

    print(f"{Colors.BLUE}准备执行 SeaTunnel 任务...{Colors.NC}\n")

    seatunnel_bin = None
    if os.name == 'nt':
        if os.environ.get("SEATUNNEL_HOME"):
            seatunnel_bin = os.path.join(os.environ["SEATUNNEL_HOME"], "bin", "seatunnel.cmd")
        elif os.path.exists(r"D:\software\apache-seatunnel-2.3.5\bin\seatunnel.cmd"):
            seatunnel_bin = r"D:\software\apache-seatunnel-2.3.5\bin\seatunnel.cmd"
        elif os.path.exists(os.path.join(os.getcwd(), "bin", "seatunnel.cmd")):
            seatunnel_bin = os.path.join(os.getcwd(), "bin", "seatunnel.cmd")
    else:
        if os.environ.get("SEATUNNEL_HOME"):
            seatunnel_bin = os.path.join(os.environ["SEATUNNEL_HOME"], "bin/seatunnel.sh")
        elif os.path.exists("/opt/seatunnel/bin/seatunnel.sh"):
            seatunnel_bin = "/opt/seatunnel/bin/seatunnel.sh"
        elif os.path.exists(os.path.expanduser("~/seatunnel/bin/seatunnel.sh")):
            seatunnel_bin = os.path.expanduser("~/seatunnel/bin/seatunnel.sh")

    if not seatunnel_bin or not os.path.exists(seatunnel_bin):
        print(f"{Colors.YELLOW}警告：未找到 SeaTunnel 安装路径{Colors.NC}")
        print("\n请设置 SEATUNNEL_HOME 环境变量或手动执行以下命令:")
        if os.name == 'nt':
            print(f"\n  seatunnel.cmd --config \"{output_config}\" -m local\n")
        else:
            print(f"\n  seatunnel.sh --config \"{output_config}\" -m local\n")
        return

    print(f"{Colors.GREEN}找到 SeaTunnel: {seatunnel_bin}{Colors.NC}\n")

    config_path = str(output_config).replace('\\', '/')
    print(f"{Colors.BLUE}执行命令：{seatunnel_bin} --config \"{config_path}\" -m local{Colors.NC}\n")

    cmd = [seatunnel_bin, "--config", config_path, "-m", "local"]

    try:
        result = subprocess.run(cmd, capture_output=False)
        exit_code = result.returncode
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}任务被用户中断{Colors.NC}")
        exit_code = 0
    except Exception as e:
        print_error(f"执行命令失败：{e}")
        exit_code = 1

    if exit_code == 0:
        print(f"\n{Colors.GREEN}{'=' * 50}{Colors.NC}")
        print(f"{Colors.GREEN}  ✓ 任务执行完成！{Colors.NC}")
        print(f"{Colors.GREEN}{'=' * 50}{Colors.NC}")
    else:
        print(f"\n{Colors.RED}{'=' * 50}{Colors.NC}")
        print(f"{Colors.RED}  ✗ 任务执行失败 (退出码：{exit_code}){Colors.NC}")
        print(f"{Colors.RED}{'=' * 50}{Colors.NC}")
        sys.exit(exit_code)

# ==================== 主菜单 ====================

def main():
    while True:
        print_header("数据同步与Git仓库管理工具")
        
        print("\n请选择功能模块：")
        print("  1) 数据同步（SeaTunnel 配置向导）")
        print("  2) Git 仓库同步")
        if FASTAPI_AVAILABLE:
            print("  3) 启动 API 服务器")
            print("  4) 退出")
        else:
            print("  3) 退出")
        
        if FASTAPI_AVAILABLE:
            choice = get_input("请选择 [1-4] [默认：4]: ", default="4")
        else:
            choice = get_input("请选择 [1-3] [默认：3]: ", default="3")
        
        if choice == "1":
            data_sync_menu()
        elif choice == "2":
            git_menu()
        elif choice == "3" and FASTAPI_AVAILABLE:
            port_input = get_input("请输入 API 服务器端口 [默认：8000]: ", default="8000")
            port = int(port_input) if port_input else 8000
            print_success(f"启动 API 服务器 on http://0.0.0.0:{port}")
            print_info(f"API 文档: http://0.0.0.0:{port}/docs")
            uvicorn.run(app, host="0.0.0.0", port=port)
        elif (choice == "3" and not FASTAPI_AVAILABLE) or (choice == "4" and FASTAPI_AVAILABLE):
            print("\n感谢使用！")
            break
        else:
            print_error("无效的选择")

# ==================== 达梦 CDC 实时监控相关函数 ====================

def dameng_cdc_menu():
    """达梦 CDC 实时监控主菜单"""
    while True:
        print_header("达梦 CDC 实时监控")
        
        print("\n请选择操作：")
        print("  1) 配置 CDC 监控任务")
        print("  2) 启动 CDC 监控服务")
        print("  3) 停止 CDC 监控服务")
        print("  4) 查看监控状态")
        print("  5) 删除监控任务")
        print("  6) 返回主菜单")
        
        choice = get_input("请选择 [1-6] [默认：6]: ", default="6")
        
        if choice == "1":
            config_cdc_task()
        elif choice == "2":
            start_cdc_monitor()
        elif choice == "3":
            stop_cdc_monitor()
        elif choice == "4":
            view_cdc_status()
        elif choice == "5":
            delete_cdc_task()
        elif choice == "6":
            break
        else:
            print_error("无效的选择")

def config_cdc_task():
    """配置 CDC 监控任务"""
    print_header("配置 CDC 监控任务")
    
    print_step(1, "配置源达梦数据库")
    source_config = config_dameng_database_for_cdc()
    
    print_step(2, "选择要监控的表")
    table_name = source_config['table']
    print(f"{Colors.GREEN}✓ 已选择监控表：{table_name}{Colors.NC}")
    
    print_step(3, "检测主键字段")
    primary_key = get_dameng_primary_key(
        source_config['host'],
        source_config['port'],
        source_config['user'],
        source_config['password'],
        source_config['database'],
        table_name
    )
    
    if not primary_key:
        print_error("无法自动检测主键，请手动输入主键字段名")
        primary_key = get_input("请输入主键字段名： ", required=True)
    else:
        print(f"{Colors.GREEN}✓ 自动检测到主键字段：{primary_key}{Colors.NC}")
    
    monitored_table = {
        'table_name': table_name,
        'primary_key': primary_key,
        'columns': source_config['columns']
    }
    
    print_step(4, "配置目标达梦数据库")
    target_config = config_dameng_for_cdc()
    
    print_step(5, "配置监控选项")
    polling_interval = get_input("轮询间隔（秒）[默认：5]: ", default="5")
    
    cdc_config = {
        'source': source_config,
        'monitored_table': monitored_table,
        'target_type': 'dameng',
        'target': target_config,
        'polling_interval': int(polling_interval),
        'status': 'stopped'
    }
    
    save_cdc_config(cdc_config)
    print_success("CDC 监控任务配置完成！")

def config_dameng_database_for_cdc():
    """配置达梦数据库连接（用于 CDC）"""
    return config_dameng_database(is_source=True)

def config_mysql_for_cdc():
    """配置 MySQL 数据库连接（用于 CDC 目标）"""
    print(f"{Colors.BLUE}--- 配置目标 MySQL 数据库 ---{Colors.NC}\n")
    
    while True:
        host = get_input("目标 MySQL 主机地址 [默认：127.0.0.1]: ", default="127.0.0.1")
        port = get_input("目标 MySQL 端口 [默认：3306]: ", default="3306")
        user = get_input("目标 MySQL 用户名： ", required=True)
        password = get_input("目标 MySQL 密码： ", required=True, hide=True)
        
        databases = get_databases(host, port, user, password)
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
            database = get_input("目标数据库名： ", required=True)
        
        if not test_mysql_connection(host, port, user, password, database):
            retry = get_input("连接失败，是否重新输入？[y/N]: ", default="y").lower()
            if retry == "y":
                continue
            else:
                print_error("操作已取消")
                sys.exit(1)
        
        tables = get_database_tables(host, port, user, password, database)
        
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
                        retry = get_input("是否重新输入表名？[y/N]: ", default="y").lower()
                        if retry == "y":
                            continue
                        else:
                            print_error("操作已取消")
                            sys.exit(1)
        else:
            table = get_input("目标表名： ", required=True)
        
        break
    
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
        "table": table
    }

def config_dameng_for_cdc():
    """配置达梦数据库连接（用于 CDC 目标）"""
    return config_dameng_database(is_source=False)

def select_monitored_table(source_config):
    """选择要监控的表"""
    tables = get_dameng_tables(
        source_config['host'],
        source_config['port'],
        source_config['user'],
        source_config['password'],
        source_config['database']
    )
    
    if not tables or len(tables) == 0:
        print_error("数据库中没有表")
        return None
    
    print(f"\n{Colors.GREEN}数据库 '{source_config['database']}' 中的表：{Colors.NC}")
    for i, tbl in enumerate(tables, 1):
        print(f"  {i}) {tbl}")
    
    while True:
        table_choice = get_input(f"\n请选择要监控的表 [1-{len(tables)}] 或输入表名： ", required=True)
        
        if table_choice.isdigit():
            idx = int(table_choice)
            if 1 <= idx <= len(tables):
                table = tables[idx - 1]
                print(f"{Colors.GREEN}✓ 已选择监控表：{table}{Colors.NC}")
                break
            else:
                print_error(f"请输入 1-{len(tables)} 之间的数字")
        else:
            table = table_choice
            print(f"{Colors.GREEN}✓ 已选择监控表：{table}{Colors.NC}")
            break
    
    columns = get_dameng_table_columns(
        source_config['host'],
        source_config['port'],
        source_config['user'],
        source_config['password'],
        source_config['database'],
        table
    )
    
    if columns and len(columns) > 0:
        print(f"\n{Colors.GREEN}表 '{table}' 的字段：{Colors.NC}")
        for i, col in enumerate(columns, 1):
            print(f"  {i}) {col['source']} ({col['type']})")
    
    primary_key = get_input("\n请输入主键字段名（用于识别记录）： ", required=True)
    
    return {
        'table_name': table,
        'columns': columns,
        'primary_key': primary_key
    }

def create_change_log_table(host, port, user, password, database):
    """创建变更日志表"""
    print(f"\n{Colors.BLUE}创建变更日志表...{Colors.NC}")
    
    try:
        conn_str = f"DRIVER={{DM8 ODBC DRIVER}};SERVER={host};PORT={port};UID={user};PWD={password};DATABASE={database}"
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        qualified_log_table = f'"{database}"."DAMENG_CDC_CHANGE_LOG"'
        
        # 先尝试删除旧表
        try:
            cursor.execute(f'DROP TABLE {qualified_log_table}')
            conn.commit()
            print_info("已删除旧的变更日志表")
        except:
            pass
        
        create_sql = f"""
        CREATE TABLE {qualified_log_table} (
            "ID" INT IDENTITY(1,1) PRIMARY KEY,
            "TABLE_NAME" VARCHAR(100) NOT NULL,
            "OPERATION" VARCHAR(10) NOT NULL,
            "PK_VALUE" VARCHAR(500),
            "OLD_DATA" VARCHAR(4000),
            "NEW_DATA" VARCHAR(4000),
            "CHANGE_TIME" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            "PROCESSED" INT DEFAULT 0
        )
        """
        
        cursor.execute(create_sql)
        conn.commit()
        cursor.close()
        conn.close()
        
        print_success("变更日志表创建成功")
        return True
    except Exception as e:
        print_error(f"创建变更日志表失败：{e}")
        return False

def create_trigger_for_table(host, port, user, password, database, table_name, primary_key, columns):
    """为表创建 CDC 触发器"""
    print(f"\n{Colors.BLUE}为表 '{table_name}' 创建 CDC 触发器...{Colors.NC}")
    
    try:
        conn_str = f"DRIVER={{DM8 ODBC DRIVER}};SERVER={host};PORT={port};UID={user};PWD={password};DATABASE={database}"
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        column_names = ', '.join([col['source'] for col in columns])
        qualified_table = f'"{database}"."{table_name}"'
        qualified_log_table = f'"{database}"."DAMENG_CDC_CHANGE_LOG"'
        
        # 构建管道分隔的值列表
        def build_pipe_list(prefix):
            parts = []
            for col in columns:
                col_name = col["source"]
                parts.append(f'COALESCE(CAST({prefix}."{col_name}" AS VARCHAR(4000)), \'NULL\')')
            return ' || \'|\' || '.join(parts)
        
        insert_values = build_pipe_list(':NEW')
        update_new_values = build_pipe_list(':NEW')
        update_old_values = build_pipe_list(':OLD')
        
        # 先尝试删除可能存在的旧触发器
        try:
            cursor.execute(f'DROP TRIGGER IF EXISTS "TR_{table_name}_CDC_INSERT"')
            cursor.execute(f'DROP TRIGGER IF EXISTS "TR_{table_name}_CDC_UPDATE"')
            cursor.execute(f'DROP TRIGGER IF EXISTS "TR_{table_name}_CDC_DELETE"')
            conn.commit()
        except:
            pass  # 如果触发器不存在，忽略错误
        
        insert_trigger = f"""
        CREATE OR REPLACE TRIGGER "TR_{table_name}_CDC_INSERT"
        AFTER INSERT ON {qualified_table}
        FOR EACH ROW
        BEGIN
            INSERT INTO {qualified_log_table} ("TABLE_NAME", "OPERATION", "PK_VALUE", "OLD_DATA", "NEW_DATA")
            VALUES ('{table_name}', 'INSERT', :NEW."{primary_key}", NULL, {insert_values});
        END;
        """
        
        update_trigger = f"""
        CREATE OR REPLACE TRIGGER "TR_{table_name}_CDC_UPDATE"
        AFTER UPDATE ON {qualified_table}
        FOR EACH ROW
        BEGIN
            INSERT INTO {qualified_log_table} ("TABLE_NAME", "OPERATION", "PK_VALUE", "OLD_DATA", "NEW_DATA")
            VALUES ('{table_name}', 'UPDATE', :NEW."{primary_key}", {update_old_values}, {update_new_values});
        END;
        """
        
        delete_trigger = f"""
        CREATE OR REPLACE TRIGGER "TR_{table_name}_CDC_DELETE"
        AFTER DELETE ON {qualified_table}
        FOR EACH ROW
        BEGIN
            INSERT INTO {qualified_log_table} ("TABLE_NAME", "OPERATION", "PK_VALUE", "OLD_DATA", "NEW_DATA")
            VALUES ('{table_name}', 'DELETE', :OLD."{primary_key}", {update_old_values}, NULL);
        END;
        """
        
        for trigger_sql in [insert_trigger, update_trigger, delete_trigger]:
            cursor.execute(trigger_sql)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print_success(f"表 '{table_name}' 的 CDC 触发器创建成功")
        return True
    except Exception as e:
        print_error(f"创建触发器失败：{e}")
        return False

def save_cdc_config(cdc_config):
    """保存 CDC 配置"""
    config_path = Path("cdc_config.json")
    import json
    
    existing = []
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            existing = json.load(f)
    
    existing.append(cdc_config)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    
    print_success("CDC 配置已保存")

def load_cdc_configs():
    """加载 CDC 配置"""
    config_path = Path("cdc_config.json")
    import json
    
    if not config_path.exists():
        return []
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def start_cdc_monitor():
    """启动 CDC 监控服务"""
    print_header("启动 CDC 监控服务")
    
    configs = load_cdc_configs()
    if not configs:
        print_error("没有配置 CDC 监控任务，请先配置")
        return
    
    print(f"\n{Colors.GREEN}已配置的 CDC 监控任务：{Colors.NC}\n")
    for i, cfg in enumerate(configs, 1):
        status = cfg.get('status', 'stopped')
        status_color = Colors.GREEN if status == 'running' else Colors.YELLOW
        print(f"  {i}) {cfg['source']['database']}.{cfg['monitored_table']['table_name']} -> {cfg['target']['database']}.{cfg['target']['table']} [{status_color}{status}{Colors.NC}]")
    
    task_choice = get_input(f"\n请选择要启动的任务 [1-{len(configs)}]： ", default="1")
    
    if task_choice.isdigit():
        idx = int(task_choice) - 1
        if 0 <= idx < len(configs):
            cdc_config = configs[idx]
        else:
            print_error("无效的选择")
            return
    else:
        print_error("无效的选择")
        return
    
    source_config = cdc_config['source']
    monitored_table = cdc_config['monitored_table']
    
    if not create_change_log_table(
        source_config['host'],
        source_config['port'],
        source_config['user'],
        source_config['password'],
        source_config['database']
    ):
        return
    
    if not create_trigger_for_table(
        source_config['host'],
        source_config['port'],
        source_config['user'],
        source_config['password'],
        source_config['database'],
        monitored_table['table_name'],
        monitored_table['primary_key'],
        monitored_table['columns']
    ):
        return
    
    print_success("CDC 监控已启动，正在监控变更...")
    print(f"\n{Colors.YELLOW}按 Ctrl+C 停止监控{Colors.NC}")
    
    try:
        monitor_loop(cdc_config)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}监控已停止{Colors.NC}")

def monitor_loop(cdc_config):
    """监控循环"""
    import time
    import json
    
    source = cdc_config['source']
    target = cdc_config['target']
    monitored_table = cdc_config['monitored_table']
    polling_interval = cdc_config['polling_interval']
    
    last_processed_id = 0
    
    source_conn_str = f"DRIVER={{DM8 ODBC DRIVER}};SERVER={source['host']};PORT={source['port']};UID={source['user']};PWD={source['password']};DATABASE={source['database']}"
    
    qualified_log_table = f'"{source["database"]}"."DAMENG_CDC_CHANGE_LOG"'
    
    while True:
        try:
            source_conn = pyodbc.connect(source_conn_str)
            source_cursor = source_conn.cursor()
            
            source_cursor.execute(f"""
                SELECT "ID", "TABLE_NAME", "OPERATION", "PK_VALUE", "OLD_DATA", "NEW_DATA", "CHANGE_TIME"
                FROM {qualified_log_table}
                WHERE "PROCESSED" = 0 AND "ID" > ?
                ORDER BY "ID"
            """, (last_processed_id,))
            
            changes = source_cursor.fetchall()
            
            if changes:
                print(f"\n{Colors.BLUE}检测到 {len(changes)} 个变更{Colors.NC}")
                
                for change in changes:
                    change_id, table_name, operation, pk_value, old_data, new_data, change_time = change
                    
                    try:
                        if cdc_config['target_type'] == 'mysql':
                            apply_change_to_mysql(target, monitored_table, operation, pk_value, old_data, new_data)
                        else:
                            apply_change_to_dameng(target, monitored_table, operation, pk_value, old_data, new_data)
                        
                        source_cursor.execute(f'UPDATE {qualified_log_table} SET "PROCESSED" = 1 WHERE "ID" = ?', (change_id,))
                        source_conn.commit()
                        
                        print(f"  {Colors.GREEN}✓{Colors.NC} {operation}: PK={pk_value}")
                    except Exception as e:
                        print(f"  {Colors.RED}✗{Colors.NC} {operation}: PK={pk_value} - {e}")
                    
                    last_processed_id = change_id
            
            source_cursor.close()
            source_conn.close()
            
            time.sleep(polling_interval)
            
        except Exception as e:
            print_error(f"监控错误：{e}")
            time.sleep(polling_interval)

def apply_change_to_mysql(target_config, monitored_table, operation, pk_value, old_data, new_data):
    """应用变更到 MySQL 数据库"""
    try:
        conn = mysql.connector.connect(
            host=target_config['host'],
            port=int(target_config['port']),
            user=target_config['user'],
            password=target_config['password'],
            database=target_config['database']
        )
        cursor = conn.cursor()
        
        table_name = monitored_table['table_name']
        columns = monitored_table['columns']
        column_names = [col['source'] for col in columns]
        
        if operation == 'INSERT':
            placeholders = ', '.join(['%s' for _ in column_names])
            insert_sql = f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({placeholders})"
            cursor.execute(insert_sql, [pk_value] + [None] * (len(column_names) - 1))
        
        elif operation == 'UPDATE':
            set_clause = ', '.join([f"{col} = %s" for col in column_names])
            update_sql = f"UPDATE {table_name} SET {set_clause} WHERE {monitored_table['primary_key']} = %s"
            cursor.execute(update_sql, [pk_value] * (len(column_names) + 1))
        
        elif operation == 'DELETE':
            delete_sql = f"DELETE FROM {table_name} WHERE {monitored_table['primary_key']} = %s"
            cursor.execute(delete_sql, (pk_value,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception as e:
        raise Exception(f"MySQL 应用变更失败：{e}")

def apply_change_to_dameng(target_config, monitored_table, operation, pk_value, old_data, new_data):
    """应用变更到达梦数据库"""
    try:
        conn_str = f"DRIVER={{DM8 ODBC DRIVER}};SERVER={target_config['host']};PORT={target_config['port']};UID={target_config['user']};PWD={target_config['password']};DATABASE={target_config['database']}"
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        table_name = target_config['table']
        columns = monitored_table['columns']
        column_names = [col['source'] for col in columns]
        qualified_target_table = f'"{target_config["database"]}"."{table_name}"'
        
        # 解析管道分隔的值
        def parse_pipe_data(data):
            if not data:
                return [None] * len(column_names)
            parts = data.split('|')
            # 把 'NULL' 转为 None
            return [None if p == 'NULL' else p for p in parts]
        
        if operation == 'INSERT':
            values = parse_pipe_data(new_data)
            columns_str = ', '.join([f'"{col}"' for col in column_names])
            placeholders = ', '.join(['?' for _ in column_names])
            insert_sql = f'INSERT INTO {qualified_target_table} ({columns_str}) VALUES ({placeholders})'
            cursor.execute(insert_sql, values)
        
        elif operation == 'UPDATE':
            values = parse_pipe_data(new_data)
            values.append(pk_value)
            set_clause = ', '.join([f'"{col}" = ?' for col in column_names])
            update_sql = f'UPDATE {qualified_target_table} SET {set_clause} WHERE "{monitored_table["primary_key"]}" = ?'
            cursor.execute(update_sql, values)
        
        elif operation == 'DELETE':
            delete_sql = f'DELETE FROM {qualified_target_table} WHERE "{monitored_table["primary_key"]}" = ?'
            cursor.execute(delete_sql, (pk_value,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception as e:
        raise Exception(f"达梦应用变更失败：{e}")

def stop_cdc_monitor():
    """停止 CDC 监控服务"""
    print_header("停止 CDC 监控服务")
    print_success("CDC 监控服务已停止")

def view_cdc_status():
    """查看 CDC 监控状态"""
    print_header("CDC 监控状态")
    
    configs = load_cdc_configs()
    if not configs:
        print_info("没有配置 CDC 监控任务")
        return
    
    print(f"\n{Colors.GREEN}已配置的 CDC 监控任务：{Colors.NC}\n")
    
    for i, cfg in enumerate(configs, 1):
        status = cfg.get('status', 'stopped')
        status_color = Colors.GREEN if status == 'running' else Colors.YELLOW
        
        print(f"任务 {i}:")
        print(f"  源数据库: {cfg['source']['database']}")
        print(f"  监控表: {cfg['monitored_table']['table_name']}")
        print(f"  目标数据库: {cfg['target']['database']}")
        print(f"  目标表: {cfg['target']['table']}")
        print(f"  轮询间隔: {cfg['polling_interval']} 秒")
        print(f"  状态: {status_color}{status}{Colors.NC}")
        print()

def delete_cdc_config(index):
    """删除 CDC 配置"""
    config_path = Path("cdc_config.json")
    import json
    
    configs = load_cdc_configs()
    if 0 <= index < len(configs):
        deleted_config = configs.pop(index)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(configs, f, indent=2, ensure_ascii=False)
        return deleted_config
    return None

def delete_cdc_task():
    """删除 CDC 监控任务"""
    print_header("删除 CDC 监控任务")
    
    configs = load_cdc_configs()
    if not configs:
        print_info("没有配置 CDC 监控任务")
        return
    
    print(f"\n{Colors.RED}已配置的 CDC 监控任务：{Colors.NC}\n")
    
    for i, cfg in enumerate(configs, 1):
        status = cfg.get('status', 'stopped')
        status_color = Colors.GREEN if status == 'running' else Colors.YELLOW
        print(f"  {i}) {cfg['source']['database']}.{cfg['monitored_table']['table_name']} -> {cfg['target']['database']}.{cfg['target']['table']} [{status_color}{status}{Colors.NC}]")
    
    task_choice = get_input(f"\n请选择要删除的任务 [1-{len(configs)}]： ", default="")
    
    if not task_choice:
        print_error("取消删除")
        return
    
    if not task_choice.isdigit():
        print_error("无效的选择")
        return
    
    idx = int(task_choice) - 1
    if idx < 0 or idx >= len(configs):
        print_error("无效的选择")
        return
    
    deleted_config = configs[idx]
    confirm = get_input(f"确认删除任务 '{deleted_config['source']['database']}.{deleted_config['monitored_table']['table_name']} -> {deleted_config['target']['database']}.{deleted_config['target']['table']}'? (y/n) [默认：n]: ", default="n")
    
    if confirm.lower() == 'y':
        deleted = delete_cdc_config(idx)
        if deleted:
            print_success("CDC 监控任务已删除")
        else:
            print_error("删除失败")
    else:
        print_info("取消删除")

def load_sync_history():
    """加载同步历史记录"""
    history_file = Path("config") / "sync_history.json"
    if history_file.exists():
        with open(history_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_sync_history(source_db, source_table, target_db, target_table, field_mapping):
    """保存同步历史记录"""
    history = load_sync_history()
    
    # 创建唯一标识
    record_id = f"{source_db}.{source_table}->{target_db}.{target_table}"
    
    # 检查是否已存在，存在则更新
    found = False
    for record in history:
        if record['id'] == record_id:
            record['field_mapping'] = field_mapping
            record['updated_at'] = datetime.now().isoformat()
            found = True
            break
    
    if not found:
        history.append({
            'id': record_id,
            'source_db': source_db,
            'source_table': source_table,
            'target_db': target_db,
            'target_table': target_table,
            'field_mapping': field_mapping,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        })
    
    history_file = Path("config") / "sync_history.json"
    history_file.parent.mkdir(parents=True, exist_ok=True)
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def check_sync_history(source_db, source_table, target_db, target_table):
    """检查是否有同步历史记录"""
    history = load_sync_history()
    record_id = f"{source_db}.{source_table}->{target_db}.{target_table}"
    
    for record in history:
        if record['id'] == record_id:
            return record
    return None

# ==================== FastAPI 相关代码 ====================

if FASTAPI_AVAILABLE:
    
    # ==================== 数据模型 ====================
    
    class GitMonitorMode(str, Enum):
        AUTO = "auto"
        MANUAL = "manual"
    
    class TaskStatus(str, Enum):
        RUNNING = "running"
        STOPPED = "stopped"
        ERROR = "error"
    
    class GitTaskCreate(BaseModel):
        repo_url: str = Field(..., description="仓库地址 (HTTPS/SSH)")
        local_path: str = Field(..., description="本地仓库路径")
        branch: str = Field(default="main", description="分支名")
        mode: GitMonitorMode = Field(default=GitMonitorMode.MANUAL, description="监控模式")
        polling_interval: int = Field(default=60, description="轮询间隔(秒)")
    
    class GitTaskResponse(BaseModel):
        id: int
        repo_url: str
        local_path: str
        branch: str
        mode: str
        polling_interval: int
        status: str
        last_check: Optional[str] = None
        last_update: Optional[str] = None
        has_updates: bool = False
        pending_pull: bool = False
        last_pull: Optional[str] = None
    
    class ApiSyncTaskCreate(BaseModel):
        api_url: str = Field(..., description="API 地址")
        api_method: str = Field(default="GET", description="HTTP 方法")
        json_path: str = Field(default="results", description="JSON 数据路径")
        target_db_type: str = Field(default="mysql", description="目标数据库类型")
        target_host: str = Field(..., description="目标主机")
        target_port: int = Field(..., description="目标端口")
        target_user: str = Field(..., description="目标用户名")
        target_password: str = Field(..., description="目标密码")
        target_database: str = Field(..., description="目标数据库")
        target_table: str = Field(..., description="目标表名")
        polling_interval: int = Field(default=60, description="轮询间隔(秒)")
    
    class ApiSyncTaskResponse(BaseModel):
        id: int
        api_url: str
        api_method: str
        json_path: str
        target_host: str
        target_port: int
        target_database: str
        target_table: str
        polling_interval: int
        status: str
        last_sync: Optional[str] = None
        records_synced: int = 0
    
    class DbSyncTaskCreate(BaseModel):
        source_type: str = Field(..., description="源数据库类型")
        source_host: str = Field(..., description="源主机")
        source_port: int = Field(..., description="源端口")
        source_user: str = Field(..., description="源用户名")
        source_password: str = Field(..., description="源密码")
        source_database: str = Field(..., description="源数据库")
        source_table: str = Field(..., description="源表名")
        target_type: str = Field(..., description="目标数据库类型")
        target_host: str = Field(..., description="目标主机")
        target_port: int = Field(..., description="目标端口")
        target_user: str = Field(..., description="目标用户名")
        target_password: str = Field(..., description="目标密码")
        target_database: str = Field(..., description="目标数据库")
        target_table: str = Field(..., description="目标表名")
        mode: str = Field(default="batch", description="同步模式")
        field_mapping: Optional[List[Dict[str, str]]] = Field(default=None, description="字段映射")
    
    class DbSyncTaskResponse(BaseModel):
        id: int
        source_type: str
        source_host: str
        source_port: int
        source_user: str
        source_password: str
        source_database: str
        source_table: str
        target_type: str
        target_host: str
        target_port: int
        target_user: str
        target_password: str
        target_database: str
        target_table: str
        mode: str
        field_mapping: Optional[List[Dict[str, str]]] = None
        status: str
        last_sync: Optional[str] = None
        records_synced: int = 0
        sync_status: Optional[str] = None
    
    class PullRequest(BaseModel):
        message: Optional[str] = None
    
    # ==================== 任务存储 ====================
    
    git_tasks: Dict[int, Dict[str, Any]] = {}
    api_sync_tasks: Dict[int, Dict[str, Any]] = {}
    db_sync_tasks: Dict[int, Dict[str, Any]] = {}
    next_git_task_id = 1
    next_api_task_id = 1
    next_db_sync_task_id = 1
    running_monitors: Dict[str, threading.Thread] = {}
    running_monitors_lock = threading.Lock()
    
    # ==================== FastAPI 应用 ====================
    
    app = FastAPI(
        title="数据同步与Git仓库管理 API",
        description="提供 Git 仓库监控和数据同步的 RESTful API 接口",
        version="1.0.0"
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # ==================== 辅助函数 ====================
    
    def run_git_command_fastapi(cmd, cwd):
        """执行 Git 命令"""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return -1, "", str(e)
    
    def get_git_repo_info(local_path: str) -> Dict[str, Any]:
        """获取 Git 仓库信息"""
        returncode, branch, _ = run_git_command_fastapi(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=local_path
        )
        if returncode != 0:
            return {"error": "无法获取分支信息"}
        
        returncode, commit, _ = run_git_command_fastapi(
            ["git", "rev-parse", "HEAD"],
            cwd=local_path
        )
        if returncode != 0:
            return {"error": "无法获取提交信息"}
        
        returncode, remote_commit, _ = run_git_command_fastapi(
            ["git", "fetch", "origin"],
            cwd=local_path
        )
        
        current_branch = branch.strip()
        returncode, remote_commit, _ = run_git_command_fastapi(
            ["git", "rev-parse", f"origin/{current_branch}"],
            cwd=local_path
        )
        
        return {
            "branch": current_branch,
            "local_commit": commit.strip()[:7] if returncode == 0 else "unknown",
            "remote_commit": remote_commit.strip()[:7] if returncode == 0 else "unknown",
            "has_updates": returncode == 0 and commit.strip() != remote_commit.strip()
        }
    
    def git_monitor_thread(task_id: int):
        """Git 监控后台线程"""
        task = git_tasks.get(task_id)
        if not task:
            return
        
        local_path = task['local_path']
        mode = task.get('mode', 'manual')
        polling_interval = task.get('polling_interval', 60)
        
        while True:
            with running_monitors_lock:
                if f"git_{task_id}" not in running_monitors:
                    break
            
            try:
                info = get_git_repo_info(local_path)
                if "error" not in info:
                    task['last_check'] = datetime.now().isoformat()
                    if info['has_updates']:
                        task['last_update'] = datetime.now().isoformat()
                        
                        if mode == 'auto':
                            # 自动模式：直接拉取，不保留更新提示
                            returncode, stdout, stderr = run_git_command_fastapi(
                                ["git", "pull", "origin"],
                                cwd=local_path
                            )
                            if returncode == 0:
                                task['last_pull'] = datetime.now().isoformat()
                                task['pull_status'] = 'success'
                                task['has_updates'] = False
                                task['pending_pull'] = False
                            else:
                                task['pull_status'] = f'failed: {stderr[:50]}'
                                task['has_updates'] = False
                                task['pending_pull'] = False
                        else:
                            # 手动模式：设置更新提示，等待用户确认
                            task['has_updates'] = True
                            task['pending_pull'] = True
                    else:
                        # 没有更新时清除所有提示
                        task['has_updates'] = False
                        task['pending_pull'] = False
            except Exception as e:
                task['error'] = str(e)
            
            time.sleep(polling_interval)
    
    def api_sync_thread(task_id: int):
        """API 同步后台线程"""
        task = api_sync_tasks.get(task_id)
        if not task:
            return
        
        polling_interval = task.get('polling_interval', 60)
        
        while True:
            with running_monitors_lock:
                if f"api_{task_id}" not in running_monitors:
                    break
            
            try:
                import requests
                response = requests.request(
                    method=task['api_method'],
                    url=task['api_url'],
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if task['json_path']:
                        keys = task['json_path'].split('.')
                        for key in keys:
                            if key in data:
                                data = data[key]
                    
                    if isinstance(data, list) and len(data) > 0:
                        # 获取数据并同步到数据库
                        sync_to_database(task, data)
                        task['records_synced'] = len(data)
                        task['last_sync'] = datetime.now().isoformat()
                        task['sync_status'] = 'success'
                        task['last_record_count'] = len(data)
                    elif isinstance(data, dict):
                        # 单个对象也支持，包装成数组
                        sync_to_database(task, [data])
                        task['records_synced'] = 1
                        task['last_sync'] = datetime.now().isoformat()
                        task['sync_status'] = 'success'
                        task['last_record_count'] = 1
                    else:
                        task['sync_status'] = 'data_not_array'
                else:
                    task['sync_status'] = f'http_error_{response.status_code}'
                    
            except Exception as e:
                task['sync_status'] = f'error: {str(e)[:50]}'
            
            time.sleep(polling_interval)
    
    def sync_to_database(task, data):
        """将数据同步到目标数据库"""
        db_type = task.get('target_db_type', 'mysql')
        host = task['target_host']
        port = int(task['target_port'])
        user = task['target_user']
        password = task['target_password']
        database = task['target_database']
        table = task['target_table']
        
        try:
            if db_type == 'mysql':
                import pymysql
                connection = pymysql.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=database,
                    charset='utf8mb4'
                )
                
                with connection.cursor() as cursor:
                    # 检查表是否存在
                    cursor.execute(f"SHOW TABLES LIKE '{table}'")
                    table_exists = cursor.fetchone()
                    
                    if not table_exists:
                        # 自动创建表
                        create_table_from_data(cursor, table, data)
                        task['table_created'] = True
                    
                    # 插入数据
                    insert_data(cursor, table, data)
                    connection.commit()
                
                connection.close()
        except Exception as e:
            task['sync_status'] = f'db_error: {str(e)[:50]}'
    
    def create_table_from_data(cursor, table_name, data):
        """根据数据自动创建表"""
        if not data or not isinstance(data, list) or len(data) == 0:
            return
        
        sample = data[0]
        columns = []
        
        for key, value in sample.items():
            sql_type = get_sql_type(value)
            columns.append(f"`{key}` {sql_type}")
        
        create_sql = f"CREATE TABLE IF NOT EXISTS `{table_name}` ({', '.join(columns)}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
        cursor.execute(create_sql)
    
    def get_sql_type(value):
        """根据值推断 SQL 类型"""
        if isinstance(value, int):
            return 'INT'
        elif isinstance(value, float):
            return 'DECIMAL(10,2)'
        elif isinstance(value, bool):
            return 'TINYINT(1)'
        elif isinstance(value, dict) or isinstance(value, list):
            return 'TEXT'
        else:
            # 字符串类型，根据长度选择
            str_value = str(value)
            if len(str_value) <= 255:
                return 'VARCHAR(255)'
            elif len(str_value) <= 65535:
                return 'TEXT'
            else:
                return 'LONGTEXT'
    
    def insert_data(cursor, table_name, data):
        """批量插入数据"""
        if not data or not isinstance(data, list) or len(data) == 0:
            return
        
        sample = data[0]
        columns = [f"`{k}`" for k in sample.keys()]
        placeholders = [f"%({k})s" for k in sample.keys()]
        
        insert_sql = f"INSERT INTO `{table_name}` ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
        
        for row in data:
            try:
                cursor.execute(insert_sql, row)
            except Exception:
                pass  # 跳过插入失败的行

    def execute_mysql_sync(source_config, target_config, field_mapping=None, mode='batch'):
        """执行 MySQL 数据库同步"""
        try:
            import pymysql
            
            # 连接源数据库
            source_conn = pymysql.connect(
                host=source_config['host'],
                port=int(source_config['port']),
                user=source_config['user'],
                password=source_config['password'],
                database=source_config['database'],
                charset='utf8mb4'
            )
            
            # 连接目标数据库
            target_conn = pymysql.connect(
                host=target_config['host'],
                port=int(target_config['port']),
                user=target_config['user'],
                password=target_config['password'],
                database=target_config['database'],
                charset='utf8mb4'
            )
            
            source_cursor = source_conn.cursor()
            target_cursor = target_conn.cursor()
            
            # 获取源表字段
            source_cursor.execute(f"SELECT * FROM `{source_config['table']}` LIMIT 0")
            source_columns = [col[0] for col in source_cursor.description]
            
            # 获取目标表字段（如果存在）
            target_cursor.execute(f"SHOW TABLES LIKE '{target_config['table']}'")
            table_exists = target_cursor.fetchone()
            
            if not table_exists:
                # 如果目标表不存在，根据源表结构创建
                source_cursor.execute(f"DESCRIBE `{source_config['table']}`")
                create_cols = []
                for row in source_cursor.fetchall():
                    col_name = row[0]
                    col_type = row[1]
                    create_cols.append(f"`{col_name}` {col_type}")
                
                create_sql = f"CREATE TABLE `{target_config['table']}` ({', '.join(create_cols)}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
                target_cursor.execute(create_sql)
                target_conn.commit()
            
            # 获取目标表字段
            target_cursor.execute(f"SELECT * FROM `{target_config['table']}` LIMIT 0")
            target_columns = [col[0] for col in target_cursor.description]
            
            # 处理字段映射
            if field_mapping:
                mapped_source_cols = [m['source'] for m in field_mapping]
                mapped_target_cols = [m['target'] for m in field_mapping]
                common_source = [col for col in mapped_source_cols if col in source_columns]
                common_target = [mapped_target_cols[mapped_source_cols.index(col)] for col in common_source]
            else:
                common_source = [col for col in source_columns if col in target_columns]
                common_target = common_source
            
            if not common_source:
                return False
            
            # 执行同步
            source_cursor.execute(f"SELECT {', '.join([f'`{col}`' for col in common_source])} FROM `{source_config['table']}`")
            
            insert_count = 0
            update_count = 0
            
            for row in source_cursor.fetchall():
                row_dict = dict(zip(common_source, row))
                
                # 使用第一个字段作为主键进行更新判断
                pk_col = common_target[0]
                pk_val = row[0]
                
                target_cursor.execute(f"SELECT COUNT(*) FROM `{target_config['table']}` WHERE `{pk_col}` = %s", (pk_val,))
                exists = target_cursor.fetchone()[0]
                
                if exists:
                    set_clause = ", ".join([f"`{tgt}` = %s" for tgt in common_target])
                    update_sql = f"UPDATE `{target_config['table']}` SET {set_clause} WHERE `{pk_col}` = %s"
                    params = list(row) + [pk_val]
                    target_cursor.execute(update_sql, params)
                    update_count += 1
                else:
                    placeholders = ", ".join(["%s" for _ in common_target])
                    insert_sql = f"INSERT INTO `{target_config['table']}` ({', '.join([f'`{col}`' for col in common_target])}) VALUES ({placeholders})"
                    target_cursor.execute(insert_sql, row)
                    insert_count += 1
            
            target_conn.commit()
            
            source_cursor.close()
            target_cursor.close()
            source_conn.close()
            target_conn.close()
            
            return True
            
        except Exception as e:
            print_error(f"MySQL同步失败：{e}")
            return False

    def db_sync_thread(task_id: int):
        """数据库同步后台线程"""
        task = db_sync_tasks.get(task_id)
        if not task:
            return
        
        while True:
            with running_monitors_lock:
                if f"db_sync_{task_id}" not in running_monitors:
                    break
            
            try:
                # 构建源和目标配置
                source_config = {
                    'host': task['source_host'],
                    'port': task['source_port'],
                    'user': task['source_user'],
                    'password': task['source_password'],
                    'database': task['source_database'],
                    'table': task['source_table']
                }
                
                target_config = {
                    'host': task['target_host'],
                    'port': task['target_port'],
                    'user': task['target_user'],
                    'password': task['target_password'],
                    'database': task['target_database'],
                    'table': task['target_table']
                }
                
                # 执行同步
                if task['source_type'] == 'dameng' and task['target_type'] == 'dameng':
                    success = sync_dameng_data(source_config, target_config, task.get('field_mapping'))
                elif task['source_type'] == 'mysql' and task['target_type'] == 'mysql':
                    success = execute_mysql_sync(source_config, target_config, task.get('field_mapping'), task.get('mode', 'batch'))
                else:
                    # MySQL 与达梦之间的同步
                    success = execute_mysql_sync(source_config, target_config, task.get('field_mapping'), task.get('mode', 'batch'))
                
                if success:
                    task['last_sync'] = datetime.now().isoformat()
                    task['sync_status'] = 'success'
                else:
                    task['sync_status'] = 'failed'
            
            except Exception as e:
                task['sync_status'] = f'error: {str(e)[:50]}'
            
            time.sleep(60)  # 每分钟同步一次

    # ==================== 数据库信息 API ====================
    
    @app.get("/api/databases", tags=["数据库信息"])
    async def get_databases(db_type: str = "mysql", host: str = "localhost", port: int = 3306, 
                            user: str = "root", password: str = ""):
        """获取可用数据库列表"""
        try:
            if db_type == 'mysql':
                import pymysql
                connection = pymysql.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password
                )
                
                with connection.cursor() as cursor:
                    cursor.execute("SHOW DATABASES")
                    databases = [row[0] for row in cursor.fetchall()]
                
                connection.close()
                return {"databases": databases, "success": True}
            elif db_type == 'dameng':
                try:
                    conn_str = f"DRIVER={{DM8 ODBC DRIVER}};SERVER={host};PORT={port};UID={user};PWD={password}"
                    conn = pyodbc.connect(conn_str)
                    cursor = conn.cursor()
                    cursor.execute("SELECT DISTINCT OWNER FROM ALL_TABLES ORDER BY OWNER")
                    databases = [row[0] for row in cursor.fetchall()]
                    cursor.close()
                    conn.close()
                    return {"databases": databases, "success": True}
                except Exception as e:
                    return {"error": str(e), "success": False}
            else:
                return {"error": "Unsupported database type", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}
    
    @app.get("/api/databases/{database}/tables", tags=["数据库信息"])
    async def get_tables(database: str, db_type: str = "mysql", host: str = "localhost", 
                         port: int = 3306, user: str = "root", password: str = ""):
        """获取数据库中的表列表"""
        try:
            if db_type == 'mysql':
                import pymysql
                connection = pymysql.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=database
                )
                
                with connection.cursor() as cursor:
                    cursor.execute("SHOW TABLES")
                    tables = [row[0] for row in cursor.fetchall()]
                
                connection.close()
                return {"database": database, "tables": tables, "success": True}
            elif db_type == 'dameng':
                try:
                    conn_str = f"DRIVER={{DM8 ODBC DRIVER}};SERVER={host};PORT={port};UID={user};PWD={password};DATABASE={database}"
                    conn = pyodbc.connect(conn_str)
                    cursor = conn.cursor()
                    cursor.execute(f"SELECT TABLE_NAME FROM ALL_TABLES WHERE OWNER = '{database}' ORDER BY TABLE_NAME")
                    tables = [row[0] for row in cursor.fetchall()]
                    cursor.close()
                    conn.close()
                    return {"database": database, "tables": tables, "success": True}
                except Exception as e:
                    return {"error": str(e), "success": False}
            else:
                return {"error": "Unsupported database type", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}
    
    @app.get("/api/databases/{database}/tables/{table}/schema", tags=["数据库信息"])
    async def get_table_schema(database: str, table: str, db_type: str = "mysql", 
                              host: str = "localhost", port: int = 3306, 
                              user: str = "root", password: str = ""):
        """获取表的结构信息"""
        try:
            if db_type == 'mysql':
                import pymysql
                connection = pymysql.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=database
                )
                
                with connection.cursor() as cursor:
                    cursor.execute(f"DESCRIBE `{table}`")
                    schema = []
                    for row in cursor.fetchall():
                        schema.append({
                            "field": row[0],
                            "type": row[1],
                            "null": row[2],
                            "key": row[3],
                            "default": row[4],
                            "extra": row[5]
                        })
                
                connection.close()
                return {"database": database, "table": table, "schema": schema, "success": True}
            else:
                return {"error": "Unsupported database type", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}

    @app.get("/api/databases/{database}/tables/{table}/fields", tags=["数据库信息"])
    async def get_table_fields(database: str, table: str, db_type: str = "mysql", 
                              host: str = "localhost", port: int = 3306, 
                              user: str = "root", password: str = ""):
        """获取表的字段信息（用于字段映射）"""
        try:
            if db_type == 'mysql':
                import pymysql
                connection = pymysql.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=database
                )
                
                with connection.cursor() as cursor:
                    cursor.execute(f"DESCRIBE `{table}`")
                    fields = []
                    for row in cursor.fetchall():
                        field_name = row[0]
                        field_type = row[1]
                        # 映射类型
                        if 'int' in str(field_type).lower():
                            mapped_type = 'INT'
                        elif 'datetime' in str(field_type).lower() or 'date' in str(field_type).lower():
                            mapped_type = 'DATETIME'
                        elif 'bool' in str(field_type).lower():
                            mapped_type = 'BOOLEAN'
                        else:
                            mapped_type = 'STRING'
                        fields.append({
                            "name": field_name,
                            "type": mapped_type
                        })
                
                connection.close()
                return {"database": database, "table": table, "fields": fields, "success": True}
            elif db_type == 'dameng':
                try:
                    conn_str = f"DRIVER={{DM8 ODBC DRIVER}};SERVER={host};PORT={port};UID={user};PWD={password};DATABASE={database}"
                    conn = pyodbc.connect(conn_str)
                    cursor = conn.cursor()
                    
                    cursor.execute(f"""
                        SELECT COLUMN_NAME, DATA_TYPE 
                        FROM ALL_TAB_COLUMNS 
                        WHERE OWNER = '{database}' AND TABLE_NAME = '{table}' 
                        ORDER BY COLUMN_ID
                    """)
                    fields = []
                    for row in cursor.fetchall():
                        column_name = row[0]
                        column_type = row[1]
                        if 'INT' in str(column_type).upper():
                            mapped_type = 'INT'
                        elif 'DATE' in str(column_type).upper() or 'TIME' in str(column_type).upper():
                            mapped_type = 'DATETIME'
                        elif 'BOOL' in str(column_type).upper():
                            mapped_type = 'BOOLEAN'
                        else:
                            mapped_type = 'STRING'
                        fields.append({
                            "name": column_name,
                            "type": mapped_type
                        })
                    
                    cursor.close()
                    conn.close()
                    return {"database": database, "table": table, "fields": fields, "success": True}
                except Exception as e:
                    return {"error": str(e), "success": False}
            else:
                return {"error": "Unsupported database type", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}

    # ==================== 健康检查 ====================
    
    @app.get("/", tags=["健康检查"])
    async def root():
        """API 根路径"""
        return {
            "message": "数据同步与Git仓库管理 API",
            "version": "1.0.0",
            "docs_url": "/docs"
        }
    
    @app.get("/health", tags=["健康检查"])
    async def health_check():
        """健康检查"""
        return {"status": "healthy"}

    @app.get("/ui", tags=["前端界面"])
    async def get_frontend():
        """获取前端界面"""
        frontend_path = os.path.join(os.path.dirname(__file__), "frontend", "index.html")
        return FileResponse(frontend_path)

    @app.get("/ui/{path:path}", tags=["前端界面"])
    async def get_frontend_assets(path: str):
        """获取前端资源文件"""
        frontend_path = os.path.join(os.path.dirname(__file__), "frontend", path)
        if os.path.exists(frontend_path):
            return FileResponse(frontend_path)
        return {"error": "文件不存在"}

    # ==================== Git 监控 API ====================
    
    @app.post("/api/git/tasks", response_model=GitTaskResponse, tags=["Git 监控"])
    async def create_git_task(task: GitTaskCreate):
        """创建 Git 监控任务"""
        global next_git_task_id
        
        if not os.path.exists(task.local_path):
            raise HTTPException(status_code=400, detail=f"本地路径不存在: {task.local_path}")
        
        # 检查是否是有效的 Git 仓库
        git_dir = os.path.join(task.local_path, '.git')
        if not os.path.exists(git_dir):
            # 如果不是 Git 仓库，尝试初始化
            returncode, stdout, stderr = run_git_command_fastapi(
                ["git", "init"],
                cwd=task.local_path
            )
            if returncode != 0:
                raise HTTPException(status_code=400, detail=f"无法初始化 Git 仓库: {stderr}")
            
            # 配置远程仓库
            returncode, stdout, stderr = run_git_command_fastapi(
                ["git", "remote", "add", "origin", task.repo_url],
                cwd=task.local_path
            )
            if returncode != 0:
                raise HTTPException(status_code=400, detail=f"无法配置远程仓库: {stderr}")
            
            # 设置 pull 默认分支
            returncode, stdout, stderr = run_git_command_fastapi(
                ["git", "branch", "--set-upstream-to", f"origin/{task.branch}", task.branch],
                cwd=task.local_path
            )
            # 如果分支不存在，先创建
            if returncode != 0:
                returncode, stdout, stderr = run_git_command_fastapi(
                    ["git", "checkout", "-b", task.branch],
                    cwd=task.local_path
                )
                if returncode != 0:
                    raise HTTPException(status_code=400, detail=f"无法创建分支: {stderr}")
                
                # 设置上游分支
                returncode, stdout, stderr = run_git_command_fastapi(
                    ["git", "branch", "--set-upstream-to", f"origin/{task.branch}"],
                    cwd=task.local_path
                )
                if returncode != 0:
                    # 忽略上游设置失败，后续 pull 时可能需要指定分支
                    pass
        
        task_dict = task.model_dump()
        task_dict['status'] = 'stopped'
        task_dict['has_updates'] = False
        task_dict['pending_pull'] = False
        
        with running_monitors_lock:
            git_tasks[next_git_task_id] = task_dict
        
        response = GitTaskResponse(
            id=next_git_task_id,
            **task_dict
        )
        next_git_task_id += 1
        return response
    
    @app.get("/api/git/tasks", response_model=List[GitTaskResponse], tags=["Git 监控"])
    async def list_git_tasks():
        """获取所有 Git 监控任务"""
        for tid, task in git_tasks.items():
            if task.get('status') == 'running':
                local_path = task['local_path']
                mode = task.get('mode', 'manual')
                branch = task.get('branch', 'main')
                
                if os.path.exists(local_path):
                    repo_info = get_git_repo_info(local_path)
                    if 'error' not in repo_info:
                        task['last_check'] = datetime.now().isoformat()
                        if repo_info.get('has_updates'):
                            if mode == 'auto':
                                # 自动模式：自动拉取（尝试多种方式）
                                returncode, stdout, stderr = run_git_command_fastapi(
                                    ["git", "pull", "origin"],
                                    cwd=local_path
                                )
                                
                                if returncode != 0:
                                    # 方式2: 指定分支拉取
                                    returncode, stdout, stderr = run_git_command_fastapi(
                                        ["git", "pull", "origin", branch],
                                        cwd=local_path
                                    )
                                
                                if returncode != 0:
                                    # 方式3: 先fetch再merge
                                    returncode_fetch, stdout_fetch, stderr_fetch = run_git_command_fastapi(
                                        ["git", "fetch", "origin"],
                                        cwd=local_path
                                    )
                                    
                                    if returncode_fetch == 0:
                                        returncode, stdout, stderr = run_git_command_fastapi(
                                            ["git", "merge", f"origin/{branch}"],
                                            cwd=local_path
                                        )
                                
                                if returncode == 0:
                                    task['last_pull'] = datetime.now().isoformat()
                                    task['pull_status'] = 'success'
                                    task['has_updates'] = False
                                    task['pending_pull'] = False
                                else:
                                    task['pull_status'] = f'failed: {stderr[:50]}'
                                    task['has_updates'] = False
                                    task['pending_pull'] = False
                            else:
                                # 手动模式：设置更新提示
                                task['has_updates'] = True
                                task['pending_pull'] = True
                                task['last_update'] = datetime.now().isoformat()
                        else:
                            # 没有更新
                            task['has_updates'] = False
                            task['pending_pull'] = False
        
        return [
            GitTaskResponse(id=tid, **task) 
            for tid, task in git_tasks.items()
        ]
    
    @app.get("/api/git/tasks/{task_id}", response_model=GitTaskResponse, tags=["Git 监控"])
    async def get_git_task(task_id: int):
        """获取指定 Git 监控任务"""
        if task_id not in git_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        return GitTaskResponse(id=task_id, **git_tasks[task_id])
    
    @app.post("/api/git/tasks/{task_id}/start", tags=["Git 监控"])
    async def start_git_task(task_id: int):
        """启动 Git 监控任务"""
        if task_id not in git_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        monitor_key = f"git_{task_id}"
        
        with running_monitors_lock:
            if monitor_key in running_monitors:
                raise HTTPException(status_code=400, detail="任务已在运行中")
            
            git_tasks[task_id]['status'] = 'running'
            thread = threading.Thread(target=git_monitor_thread, args=(task_id,), daemon=True)
            running_monitors[monitor_key] = thread
            thread.start()
        
        return {"message": "任务已启动", "task_id": task_id}
    
    @app.post("/api/git/tasks/{task_id}/stop", tags=["Git 监控"])
    async def stop_git_task(task_id: int):
        """停止 Git 监控任务"""
        if task_id not in git_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        monitor_key = f"git_{task_id}"
        
        with running_monitors_lock:
            if monitor_key not in running_monitors:
                raise HTTPException(status_code=400, detail="任务未在运行")
            
            del running_monitors[monitor_key]
            git_tasks[task_id]['status'] = 'stopped'
        
        return {"message": "任务已停止", "task_id": task_id}
    
    @app.post("/api/git/tasks/{task_id}/pull", tags=["Git 监控"])
    async def pull_git_task(task_id: int, request: PullRequest = None):
        """手动拉取 Git 仓库"""
        if task_id not in git_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        task = git_tasks[task_id]
        local_path = task['local_path']
        branch = task.get('branch', 'main')
        
        # 尝试多种方式拉取
        # 方式1: 尝试直接拉取
        returncode, stdout, stderr = run_git_command_fastapi(
            ["git", "pull", "origin"],
            cwd=local_path
        )
        
        if returncode != 0:
            # 方式2: 指定分支拉取
            returncode, stdout, stderr = run_git_command_fastapi(
                ["git", "pull", "origin", branch],
                cwd=local_path
            )
        
        if returncode != 0:
            # 方式3: 先fetch再merge
            returncode_fetch, stdout_fetch, stderr_fetch = run_git_command_fastapi(
                ["git", "fetch", "origin"],
                cwd=local_path
            )
            
            if returncode_fetch == 0:
                returncode, stdout, stderr = run_git_command_fastapi(
                    ["git", "merge", f"origin/{branch}"],
                    cwd=local_path
                )
        
        if returncode == 0:
            task['last_pull'] = datetime.now().isoformat()
            task['has_updates'] = False
            task['pending_pull'] = False
            return {
                "message": "拉取成功", 
                "task_id": task_id,
                "output": stdout
            }
        else:
            raise HTTPException(status_code=500, detail=f"拉取失败: {stderr}")
    
    @app.delete("/api/git/tasks/{task_id}", tags=["Git 监控"])
    async def delete_git_task(task_id: int):
        """删除 Git 监控任务"""
        if task_id not in git_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        monitor_key = f"git_{task_id}"
        with running_monitors_lock:
            if monitor_key in running_monitors:
                del running_monitors[monitor_key]
        
        del git_tasks[task_id]
        return {"message": "任务已删除", "task_id": task_id}
    
    @app.get("/api/git/tasks/{task_id}/status", tags=["Git 监控"])
    async def get_git_task_status(task_id: int):
        """获取 Git 任务详细状态"""
        if task_id not in git_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        task = git_tasks[task_id]
        local_path = task['local_path']
        mode = task.get('mode', 'manual')
        
        repo_info = get_git_repo_info(local_path) if os.path.exists(local_path) else {"error": "路径不存在"}
        
        task['last_check'] = datetime.now().isoformat()
        if 'error' not in repo_info:
            if repo_info.get('has_updates'):
                if mode == 'auto':
                    # 自动模式：自动拉取
                    returncode, stdout, stderr = run_git_command_fastapi(
                        ["git", "pull", "origin"],
                        cwd=local_path
                    )
                    if returncode == 0:
                        task['last_pull'] = datetime.now().isoformat()
                        task['pull_status'] = 'success'
                        task['has_updates'] = False
                        task['pending_pull'] = False
                    else:
                        task['pull_status'] = f'failed: {stderr[:50]}'
                        task['has_updates'] = False
                        task['pending_pull'] = False
                else:
                    # 手动模式：设置更新提示
                    task['has_updates'] = True
                    task['pending_pull'] = True
                    task['last_update'] = datetime.now().isoformat()
            else:
                # 没有更新
                task['has_updates'] = False
                task['pending_pull'] = False
        
        return {
            "task_id": task_id,
            "status": task.get('status', 'stopped'),
            "mode": task.get('mode', 'manual'),
            "repo_info": repo_info,
            "last_check": task.get('last_check'),
            "last_update": task.get('last_update'),
            "last_pull": task.get('last_pull'),
            "has_updates": task.get('has_updates', False),
            "pending_pull": task.get('pending_pull', False),
            "error": task.get('error')
        }
    
    # ==================== API 数据同步 API ====================
    
    @app.post("/api/sync/tasks", response_model=ApiSyncTaskResponse, tags=["数据同步"])
    async def create_sync_task(task: ApiSyncTaskCreate):
        """创建 API 数据同步任务"""
        global next_api_task_id
        
        task_dict = task.model_dump()
        task_dict['status'] = 'stopped'
        task_dict['records_synced'] = 0
        task_dict['last_sync'] = None
        task_dict['sync_status'] = None
        
        api_sync_tasks[next_api_task_id] = task_dict
        response = ApiSyncTaskResponse(
            id=next_api_task_id,
            **task_dict
        )
        next_api_task_id += 1
        return response
    
    @app.get("/api/sync/tasks", response_model=List[ApiSyncTaskResponse], tags=["数据同步"])
    async def list_sync_tasks():
        """获取所有同步任务"""
        return [
            ApiSyncTaskResponse(id=tid, **task) 
            for tid, task in api_sync_tasks.items()
        ]
    
    @app.get("/api/sync/tasks/{task_id}", response_model=ApiSyncTaskResponse, tags=["数据同步"])
    async def get_sync_task(task_id: int):
        """获取指定同步任务"""
        if task_id not in api_sync_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        return ApiSyncTaskResponse(id=task_id, **api_sync_tasks[task_id])
    
    @app.post("/api/sync/tasks/{task_id}/start", tags=["数据同步"])
    async def start_sync_task(task_id: int):
        """启动同步任务"""
        if task_id not in api_sync_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        monitor_key = f"api_{task_id}"
        
        with running_monitors_lock:
            if monitor_key in running_monitors:
                raise HTTPException(status_code=400, detail="任务已在运行中")
            
            api_sync_tasks[task_id]['status'] = 'running'
            thread = threading.Thread(target=api_sync_thread, args=(task_id,), daemon=True)
            running_monitors[monitor_key] = thread
            thread.start()
        
        return {"message": "任务已启动", "task_id": task_id}
    
    @app.post("/api/sync/tasks/{task_id}/stop", tags=["数据同步"])
    async def stop_sync_task(task_id: int):
        """停止同步任务"""
        if task_id not in api_sync_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        monitor_key = f"api_{task_id}"
        
        with running_monitors_lock:
            if monitor_key not in running_monitors:
                raise HTTPException(status_code=400, detail="任务未在运行")
            
            del running_monitors[monitor_key]
            api_sync_tasks[task_id]['status'] = 'stopped'
        
        return {"message": "任务已停止", "task_id": task_id}
    
    @app.delete("/api/sync/tasks/{task_id}", tags=["数据同步"])
    async def delete_sync_task(task_id: int):
        """删除同步任务"""
        if task_id not in api_sync_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        monitor_key = f"api_{task_id}"
        with running_monitors_lock:
            if monitor_key in running_monitors:
                del running_monitors[monitor_key]
        
        del api_sync_tasks[task_id]
        return {"message": "任务已删除", "task_id": task_id}
    
    @app.get("/api/sync/tasks/{task_id}/status", tags=["数据同步"])
    async def get_sync_task_status(task_id: int):
        """获取同步任务详细状态"""
        if task_id not in api_sync_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        task = api_sync_tasks[task_id]
        return {
            "task_id": task_id,
            "status": task.get('status', 'stopped'),
            "records_synced": task.get('records_synced', 0),
            "last_sync": task.get('last_sync'),
            "sync_status": task.get('sync_status'),
            "last_record_count": task.get('last_record_count')
        }
    
    @app.post("/api/sync/tasks/{task_id}/sync-now", tags=["数据同步"])
    async def sync_now(task_id: int):
        """立即执行一次同步"""
        if task_id not in api_sync_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        task = api_sync_tasks[task_id]
        
        try:
            import requests
            response = requests.request(
                method=task['api_method'],
                url=task['api_url'],
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if task['json_path']:
                    keys = task['json_path'].split('.')
                    for key in keys:
                        if key in data:
                            data = data[key]
                
                if isinstance(data, list):
                    task['records_synced'] = len(data)
                    task['last_sync'] = datetime.now().isoformat()
                    return {
                        "message": "同步成功",
                        "task_id": task_id,
                        "records_count": len(data)
                    }
                else:
                    return {"message": "数据不是数组格式", "task_id": task_id}
            else:
                raise HTTPException(status_code=500, detail=f"HTTP 错误: {response.status_code}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ==================== 数据库同步 API ====================

    @app.post("/api/db-sync/tasks", response_model=DbSyncTaskResponse, tags=["数据库同步"])
    async def create_db_sync_task(task: DbSyncTaskCreate):
        """创建数据库同步任务"""
        global next_db_sync_task_id
        
        task_dict = task.model_dump()
        task_dict['status'] = 'stopped'
        task_dict['records_synced'] = 0
        task_dict['last_sync'] = None
        task_dict['sync_status'] = None
        
        db_sync_tasks[next_db_sync_task_id] = task_dict
        response = DbSyncTaskResponse(
            id=next_db_sync_task_id,
            **task_dict
        )
        next_db_sync_task_id += 1
        return response

    @app.get("/api/db-sync/tasks", response_model=List[DbSyncTaskResponse], tags=["数据库同步"])
    async def list_db_sync_tasks():
        """获取所有数据库同步任务"""
        return [
            DbSyncTaskResponse(id=tid, **task) 
            for tid, task in db_sync_tasks.items()
        ]

    @app.get("/api/db-sync/tasks/{task_id}", response_model=DbSyncTaskResponse, tags=["数据库同步"])
    async def get_db_sync_task(task_id: int):
        """获取指定数据库同步任务"""
        if task_id not in db_sync_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        return DbSyncTaskResponse(id=task_id, **db_sync_tasks[task_id])

    @app.post("/api/db-sync/tasks/{task_id}/start", tags=["数据库同步"])
    async def start_db_sync_task(task_id: int):
        """启动数据库同步任务"""
        if task_id not in db_sync_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        monitor_key = f"db_sync_{task_id}"
        
        with running_monitors_lock:
            if monitor_key in running_monitors:
                raise HTTPException(status_code=400, detail="任务已在运行中")
            
            db_sync_tasks[task_id]['status'] = 'running'
            thread = threading.Thread(target=db_sync_thread, args=(task_id,), daemon=True)
            running_monitors[monitor_key] = thread
            thread.start()
        
        return {"message": "任务已启动", "task_id": task_id}

    @app.post("/api/db-sync/tasks/{task_id}/stop", tags=["数据库同步"])
    async def stop_db_sync_task(task_id: int):
        """停止数据库同步任务"""
        if task_id not in db_sync_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        monitor_key = f"db_sync_{task_id}"
        
        with running_monitors_lock:
            if monitor_key not in running_monitors:
                raise HTTPException(status_code=400, detail="任务未在运行")
            
            del running_monitors[monitor_key]
            db_sync_tasks[task_id]['status'] = 'stopped'
        
        return {"message": "任务已停止", "task_id": task_id}

    @app.delete("/api/db-sync/tasks/{task_id}", tags=["数据库同步"])
    async def delete_db_sync_task(task_id: int):
        """删除数据库同步任务"""
        if task_id not in db_sync_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        monitor_key = f"db_sync_{task_id}"
        with running_monitors_lock:
            if monitor_key in running_monitors:
                del running_monitors[monitor_key]
        
        del db_sync_tasks[task_id]
        return {"message": "任务已删除", "task_id": task_id}

    @app.get("/api/db-sync/tasks/{task_id}/status", tags=["数据库同步"])
    async def get_db_sync_task_status(task_id: int):
        """获取数据库同步任务详细状态"""
        if task_id not in db_sync_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        task = db_sync_tasks[task_id]
        return {
            "task_id": task_id,
            "status": task.get('status', 'stopped'),
            "records_synced": task.get('records_synced', 0),
            "last_sync": task.get('last_sync'),
            "sync_status": task.get('sync_status')
        }

    @app.post("/api/db-sync/tasks/{task_id}/sync-now", tags=["数据库同步"])
    async def sync_db_now(task_id: int):
        """立即执行一次数据库同步"""
        if task_id not in db_sync_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        task = db_sync_tasks[task_id]
        
        try:
            # 构建源和目标配置
            source_config = {
                'db_type': task['source_type'],
                'host': task['source_host'],
                'port': task['source_port'],
                'user': task['source_user'],
                'password': task['source_password'],
                'database': task['source_database'],
                'table': task['source_table']
            }
            
            target_config = {
                'db_type': task['target_type'],
                'host': task['target_host'],
                'port': task['target_port'],
                'user': task['target_user'],
                'password': task['target_password'],
                'database': task['target_database'],
                'table': task['target_table']
            }
            
            # 执行同步
            if task['source_type'] == 'dameng' and task['target_type'] == 'dameng':
                success = sync_dameng_data(source_config, target_config, task.get('field_mapping'))
            else:
                # MySQL 同步逻辑（使用已有的 SeaTunnel 配置）
                success = execute_mysql_sync(source_config, target_config, task.get('field_mapping'), task.get('mode', 'batch'))
            
            if success:
                task['last_sync'] = datetime.now().isoformat()
                task['sync_status'] = 'success'
                return {"message": "同步成功", "task_id": task_id}
            else:
                task['sync_status'] = 'failed'
                raise HTTPException(status_code=500, detail="同步失败")
        except Exception as e:
            task['sync_status'] = 'failed'
            raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    try:
        # 检查是否有 --api 参数
        if "--api" in sys.argv:
            port = 8000
            # 检查是否指定了端口
            if "-p" in sys.argv:
                idx = sys.argv.index("-p")
                if idx + 1 < len(sys.argv):
                    port = int(sys.argv[idx + 1])
            print(f"启动 API 服务器 on http://0.0.0.0:{port}")
            print(f"API 文档: http://0.0.0.0:{port}/docs")
            uvicorn.run(app, host="0.0.0.0", port=port)
        else:
            main()
    except KeyboardInterrupt:
        print(f"\n\n操作被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"发生错误：{e}")
        sys.exit(1)