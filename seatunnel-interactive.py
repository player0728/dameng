#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SeaTunnel 交互式配置工具 
支持 MySQL/达梦DM->MySQL/达梦DM (CDC/batch)、API->MySQL/达梦DM 数据同步
失败了
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

class Colors:
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BLUE}{'=' * 50}{Colors.NC}")
    print(f"{Colors.BLUE}  {text}{Colors.NC}")
    print(f"{Colors.BLUE}{'=' * 50}{Colors.NC}\n")

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

# ==================== MySQL 相关函数 ====================

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

# ==================== 达梦数据库相关函数 ====================

def test_dameng_connection(host, port, user, password, database):
    """测试达梦数据库连接"""
    if not mysql_connector_available:
        print(f"{Colors.YELLOW}警告：未安装 mysql-connector-python，跳过连接测试{Colors.NC}")
        return True

    print(f"\n{Colors.BLUE}正在测试达梦连接...{Colors.NC}")
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
        print(f"{Colors.GREEN}✓ 达梦数据库连接成功{Colors.NC}")
        return True
    except socket.error as e:
        print_error(f"连接失败：端口 {port} 不可达 - {e}")
        return False
    except mysql.connector.Error as e:
        print_error(f"连接失败：{e}")
        return False

def get_dameng_databases(host, port, user, password):
    """获取所有可用的达梦数据库（Schema）"""
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
        cursor.execute("SELECT DISTINCT OWNER FROM ALL_TABLES ORDER BY OWNER")
        databases = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return databases
    except mysql.connector.Error as e:
        print_error(f"获取达梦数据库列表失败：{e}")
        return None

def get_dameng_database_tables(host, port, user, password, database):
    """获取达梦数据库中的所有表"""
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
        cursor.execute(f"SELECT TABLE_NAME FROM ALL_TABLES WHERE OWNER = '{database.upper()}'")
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return tables
    except mysql.connector.Error as e:
        print_error(f"获取达梦表列表失败：{e}")
        return None

def get_dameng_table_columns(host, port, user, password, database, table):
    """获取达梦表的所有列名及类型"""
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
        cursor.execute(f"SELECT COLUMN_NAME, DATA_TYPE FROM ALL_TAB_COLUMNS WHERE OWNER = '{database.upper()}' AND TABLE_NAME = '{table.upper()}'")
        columns = []
        for row in cursor.fetchall():
            column_name = row[0]
            column_type = row[1]
            if 'INT' in str(column_type).upper():
                mapped_type = 'INT'
            elif 'DATE' in str(column_type).upper() or 'TIME' in str(column_type).upper():
                mapped_type = 'DATETIME'
            elif 'CHAR' in str(column_type).upper() or 'TEXT' in str(column_type).upper():
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
        print_error(f"获取达梦表结构失败：{e}")
        return None

# ==================== 通用函数 ====================

def configure_field_mapping(source_columns, show_step=True):
    """配置字段映射"""
    if show_step:
        print_step(4, "字段映射配置")
    
    mapped_columns = source_columns.copy() if source_columns else []
    
    while True:
        print(f"\n{Colors.BLUE}当前字段映射：{Colors.NC}")
        print(f"{Colors.GREEN}{'='*60}{Colors.NC}")
        print(f"{Colors.GREEN}{'序号'.ljust(5)}{'源字段名'.ljust(15)} {'目标字段名'.ljust(15)} {'字段类型'.ljust(10)}{Colors.NC}")
        print(f"{Colors.GREEN}{'='*60}{Colors.NC}")
        
        for i, col in enumerate(mapped_columns, 1):
            print(f"{str(i).ljust(5)} {col['source'].ljust(15)} → {col['target'].ljust(15)} → {col['type'].ljust(10)}")
        
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
    """配置 MySQL 数据库"""
    direction = "源" if is_source else "目标"
    print(f"{Colors.BLUE}--- 配置{direction} MySQL 数据库 ---{Colors.NC}\n")

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

