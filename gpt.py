#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
gpt生成的版本
完整版：支持 MySQL / 达梦 DM → MySQL / DM
包含：
✔ 数据源配置
✔ 字段映射
✔ sink 配置
✔ 生成 SeaTunnel 配置
"""

import os
import getpass

try:
    import mysql.connector
    MYSQL_OK = True
except:
    MYSQL_OK = False

try:
    import dmPython
    DM_OK = True
except:
    DM_OK = False

DB_MYSQL = "mysql"
DB_DM = "dm"

# ================= 输入 =================

def inp(p, d=None, hide=False):
    while True:
        v = getpass.getpass(p) if hide else input(p)
        if not v and d: return d
        if not v: continue
        return v

# ================= DB操作 =================

def connect_mysql(host, port, user, pwd, db):
    return mysql.connector.connect(host=host, port=int(port), user=user, password=pwd, database=db)


def connect_dm(host, port, user, pwd, db):
    conn = dmPython.connect(host=host, port=int(port), user=user, password=pwd)
    cur = conn.cursor()
    cur.execute(f'ALTER SESSION SET CURRENT_SCHEMA = "{db.upper()}"')
    cur.close()
    return conn


def get_tables(t, host, port, user, pwd, db):
    if t == DB_MYSQL:
        conn = connect_mysql(host, port, user, pwd, db)
        cur = conn.cursor()
        cur.execute("SHOW TABLES")
        res = [r[0] for r in cur.fetchall()]
    else:
        conn = connect_dm(host, port, user, pwd, db)
        cur = conn.cursor()
        cur.execute(f"SELECT TABLE_NAME FROM ALL_TABLES WHERE OWNER='{db.upper()}'")
        res = [r[0] for r in cur.fetchall()]
    cur.close(); conn.close()
    return res


def get_cols(t, host, port, user, pwd, db, table):
    if t == DB_MYSQL:
        conn = connect_mysql(host, port, user, pwd, db)
        cur = conn.cursor()
        cur.execute(f"DESCRIBE `{table}`")
        rows = cur.fetchall()
    else:
        conn = connect_dm(host, port, user, pwd, db)
        cur = conn.cursor()
        cur.execute(f"""
        SELECT COLUMN_NAME, DATA_TYPE FROM ALL_TAB_COLUMNS
        WHERE TABLE_NAME='{table.upper()}' AND OWNER='{db.upper()}'
        """)
        rows = cur.fetchall()

    cols = []
    for r in rows:
        name, tp = r[0], str(r[1]).upper()
        if "INT" in tp or "NUMBER" in tp:
            t2 = "INT"
        elif "DATE" in tp or "TIME" in tp:
            t2 = "DATETIME"
        else:
            t2 = "STRING"
        cols.append({"source": name, "target": name, "type": t2})

    cur.close(); conn.close()
    return cols

# ================= 字段映射 =================

def mapping(cols):
    while True:
        print("\n当前字段映射：")
        for i,c in enumerate(cols):
            print(i+1, c)

        print("1改名 2改类型 3删 4完成")
        ch = inp("选:")

        if ch == "1":
            i = int(inp("序号:")) - 1
            cols[i]['target'] = inp("新字段名:")
        elif ch == "2":
            i = int(inp("序号:")) - 1
            cols[i]['type'] = inp("类型(INT/STRING/DATETIME):")
        elif ch == "3":
            i = int(inp("序号:")) - 1
            cols.pop(i)
        elif ch == "4":
            return cols

# ================= JDBC =================

def jdbc(t, host, port, db):
    if t == DB_MYSQL:
        return f"jdbc:mysql://{host}:{port}/{db}", "com.mysql.cj.jdbc.Driver"
    else:
        return f"jdbc:dm://{host}:{port}/{db}", "dm.jdbc.driver.DmDriver"

# ================= 生成配置 =================

def gen_conf(src, sink, cols):
    src_url, src_driver = jdbc(src['type'], src['host'], src['port'], src['db'])
    sink_url, sink_driver = jdbc(sink['type'], sink['host'], sink['port'], sink['db'])

    mapping_str = "\n".join([f"      {c['source']} = {c['target']}" for c in cols])

    return f"""
env {{
  job.mode = \"BATCH\"
}}

source {{
  Jdbc {{
    url = \"{src_url}\"
    driver = \"{src_driver}\"
    user = \"{src['user']}\"
    password = \"{src['pwd']}\"
    query = \"select * from {src['table']}\"
  }}
}}

transform {{
  FieldMapper {{
    field_mapper = {{
{mapping_str}
    }}
  }}
}}

sink {{
  Jdbc {{
    url = \"{sink_url}\"
    driver = \"{sink_driver}\"
    user = \"{sink['user']}\"
    password = \"{sink['pwd']}\"
    table = \"{sink['table']}\"
    save_mode = \"upsert\"
  }}
}}
"""

# ================= 主流程 =================

def main():
    print("1 MySQL 2 DM")
    t = DB_MYSQL if inp("源:","1")=="1" else DB_DM

    host = inp("host:","127.0.0.1")
    port = inp("port:","3306" if t==DB_MYSQL else "5236")
    user = inp("user:")
    pwd = inp("pwd:", hide=True)
    db = inp("db:")

    tables = get_tables(t, host, port, user, pwd, db)
    print(tables)
    table = inp("选表:")

    cols = get_cols(t, host, port, user, pwd, db, table)
    cols = mapping(cols)

    print("\n配置 sink")
    t2 = DB_MYSQL if inp("目标1 MySQL 2 DM:","1")=="1" else DB_DM
    host2 = inp("host:","127.0.0.1")
    port2 = inp("port:","3306" if t2==DB_MYSQL else "5236")
    user2 = inp("user:")
    pwd2 = inp("pwd:", hide=True)
    db2 = inp("db:")
    table2 = inp("table:")

    conf = gen_conf(
        {"type":t,"host":host,"port":port,"user":user,"pwd":pwd,"db":db,"table":table},
        {"type":t2,"host":host2,"port":port2,"user":user2,"pwd":pwd2,"db":db2,"table":table2},
        cols
    )

    path = "generated.conf"
    with open(path,"w") as f:
        f.write(conf)

    print("\n已生成:", path)


if __name__ == "__main__":
    main()
