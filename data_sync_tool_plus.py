#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SeaTunnel 交互式配置工具（增强版）
更友好的终端交互体验
支持 MySQL->MySQL (CDC/batch)、API->MySQL、达梦数据库直接同步、Git仓库同步
成功
"""

import os
import sys
import subprocess
import getpass
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

def config_dameng_database(is_source=True):
    """配置达梦数据库连接"""
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
                        retry = get_input("是否重新输入表名？[y/N]: ", default="y").lower()
                        if retry == "y":
                            continue
                        else:
                            print_error("操作已取消")
                            sys.exit(1)
        else:
            table = get_input(f"{direction}表名： ", required=True)
        
        break

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
        "table": table
    }

def sync_dameng_data(source_config, sink_config):
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
        
        common_columns = [col for col in source_columns if col in sink_columns]
        if not common_columns:
            print_error("源表和目标表没有共同字段")
            return False
        
        insert_count = 0
        update_count = 0
        skip_count = 0
        
        print(f"\n{Colors.BLUE}正在同步数据...{Colors.NC}")
        
        for row in source_cursor.fetchall():
            row_dict = dict(zip(source_columns, row))
            
            pk_column = common_columns[0]
            pk_value = row_dict[pk_column]
            
            sink_cursor.execute(f"SELECT * FROM {sink_config['database']}.{sink_config['table']} WHERE {pk_column} = ?", (pk_value,))
            existing_row = sink_cursor.fetchone()
            
            if existing_row:
                existing_dict = dict(zip(sink_columns, existing_row))
                
                needs_update = False
                for col in common_columns:
                    if row_dict.get(col) != existing_dict.get(col):
                        needs_update = True
                        break
                
                if needs_update:
                    set_clause = ", ".join([f"{col} = ?" for col in common_columns])
                    update_sql = f"UPDATE {sink_config['database']}.{sink_config['table']} SET {set_clause} WHERE {pk_column} = ?"
                    params = [row_dict[col] for col in common_columns] + [pk_value]
                    sink_cursor.execute(update_sql, params)
                    update_count += 1
                else:
                    skip_count += 1
            else:
                columns_str = ", ".join(common_columns)
                placeholders = ", ".join(["?" for _ in common_columns])
                insert_sql = f"INSERT INTO {sink_config['database']}.{sink_config['table']} ({columns_str}) VALUES ({placeholders})"
                params = [row_dict[col] for col in common_columns]
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
        print("  5) 返回主菜单")
        
        choice = get_input("请选择 [1-5] [默认：5]: ", default="5")
        
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
            print("\n返回主菜单...")
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

        source_columns = get_table_columns(
            source_config['host'],
            source_config['port'],
            source_config['user'],
            source_config['password'],
            source_config['database'],
            source_config['table']
        )

        print_step(3, "字段映射配置")
        field_mapping = configure_field_mapping(source_columns, show_step=False)

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
        print_step(2, "配置源达梦数据库")
        source_config = config_dameng_database(is_source=True)

        print_step(3, "配置目标达梦数据库")
        sink_config = config_dameng_database(is_source=False)

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
        sync_dameng_data(source_config, sink_config)
        return
    
    primary_keys = ""
    if field_mapping:
        primary_keys = field_mapping[0]['target'] if field_mapping else ""

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
    database-name = "{source_config['database']}"
    table-name = "{source_config['table']}"
    server-id = {source_config['server_id']}
    startup.mode = "{source_config['startup_mode']}"
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
    query = "SELECT * FROM `{source_config['database']}`.`{source_config['table']}`"
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
        print("  3) 退出")
        
        choice = get_input("请选择 [1-3] [默认：3]: ", default="3")
        
        if choice == "1":
            data_sync_menu()
        elif choice == "2":
            git_menu()
        elif choice == "3":
            print("\n感谢使用！")
            break
        else:
            print_error("无效的选择")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}操作被用户中断{Colors.NC}")
        sys.exit(130)
    except Exception as e:
        print_error(f"发生错误：{e}")
        sys.exit(1)