def config_dameng_database(is_source=True):
    """配置达梦数据库"""
    direction = "源" if is_source else "目标"
    print(f"{Colors.BLUE}--- 配置{direction}达梦数据库 ---{Colors.NC}\n")

    host = get_input(f"{direction} 达梦主机地址 [默认：127.0.0.1]: ", default="127.0.0.1")
    port = get_input(f"{direction} 达梦端口 [默认：5236]: ", default="5236")
    user = get_input(f"{direction} 达梦用户名 [默认：SYSDBA]: ", default="SYSDBA")
    password = get_input(f"{direction} 达梦密码： ", required=True, hide=True)
    database = get_input(f"{direction} 数据库名： ", required=True)
    table = get_input(f"{direction} 表名： ", required=True)

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
        "table": table
    }

def main():
    print_header("SeaTunnel 数据采集配置向导")

    print_step(1, "选择数据源类型")

    print("选择数据源类型:")
    print("  1) MySQL 数据库")
    print("  2) 达梦数据库")
    print("  3) HTTP API")
    print("  4) 测试模式 (使用 FakeSource)")

    source_choice = get_input("请选择 [1-4] [默认：1]: ", default="1")

    source_config = None
    sink_config = None
    api_config = None
    source_db_type = None
    sink_db_type = None

    if source_choice == "1":
        print_success("数据源：MySQL 数据库")
        print_step(2, "配置源 MySQL 数据库")
        source_db_type = "mysql"

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

        print_step(4, "配置目标数据库")
        print("选择目标数据库类型:")
        print("  1) MySQL")
        print("  2) 达梦")
        sink_type_choice = get_input("请选择 [1-2] [默认：1]: ", default="1")
        
        if sink_type_choice == "1":
            sink_db_type = "mysql"
            sink_config = config_mysql_database(is_source=False)
        else:
            sink_db_type = "dm"
            sink_config = config_dameng_database(is_source=False)

    elif source_choice == "2":
        print_success("数据源：达梦数据库")
        print_step(2, "配置源达梦数据库")
        source_db_type = "dm"

        job_name = get_input("作业名称 [默认：Dameng_to_Dameng_Sync]: ", default="Dameng_to_Dameng_Sync")
        print("选择作业模式:")
        print("  1) STREAMING (实时同步) - 暂不支持")
        print("  2) BATCH (批量同步)")
        mode_choice = get_input("请选择 [1-2] [默认：2]: ", default="2")
        job_mode = "BATCH"
        parallelism = get_input("并行度 [默认：1]: ", default="1")

        source_config = config_dameng_database(is_source=True)
        
        print_step(3, "字段映射配置")
        print(f"\n{Colors.BLUE}请手动输入源表字段信息（默认使用 SELECT * 查询所有字段）{Colors.NC}")
        print("  1) 手动输入字段（用于字段映射或类型转换）")
        print("  2) 跳过字段映射（使用 SELECT *）")
        cols_choice = get_input("请选择 [1-2]: ", default="2")
        
        if cols_choice == "1":
            field_mapping = configure_field_mapping(None, show_step=False)
        else:
            field_mapping = []

        print_step(4, "配置目标达梦数据库")
        sink_db_type = "dm"
        sink_config = config_dameng_database(is_source=False)

    elif source_choice == "3":
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

        print_step(4, "配置目标数据库")
        print("选择目标数据库类型:")
        print("  1) MySQL")
        print("  2) 达梦")
        sink_type_choice = get_input("请选择 [1-2] [默认：1]: ", default="1")
        
        if sink_type_choice == "1":
            sink_db_type = "mysql"
            sink_config = config_mysql_database(is_source=False)
        else:
            sink_db_type = "dm"
            sink_config = config_dameng_database(is_source=False)

        job_name = get_input("作业名称 [默认：API_to_MySQL_Sync]: ", default="API_to_MySQL_Sync")
        job_mode = get_input("作业模式 [STREAMING/BATCH 默认：BATCH]: ", default="BATCH").upper()
        parallelism = get_input("并行度 [默认：1]: ", default="1")

    elif source_choice == "4":
        print_success("使用测试模式 (FakeSource)")
        print_step(2, "配置作业信息")
        job_name = get_input("作业名称 [默认：FakeSource_Test]: ", default="FakeSource_Test")
        job_mode = get_input("作业模式 [默认：BATCH]: ", default="BATCH").upper()
        parallelism = get_input("并行度 [默认：1]: ", default="1")
    else:
        print_error("无效的选择")
        sys.exit(1)

    print_step(5, "确认配置")

    print("┌─────────────────────────────────────────────┐")
    print("│  数据同步配置                                 │")
    print("├─────────────────────────────────────────────┤")

    if source_choice == "1":
        sync_mode = "CDC" if job_mode == "STREAMING" else "Batch"
        print(f"│  同步模式：{sync_mode:<39}│")
        print("│  源数据库                                   │")
        print(f"│    类型：{'MySQL':<36}│")
        print(f"│    主机：{source_config['host']}:{source_config['port']:<30}│")
        print(f"│    用户：{source_config['user']:<36}│")
        print(f"│    数据库：{source_config['database']:<32}│")
        print(f"│    表：{source_config['table']:<38}│")
        print("├─────────────────────────────────────────────┤")
        print("│  目标数据库                                 │")
        print(f"│    类型：{'MySQL' if sink_db_type == 'mysql' else '达梦':<36}│")
        print(f"│    主机：{sink_config['host']}:{sink_config['port']:<30}│")
        print(f"│    用户：{sink_config['user']:<36}│")
        print(f"│    数据库：{sink_config['database']:<32}│")
        print(f"│    表：{sink_config['table']:<38}│")
    elif source_choice == "2":
        print(f"│  同步模式：{'Batch':<39}│")
        print("│  源数据库                                   │")
        print(f"│    类型：{'达梦':<36}│")
        print(f"│    主机：{source_config['host']}:{source_config['port']:<30}│")
        print(f"│    用户：{source_config['user']:<36}│")
        print(f"│    数据库：{source_config['database']:<32}│")
        print(f"│    表：{source_config['table']:<38}│")
        print("├─────────────────────────────────────────────┤")
        print("│  目标数据库                                 │")
        print(f"│    类型：{'达梦':<36}│")
        print(f"│    主机：{sink_config['host']}:{sink_config['port']:<30}│")
        print(f"│    用户：{sink_config['user']:<36}│")
        print(f"│    数据库：{sink_config['database']:<32}│")
        print(f"│    表：{sink_config['table']:<38}│")
    elif source_choice == "3":
        print(f"│  API URL: {api_config['url'][:37]:<37}│")
        print(f"│  方法：{api_config['method']:<36}│")
        print(f"│  内容字段：{api_config.get('content_field', '无'):<32}│")
        print("├─────────────────────────────────────────────┤")
        print("│  目标数据库                                 │")
        print(f"│    类型：{'MySQL' if sink_db_type == 'mysql' else '达梦':<36}│")
        print(f"│    主机：{sink_config['host']}:{sink_config['port']:<30}│")
        print(f"│    用户：{sink_config['user']:<36}│")
        print(f"│    数据库：{sink_config['database']:<32}│")
        print(f"│    表：{sink_config['table']:<38}│")
    else:
        print("│  模式：测试模式 (FakeSource + Console)       │")

    print("├─────────────────────────────────────────────┤")
    print("│  作业配置                                    │")
    print("├─────────────────────────────────────────────┤")
    print(f"│  名称：{job_name:<36}│")
    print(f"│  模式：{job_mode:<36}│")
    print(f"│  并行度：{parallelism:<34}│")
    print("└─────────────────────────────────────────────┘")

    confirm = get_input("\n确认生成配置文件并执行？[y/N]: ", default="n").lower()

    if confirm != "y":
        print_error("操作已取消")
        sys.exit(0)

    print("\n正在生成配置文件...")

    if os.name == 'nt':
        workspace = Path(os.environ.get('TEMP', 'D:\temp')) / 'seatunnel'
    else:
        workspace = Path("/home/admin/openclaw/workspace/temp")

    workspace.mkdir(parents=True, exist_ok=True)
    output_config = workspace / "generated_config.conf"

    # ========== 生成配置文件 ==========

    if source_choice == "1":
        if job_mode == "STREAMING":
            mapping_config = ""
            save_mode = "create"
            primary_keys = "\"id\""
            if 'field_mapping' in locals() and field_mapping:
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
            
            # 生成目标配置
            if sink_db_type == "mysql":
                sink_url = f"jdbc:mysql://{sink_config['host']}:{sink_config['port']}/{sink_config['database']}?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai&rewriteBatchedStatements=true"
                sink_driver = "com.mysql.cj.jdbc.Driver"
            else:
                sink_url = f"jdbc:dm://{sink_config['host']}:{sink_config['port']}/{sink_config['database']}"
                sink_driver = "dm.jdbc.driver.DmDriver"

            config_content = f"""# ============================================
# SeaTunnel MySQL CDC->{sink_db_type.upper()} 实时同步配置（自动生成）
# 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# ============================================

env {{
  job.mode = "STREAMING"
  job.name = "{job_name}"
  parallelism = {parallelism}
  checkpoint.interval = 10000
}}

source {{
  MySQL-CDC {{
    base-url = "jdbc:mysql://{source_config['host']}:{source_config['port']}/{source_config['database']}?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai"
    hostname = "{source_config['host']}"
    port = {source_config['port']}
    username = "{source_config['user']}"
    password = "{source_config['password']}"
    database-names = ["{source_config['database']}"]
    table-names = ["{source_config['database']}.{source_config['table']}"]
    server-id = "{source_config['server_id']}"
    startup.mode = "{source_config['startup_mode']}"
  }}
}}{mapping_config}

sink {{
  Jdbc {{
    url = "{sink_url}"
    driver = "{sink_driver}"
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
        else:
            mapping_config = ""
            save_mode = "create"
            primary_keys = "\"id\""
            if 'field_mapping' in locals() and field_mapping:
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
            
            if sink_db_type == "mysql":
                sink_url = f"jdbc:mysql://{sink_config['host']}:{sink_config['port']}/{sink_config['database']}?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai&rewriteBatchedStatements=true"
                sink_driver = "com.mysql.cj.jdbc.Driver"
                source_url = f"jdbc:mysql://{source_config['host']}:{source_config['port']}/{source_config['database']}?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai&rewriteBatchedStatements=true"
                source_driver = "com.mysql.cj.jdbc.Driver"
            else:
                sink_url = f"jdbc:dm://{sink_config['host']}:{sink_config['port']}/{sink_config['database']}"
                sink_driver = "dm.jdbc.driver.DmDriver"
                source_url = f"jdbc:dm://{source_config['host']}:{source_config['port']}/{source_config['database']}"
                source_driver = "dm.jdbc.driver.DmDriver"

            config_content = f"""# ============================================
