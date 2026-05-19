#!/bin/bash

# ============================================
# SeaTunnel 交互式配置采集脚本
# ============================================
# 用途：在终端交互式采集用户配置，生成 SeaTunnel 配置文件并执行
# 使用：./seatunnel-interactive.sh
# ============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置模板文件
CONFIG_TEMPLATE="/home/admin/openclaw/workspace/temp/api_to_mysql.conf"
OUTPUT_CONFIG="/home/admin/openclaw/workspace/temp/generated_config.conf"

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  SeaTunnel 数据采集配置向导${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# --------------------------------------------
# 1. 采集 MySQL 目标数据库配置
# --------------------------------------------
echo -e "${YELLOW}【步骤 1/4】配置目标 MySQL 数据库${NC}"
echo ""

read -p "MySQL 主机地址 [默认：127.0.0.1]: " MYSQL_HOST
MYSQL_HOST=${MYSQL_HOST:-127.0.0.1}

read -p "MySQL 端口 [默认：3306]: " MYSQL_PORT
MYSQL_PORT=${MYSQL_PORT:-3306}

read -p "MySQL 用户名： " MYSQL_USER
while [ -z "$MYSQL_USER" ]; do
    echo -e "${RED}用户名不能为空${NC}"
    read -p "MySQL 用户名： " MYSQL_USER
done

# 隐藏密码输入
read -s -p "MySQL 密码： " MYSQL_PASSWORD
echo ""
while [ -z "$MYSQL_PASSWORD" ]; do
    echo -e "${RED}密码不能为空${NC}"
    read -s -p "MySQL 密码： " MYSQL_PASSWORD
    echo ""
done

read -p "目标数据库名 [默认：target]: " MYSQL_DATABASE
MYSQL_DATABASE=${MYSQL_DATABASE:-target}

read -p "目标表名 [默认：api_users]: " MYSQL_TABLE
MYSQL_TABLE=${MYSQL_TABLE:-api_users}

echo ""
echo -e "${GREEN}✓ MySQL 配置完成${NC}"
echo ""

# --------------------------------------------
# 2. 采集 API 源配置
# --------------------------------------------
echo -e "${YELLOW}【步骤 2/4】配置数据源 API${NC}"
echo ""

echo "选择数据源类型:"
echo "  1) Random User Generator API (https://randomuser.me/)"
echo "  2) 自定义 API"
read -p "请选择 [1-2] [默认：1]: " API_CHOICE
API_CHOICE=${API_CHOICE:-1}

if [ "$API_CHOICE" = "1" ]; then
    API_URL="https://randomuser.me/api/"
    API_METHOD="GET"
    API_PARAMS="results=10&nat=us&inc=name,email,login,location,dob,phone"
    CONTENT_FIELD="results"
    echo -e "${GREEN}✓ 使用 Random User Generator API${NC}"
elif [ "$API_CHOICE" = "2" ]; then
    read -p "API URL: " API_URL
    while [ -z "$API_URL" ]; do
        echo -e "${RED}API URL 不能为空${NC}"
        read -p "API URL: " API_URL
    done
    
    read -p "HTTP 方法 [默认：GET]: " API_METHOD
    API_METHOD=${API_METHOD:-GET}
    
    read -p "请求参数 (URL 格式，如：key1=value1&key2=value2): " API_PARAMS
    
    read -p "JSON 内容字段 (如：results, data, items) [默认：results]: " CONTENT_FIELD
    CONTENT_FIELD=${CONTENT_FIELD:-results}
else
    echo -e "${RED}无效的选择${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ API 配置完成${NC}"
echo ""

# --------------------------------------------
# 3. 采集作业配置
# --------------------------------------------
echo -e "${YELLOW}【步骤 3/4】配置 SeaTunnel 作业${NC}"
echo ""

read -p "作业名称 [默认：API_to_MySQL_Sync]: " JOB_NAME
JOB_NAME=${JOB_NAME:-API_to_MySQL_Sync}

read -p "作业模式 [默认：BATCH]: " JOB_MODE
JOB_MODE=${JOB_MODE:-BATCH}
JOB_MODE=$(echo "$JOB_MODE" | tr '[:lower:]' '[:upper:]')

read -p "并行度 [默认：1]: " PARALLELISM
PARALLELISM=${PARALLELISM:-1}

read -p "批处理大小 [默认：100]: " BATCH_SIZE
BATCH_SIZE=${BATCH_SIZE:-100}

echo ""
echo -e "${GREEN}✓ 作业配置完成${NC}"
echo ""

# --------------------------------------------
# 4. 确认配置
# --------------------------------------------
echo -e "${YELLOW}【步骤 4/4】确认配置${NC}"
echo ""
echo "┌─────────────────────────────────────────────┐"
echo "│  MySQL 配置                                  │"
echo "├─────────────────────────────────────────────┤"
printf "│  主机：%-36s│\n" "$MYSQL_HOST:$MYSQL_PORT"
printf "│  用户：%-36s│\n" "$MYSQL_USER"
printf "│  数据库：%-34s│\n" "$MYSQL_DATABASE"
printf "│  表：%-38s│\n" "$MYSQL_TABLE"
echo "├─────────────────────────────────────────────┤"
echo "│  API 配置                                    │"
echo "├─────────────────────────────────────────────┤"
printf "│  URL: %-37s│\n" "${API_URL:0:37}"
printf "│  方法：%-36s│\n" "$API_METHOD"
echo "├─────────────────────────────────────────────┤"
echo "│  作业配置                                    │"
echo "├─────────────────────────────────────────────┤"
printf "│  名称：%-36s│\n" "$JOB_NAME"
printf "│  模式：%-36s│\n" "$JOB_MODE"
printf "│  并行度：%-34s│\n" "$PARALLELISM"
echo "└─────────────────────────────────────────────┘"
echo ""

read -p "确认生成配置文件并执行？[y/N]: " CONFIRM
CONFIRM=$(echo "$CONFIRM" | tr '[:upper:]' '[:lower:]')

if [ "$CONFIRM" != "y" ]; then
    echo -e "${RED}操作已取消${NC}"
    exit 0
fi

# --------------------------------------------
# 生成 SeaTunnel 配置文件
# --------------------------------------------
echo ""
echo -e "${BLUE}正在生成配置文件...${NC}"

cat > "$OUTPUT_CONFIG" << EOF
# ============================================
# SeaTunnel 数据同步配置（自动生成）
# 生成时间：$(date '+%Y-%m-%d %H:%M:%S')
# ============================================

env {
  job.mode = "$JOB_MODE"
  job.name = "$JOB_NAME"
  parallelism = $PARALLELISM
}

source {
  Http {
    url = "$API_URL"
    method = "$API_METHOD"
    
    params = {
      "$API_PARAMS"
    }
    
    headers = {
      "Content-Type" = "application/json"
      "User-Agent" = "SeaTunnel-HTTP-Source"
    }
    
    content_field = "$CONTENT_FIELD"
    batch_size = $BATCH_SIZE
    
    socket_timeout_ms = 30000
    connect_timeout_ms = 30000
  }
}

sink {
  Jdbc {
    url = "jdbc:mysql://$MYSQL_HOST:$MYSQL_PORT/$MYSQL_DATABASE?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai&rewriteBatchedStatements=true"
    driver = "com.mysql.cj.jdbc.Driver"
    user = "$MYSQL_USER"
    password = "$MYSQL_PASSWORD"
    database = "$MYSQL_DATABASE"
    table-name = "$MYSQL_TABLE"
    
    primary_keys = ["email"]
    batch_size = $BATCH_SIZE
    support_upsert_by_query_primary_key_exist = true
    generate_sink_sql = true
    save_mode = "append"
  }
}
EOF

echo -e "${GREEN}✓ 配置文件已生成：$OUTPUT_CONFIG${NC}"
echo ""

# --------------------------------------------
# 执行 SeaTunnel 任务
# --------------------------------------------
echo -e "${BLUE}准备执行 SeaTunnel 任务...${NC}"
echo ""

# 检测 SeaTunnel 安装路径
if [ -n "$SEATUNNEL_HOME" ]; then
    SEATUNNEL_BIN="$SEATUNNEL_HOME/bin/seatunnel.sh"
elif [ -f "/opt/seatunnel/bin/seatunnel.sh" ]; then
    SEATUNNEL_BIN="/opt/seatunnel/bin/seatunnel.sh"
elif [ -f "$HOME/seatunnel/bin/seatunnel.sh" ]; then
    SEATUNNEL_BIN="$HOME/seatunnel/bin/seatunnel.sh"
else
    echo -e "${YELLOW}警告：未找到 SeaTunnel 安装路径${NC}"
    echo "请设置 SEATUNNEL_HOME 环境变量或手动执行以下命令:"
    echo ""
    echo "  seatunnel.sh --config $OUTPUT_CONFIG -m local"
    echo ""
    exit 0
fi

echo -e "${GREEN}找到 SeaTunnel: $SEATUNNEL_BIN${NC}"
echo ""
echo -e "${BLUE}执行命令：$SEATUNNEL_BIN --config $OUTPUT_CONFIG -m local${NC}"
echo ""

# 执行 SeaTunnel
if [ -f "$SEATUNNEL_BIN" ]; then
    "$SEATUNNEL_BIN" --config "$OUTPUT_CONFIG" -m local
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo ""
        echo -e "${GREEN}============================================${NC}"
        echo -e "${GREEN}  ✓ 任务执行成功！${NC}"
        echo -e "${GREEN}============================================${NC}"
    else
        echo ""
        echo -e "${RED}============================================${NC}"
        echo -e "${RED}  ✗ 任务执行失败 (退出码：$EXIT_CODE)${NC}"
        echo -e "${RED}============================================${NC}"
        exit $EXIT_CODE
    fi
else
    echo -e "${RED}错误：SeaTunnel 可执行文件不存在${NC}"
    exit 1
fi
