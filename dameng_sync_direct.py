#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
达梦数据库直接同步工具（使用 pyodbc）
只支持达梦，简易
成功
"""

import os
import sys
import socket
import pyodbc
from datetime import datetime

class Colors:
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    NC = '\033[0m'

def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.NC}")

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.NC}")

def get_input(prompt, default="", required=False, hide=False):
    """获取用户输入"""
    while True:
        if hide:
            # 简单的密码隐藏
            import getpass
            value = getpass.getpass(prompt)
        else:
            value = input(prompt)
        
        if not value and default:
            return default
        if required and not value:
            print_error("该字段为必填项")
            continue
        return value

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
        print_error(f"获取达梦数据库列表失败：{e}")
        return None

def get_dameng_database_tables(host, port, user, password, database):
    """获取达梦数据库中的所有表"""
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
    """获取达梦表的所有列名"""
    try:
        conn_str = f"DRIVER={{DM8 ODBC DRIVER}};SERVER={host};PORT={port};UID={user};PWD={password};DATABASE={database}"
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute(f"SELECT COLUMN_NAME FROM ALL_TAB_COLUMNS WHERE OWNER = '{database.upper()}' AND TABLE_NAME = '{table.upper()}' ORDER BY COLUMN_ID")
        columns = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return columns
    except Exception as e:
        print_error(f"获取达梦表结构失败：{e}")
        return None

def config_dameng_database(is_source=True):
    """配置达梦数据库"""
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

def sync_dameng_to_dameng(source_config, sink_config):
    """直接同步达梦数据库到达梦数据库"""
    print(f"\n{Colors.BLUE}开始同步数据...{Colors.NC}")
    
    source_conn_str = f"DRIVER={{DM8 ODBC DRIVER}};SERVER={source_config['host']};PORT={source_config['port']};UID={source_config['user']};PWD={source_config['password']};DATABASE={source_config['database']}"
    sink_conn_str = f"DRIVER={{DM8 ODBC DRIVER}};SERVER={sink_config['host']};PORT={sink_config['port']};UID={sink_config['user']};PWD={sink_config['password']};DATABASE={sink_config['database']}"
    
    try:
        # 获取源表字段
        source_columns = get_dameng_table_columns(
            source_config['host'],
            source_config['port'],
            source_config['user'],
            source_config['password'],
            source_config['database'],
            source_config['table']
        )
        
        if not source_columns:
            print_error("无法获取源表字段信息")
            return False
        
        columns_str = ", ".join(source_columns)
        source_table = f"{source_config['database'].upper()}.{source_config['table'].upper()}"
        sink_table = f"{sink_config['database'].upper()}.{sink_config['table'].upper()}"
        
        print(f"{Colors.BLUE}源表：{source_table}{Colors.NC}")
        print(f"{Colors.BLUE}目标表：{sink_table}{Colors.NC}")
        print(f"{Colors.BLUE}字段：{columns_str}{Colors.NC}")
        
        # 连接源数据库
        source_conn = pyodbc.connect(source_conn_str)
        source_cursor = source_conn.cursor()
        
        # 连接目标数据库
        sink_conn = pyodbc.connect(sink_conn_str)
        sink_cursor = sink_conn.cursor()
        
        # 查询源数据
        query_sql = f"SELECT {columns_str} FROM {source_table}"
        print(f"\n{Colors.BLUE}执行查询：{query_sql}{Colors.NC}")
        source_cursor.execute(query_sql)
        
        # 获取数据
        rows = source_cursor.fetchall()
        total_rows = len(rows)
        print(f"{Colors.GREEN}✓ 查询完成，共 {total_rows} 条数据{Colors.NC}")
        
        if total_rows == 0:
            print(f"{Colors.YELLOW}警告：源表没有数据{Colors.NC}")
            source_conn.close()
            sink_conn.close()
            return True
        
        # 构建插入语句（使用 MERGE INTO 实现 upsert）
        placeholders = ", ".join(["?" for _ in source_columns])
        insert_sql = f"INSERT INTO {sink_table} ({columns_str}) VALUES ({placeholders})"
        
        # 统计变量
        inserted = 0
        updated = 0
        failed = 0
        
        print(f"\n{Colors.BLUE}开始写入目标表...{Colors.NC}")
        
        for i, row in enumerate(rows, 1):
            pk_column = source_columns[0]
            pk_value = row[0]

            try:
                # 先查询目标表是否存在该主键
                check_sql = f"SELECT {columns_str} FROM {sink_table} WHERE {pk_column} = ?"
                sink_cursor.execute(check_sql, (pk_value,))
                existing_row = sink_cursor.fetchone()
                
                if existing_row:
                    # 主键存在，比较数据
                    if list(existing_row) == list(row):
                        # 数据完全相同，跳过
                        continue
                    else:
                        # 数据不同，执行更新
                        update_set = ", ".join([f"{col} = ?" for col in source_columns[1:]])
                        update_sql = f"UPDATE {sink_table} SET {update_set} WHERE {pk_column} = ?"
                        sink_cursor.execute(update_sql, row[1:] + (pk_value,))
                        sink_conn.commit()
                        updated += 1
                else:
                    # 主键不存在，执行插入
                    sink_cursor.execute(insert_sql, row)
                    sink_conn.commit()
                    inserted += 1
            except Exception as e:
                print_error(f"处理失败（行 {i}）：{e}")
                failed += 1

            if i % 100 == 0:
                print(f"{Colors.BLUE}已处理 {i}/{total_rows} 条数据{Colors.NC}")
        
        # 关闭连接
        source_conn.close()
        sink_conn.close()
        
        # 输出统计
        print(f"\n{Colors.GREEN}✓ 同步完成！{Colors.NC}")
        print(f"  插入：{inserted} 条")
        print(f"  更新：{updated} 条")
        print(f"  失败：{failed} 条")

        if failed > 0:
            print_error(f"同步完成但有 {failed} 条数据处理失败")
            return False

        return True
        
    except Exception as e:
        print_error(f"同步失败：{e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("  达梦数据库直接同步工具")
    print("=" * 60)
    
    # 配置源数据库
    print("\n【步骤 1/2】配置源达梦数据库")
    source_config = config_dameng_database(is_source=True)
    
    # 配置目标数据库
    print("\n【步骤 2/2】配置目标达梦数据库")
    sink_config = config_dameng_database(is_source=False)
    
    # 确认
    print(f"\n{Colors.BLUE}任务摘要：{Colors.NC}")
    print(f"  源数据库：达梦 {source_config['host']}:{source_config['port']}/{source_config['database']}.{source_config['table']}")
    print(f"  目标数据库：达梦 {sink_config['host']}:{sink_config['port']}/{sink_config['database']}.{sink_config['table']}")
    
    confirm = get_input("\n确认执行同步？[Y/n]: ", default="Y").upper()
    if confirm == "Y":
        start_time = datetime.now()
        success = sync_dameng_to_dameng(source_config, sink_config)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n{Colors.BLUE}耗时：{duration:.2f} 秒{Colors.NC}")
        
        if success:
            print_success("同步任务执行成功")
        else:
            print_error("同步任务执行失败")
    else:
        print_error("操作已取消")

if __name__ == "__main__":
    main()