# SeaTunnel MySQL->{sink_db_type.upper()} 批量同步配置（自动生成）
# 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# ============================================

env {{
  job.mode = "{job_mode}"
  job.name = "{job_name}"
  parallelism = {parallelism}
}}

source {{
  Jdbc {{
    url = "{source_url}"
    driver = "{source_driver}"
    user = "{source_config['user']}"
    password = "{source_config['password']}"
    database = "{source_config['database']}"
    table = "{source_config['table']}"
    query = "SELECT * FROM {source_config['table']}"
  }}
}}{mapping_config}

sink {{
  Jdbc {{
    url = "{sink_url}"
    driver = "{sink_driver}"
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

    elif source_choice == "2":
        mapping_config = ""
        
        if 'field_mapping' in locals() and field_mapping:
            has_mapping = any(col['source'] != col['target'] for col in field_mapping)
            if has_mapping:
                mapping_config = "\n\ntransform {\n  FieldMapper {\n    field_mapper = {"
                for col in field_mapping:
                    mapping_config += f"\n      {col['source']} = {col['target']},"
                mapping_config += "\n    }\n  }\n}\n"
        
        config_content = f"""# ============================================
# SeaTunnel 达梦->达梦 批量同步配置（自动生成）
# 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# ============================================

env {{
  job.mode = "{job_mode}"
  job.name = "{job_name}"
  parallelism = {parallelism}
}}

source {{
  Jdbc {{
    driver = "dm.jdbc.driver.DmDriver"
    url = "jdbc:dm://{source_config['host']}:{source_config['port']}/{source_config['database']}"
    user = "{source_config['user']}"
    password = "{source_config['password']}"
    query = "SELECT * FROM {source_config['database']}.{source_config['table']}"
  }}
}}{mapping_config}

sink {{
  Jdbc {{
    driver = "dm.jdbc.driver.DmDriver"
    url = "jdbc:dm://{sink_config['host']}:{sink_config['port']}/{sink_config['database']}"
    user = "{sink_config['user']}"
    password = "{sink_config['password']}"
    query = "INSERT INTO {sink_config['database']}.{sink_config['table']} SELECT * FROM source"
  }}
}}
"""

    elif source_choice == "3":
        json_field_lines = []
        schema_field_lines = []
        
        for col in field_mapping:
            source_field = col['source']
            target_field = col['target']
            field_type = col['type']
            
            if api_config.get('content_field'):
                if api_config.get('returns_array'):
                    json_path = f"$.{api_config['content_field']}[*].{source_field}"
                else:
                    json_path = f"$.{api_config['content_field']}.{source_field}"
            else:
                if api_config.get('returns_array'):
                    json_path = f"$[*].{source_field}"
                else:
                    json_path = f"$.{source_field}"
            
            json_field_lines.append(f'      "{target_field}" = "{json_path}"')
            
            seatunnel_type = "STRING"
            if field_type == "INT":
                seatunnel_type = "INT"
            elif field_type == "BOOLEAN":
                seatunnel_type = "BOOLEAN"
            elif field_type == "DATETIME":
                seatunnel_type = "TIMESTAMP"
            
            schema_field_lines.append(f'        {target_field} = "{seatunnel_type}"')
        
        primary_keys = "\"id\""
        for col in field_mapping:
            if col['source'] == 'id':
                primary_keys = f"\"{col['target']}\""
                break
        if primary_keys == "\"id\"" and field_mapping:
            primary_keys = f"\"{field_mapping[0]['target']}\""
        
        json_field_section = "    json_field = {\n" + "\n".join(json_field_lines) + "\n    }"
        schema_section = "    schema = {\n      fields {\n" + "\n".join(schema_field_lines) + "\n      }\n    }"
        
        if sink_db_type == "mysql":
            sink_url = f"jdbc:mysql://{sink_config['host']}:{sink_config['port']}/{sink_config['database']}?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai&rewriteBatchedStatements=true"
            sink_driver = "com.mysql.cj.jdbc.Driver"
        else:
            sink_url = f"jdbc:dm://{sink_config['host']}:{sink_config['port']}/{sink_config['database']}"
            sink_driver = "dm.jdbc.driver.DmDriver"

        config_content = f"""# ============================================
# SeaTunnel API->{sink_db_type.upper()} 同步配置（自动生成）
# 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# ============================================

env {{
  job.mode = "{job_mode}"
  job.name = "{job_name}"
  parallelism = {parallelism}
}}

source {{
  Http {{
    url = "{api_config['url']}"
    method = "{api_config['method']}"
    format = "json"

{json_field_section}

{schema_section}
    batch_size = 100

    socket_timeout_ms = 30000
    connect_timeout_ms = 30000
  }}
}}

sink {{
  Jdbc {{
    url = "{sink_url}"
    driver = "{sink_driver}"
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
        sys.exit(0)

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

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}操作被用户中断{Colors.NC}")
        sys.exit(130)
    except Exception as e:
        print_error(f"发生错误：{e}")
        sys.exit(1)
