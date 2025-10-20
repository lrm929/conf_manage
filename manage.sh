#!/bin/bash

# 配置文件生成系统 - 统一服务管理脚本
# 支持：start, stop, restart, status, install, uninstall, logs

# 配置变量
SERVICE_NAME="config-generator"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$APP_DIR/backend"
PYTHON_CMD="python3"
APP_FILE="app.py"
PORT=5000
PID_FILE="/tmp/$SERVICE_NAME.pid"
LOG_FILE="/tmp/$SERVICE_NAME.log"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Python环境
check_python() {
    if ! command -v $PYTHON_CMD &> /dev/null; then
        log_error "未找到Python3，请先安装Python3"
        exit 1
    fi
    
    local python_version=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
    log_info "Python版本: $python_version"
}

# 检查pip
check_pip() {
    if ! command -v pip3 &> /dev/null; then
        log_error "未找到pip3，请先安装pip3"
        exit 1
    fi
}

# 安装依赖
install_dependencies() {
    log_info "检查并安装Python依赖包..."
    cd "$BACKEND_DIR" || exit 1
    
    if [[ -f "requirements.txt" ]]; then
        pip3 install -r requirements.txt --user
        if [[ $? -eq 0 ]]; then
            log_info "依赖包安装成功"
        else
            log_error "依赖包安装失败"
            exit 1
        fi
    else
        log_warn "未找到requirements.txt文件"
    fi
    
    cd "$APP_DIR"
}

# 创建必要目录
create_directories() {
    log_info "创建必要的目录..."
    
    mkdir -p "$APP_DIR/uploads"
    mkdir -p "$APP_DIR/downloads"
    mkdir -p "$APP_DIR/templates"
    
    log_info "目录创建完成"
}

# 检查服务是否运行
is_running() {
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# 检查端口
check_port() {
    if netstat -tuln 2>/dev/null | grep -q ":$PORT "; then
        log_warn "端口 $PORT 已被占用"
        log_info "尝试使用其他端口..."
        PORT=5001
        if netstat -tuln 2>/dev/null | grep -q ":$PORT "; then
            PORT=5002
            if netstat -tuln 2>/dev/null | grep -q ":$PORT "; then
                log_error "无法找到可用端口"
                exit 1
            fi
        fi
        log_info "使用端口: $PORT"
    fi
}

# 启动服务
start_service() {
    log_info "启动 $SERVICE_NAME 服务..."
    
    if is_running; then
        log_warn "服务已在运行中"
        return 0
    fi
    
    check_python
    check_pip
    install_dependencies
    create_directories
    check_port
    
    # 启动应用
    cd "$BACKEND_DIR" || exit 1
    
    # 设置环境变量
    export FLASK_ENV=production
    export FLASK_APP="$APP_FILE"
    export PYTHONPATH="$BACKEND_DIR"
    
    # 使用nohup在后台运行
    nohup $PYTHON_CMD "$APP_FILE" --host=0.0.0.0 --port=$PORT > "$LOG_FILE" 2>&1 &
    local pid=$!
    
    # 保存PID
    echo "$pid" > "$PID_FILE"
    
    # 等待服务启动
    sleep 3
    
    if is_running; then
        log_info "服务启动成功 (PID: $pid)"
        log_info "访问地址: http://localhost:$PORT"
        log_info "日志文件: $LOG_FILE"
        log_info "默认登录: admin / admin123"
    else
        log_error "服务启动失败"
        rm -f "$PID_FILE"
        exit 1
    fi
}

# 停止服务
stop_service() {
    log_info "停止 $SERVICE_NAME 服务..."
    
    if ! is_running; then
        log_warn "服务未运行"
        return 0
    fi
    
    local pid=$(cat "$PID_FILE")
    
    # 优雅停止
    kill -TERM "$pid" 2>/dev/null
    
    # 等待进程结束
    local count=0
    while ps -p "$pid" > /dev/null 2>&1 && [[ $count -lt 10 ]]; do
        sleep 1
        ((count++))
    done
    
    # 强制停止
    if ps -p "$pid" > /dev/null 2>&1; then
        log_warn "强制停止服务"
        kill -KILL "$pid" 2>/dev/null
    fi
    
    rm -f "$PID_FILE"
    log_info "服务已停止"
}

# 重启服务
restart_service() {
    log_info "重启 $SERVICE_NAME 服务..."
    stop_service
    sleep 2
    start_service
}

# 查看服务状态
status_service() {
    log_info "检查 $SERVICE_NAME 服务状态..."
    
    if is_running; then
        local pid=$(cat "$PID_FILE")
        local memory=$(ps -p "$pid" -o rss= 2>/dev/null | awk '{print $1/1024 " MB"}' || echo "未知")
        local cpu=$(ps -p "$pid" -o %cpu= 2>/dev/null | awk '{print $1 "%"}' || echo "未知")
        
        log_info "服务状态: 运行中"
        log_info "进程ID: $pid"
        log_info "内存使用: $memory"
        log_info "CPU使用: $cpu"
        log_info "端口: $PORT"
        log_info "日志文件: $LOG_FILE"
        
        # 检查端口监听
        if netstat -tuln 2>/dev/null | grep -q ":$PORT "; then
            log_info "端口监听: 正常"
        else
            log_warn "端口监听: 异常"
        fi
        
        # 显示访问信息
        echo ""
        log_info "访问信息:"
        log_info "  Web界面: http://localhost:$PORT"
        log_info "  默认用户: admin"
        log_info "  默认密码: admin123"
    else
        log_info "服务状态: 未运行"
    fi
}

# 查看日志
view_logs() {
    if [[ -f "$LOG_FILE" ]]; then
        log_info "显示最近的日志 (按Ctrl+C退出):"
        tail -f "$LOG_FILE"
    else
        log_warn "日志文件不存在: $LOG_FILE"
    fi
}

# 安装服务 (创建systemd服务)
install_service() {
    log_info "安装 $SERVICE_NAME 为系统服务..."
    
    if [[ $EUID -ne 0 ]]; then
        log_error "安装系统服务需要root权限"
        log_info "请使用: sudo $0 install"
        exit 1
    fi
    
    # 创建systemd服务文件
    cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOF
[Unit]
Description=Config Generator System
After=network.target

[Service]
Type=simple
User=$(whoami)
Group=$(whoami)
WorkingDirectory=$BACKEND_DIR
ExecStart=$PYTHON_CMD $APP_FILE --host=0.0.0.0 --port=$PORT
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

Environment=FLASK_ENV=production
Environment=FLASK_APP=$APP_FILE
Environment=PYTHONPATH=$BACKEND_DIR

[Install]
WantedBy=multi-user.target
EOF

    # 重新加载systemd
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    
    log_info "系统服务安装完成"
    log_info "使用以下命令管理服务:"
    log_info "  systemctl start $SERVICE_NAME"
    log_info "  systemctl stop $SERVICE_NAME"
    log_info "  systemctl restart $SERVICE_NAME"
    log_info "  systemctl status $SERVICE_NAME"
}

# 卸载服务
uninstall_service() {
    log_info "卸载 $SERVICE_NAME 系统服务..."
    
    if [[ $EUID -ne 0 ]]; then
        log_error "卸载系统服务需要root权限"
        log_info "请使用: sudo $0 uninstall"
        exit 1
    fi
    
    # 停止服务
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        systemctl stop "$SERVICE_NAME"
    fi
    
    # 禁用服务
    if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
        systemctl disable "$SERVICE_NAME"
    fi
    
    # 删除服务文件
    if [[ -f "/etc/systemd/system/$SERVICE_NAME.service" ]]; then
        rm -f "/etc/systemd/system/$SERVICE_NAME.service"
        systemctl daemon-reload
    fi
    
    log_info "系统服务卸载完成"
}

# 显示帮助信息
show_help() {
    echo "配置文件生成系统 - 统一服务管理脚本"
    echo ""
    echo "用法: $0 {start|stop|restart|status|install|uninstall|logs|help}"
    echo ""
    echo "命令:"
    echo "  start     启动服务 (开发模式)"
    echo "  stop      停止服务"
    echo "  restart   重启服务"
    echo "  status    查看服务状态"
    echo "  install   安装为系统服务 (需要root权限)"
    echo "  uninstall 卸载系统服务 (需要root权限)"
    echo "  logs      查看日志"
    echo "  help      显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 start     # 启动服务"
    echo "  $0 status    # 查看状态"
    echo "  sudo $0 install  # 安装系统服务"
    echo ""
    echo "访问信息:"
    echo "  Web界面: http://localhost:5000"
    echo "  默认用户: admin"
    echo "  默认密码: admin123"
}

# 主函数
main() {
    case "${1:-help}" in
        start)
            start_service
            ;;
        stop)
            stop_service
            ;;
        restart)
            restart_service
            ;;
        status)
            status_service
            ;;
        install)
            install_service
            ;;
        uninstall)
            uninstall_service
            ;;
        logs)
            view_logs
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"