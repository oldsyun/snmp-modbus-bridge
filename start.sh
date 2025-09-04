#!/bin/bash
# =============================================================================
# SNMP-Modbus 桥接服务启动脚本
# =============================================================================
#
# 功能：
# 1. 检查 Python 环境和依赖
# 2. 创建必要的目录和日志文件
# 3. 启动 SNMP-Modbus 桥接服务
# 4. 支持前台和后台运行模式
# 5. 提供服务状态检查和停止功能
#
# 使用方法：
#   ./start.sh start    # 启动服务（后台运行）
#   ./start.sh stop     # 停止服务
#   ./start.sh restart  # 重启服务
#   ./start.sh status   # 查看服务状态
#   ./start.sh run      # 前台运行（调试模式）
#
# 作者: SNMP-Modbus Bridge Team
# 版本: 1.0
# 日期: 2025-09-04
# =============================================================================

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="snmp-modbus-bridge"
PYTHON_SCRIPT="snmp_modbus_bridge.py"
PID_FILE="/var/run/${SERVICE_NAME}.pid"
LOG_DIR="/var/log/${SERVICE_NAME}"
LOG_FILE="${LOG_DIR}/service.log"
CONFIG_FILE="${SCRIPT_DIR}/config.ini"
LOCK_FILE="/var/lock/subsys/${SERVICE_NAME}"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $1" >> "${LOG_FILE}" 2>/dev/null
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [WARN] $1" >> "${LOG_FILE}" 2>/dev/null
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $1" >> "${LOG_FILE}" 2>/dev/null
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [DEBUG] $1" >> "${LOG_FILE}" 2>/dev/null
}

# 检查是否以 root 权限运行
check_root() {
    if [[ $EUID -eq 0 ]]; then
        return 0
    else
        return 1
    fi
}

# 创建必要的目录
create_directories() {
    if check_root; then
        # 以 root 权限运行，创建系统目录
        mkdir -p "${LOG_DIR}"
        mkdir -p "$(dirname "${PID_FILE}")"
        mkdir -p "$(dirname "${LOCK_FILE}")"
        chmod 755 "${LOG_DIR}"
    else
        # 非 root 权限，使用本地目录
        LOG_DIR="${SCRIPT_DIR}/logs"
        LOG_FILE="${LOG_DIR}/service.log"
        PID_FILE="${SCRIPT_DIR}/${SERVICE_NAME}.pid"
        LOCK_FILE="${SCRIPT_DIR}/${SERVICE_NAME}.lock"
        
        mkdir -p "${LOG_DIR}"
        log_warn "非 root 权限运行，使用本地目录: ${LOG_DIR}"
    fi
}

# 检查 Python 环境
check_python() {
    log_info "检查 Python 环境..."
    
    # 检查 Python 3
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 未安装"
        return 1
    fi
    
    local python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
    log_info "Python 版本: ${python_version}"
    
    # 检查必要的 Python 模块
    local required_modules=("pysnmp" "pymodbus" "pyasn1" "configparser")
    for module in "${required_modules[@]}"; do
        if ! python3 -c "import ${module}" &> /dev/null; then
            log_error "Python 模块 ${module} 未安装"
            log_info "请运行: pip3 install ${module}"
            return 1
        fi
    done
    
    log_info "Python 环境检查通过"
    return 0
}

# 检查配置文件
check_config() {
    log_info "检查配置文件..."
    
    if [[ ! -f "${CONFIG_FILE}" ]]; then
        log_error "配置文件不存在: ${CONFIG_FILE}"
        return 1
    fi
    
    # 测试配置文件加载
    if ! python3 -c "
import sys
sys.path.insert(0, '${SCRIPT_DIR}')
try:
    from config_loader import SNMP_BRIDGE_CONFIG, MODBUS_TYPE
    print('配置文件加载成功')
except Exception as e:
    print(f'配置文件加载失败: {e}')
    sys.exit(1)
" &> /dev/null; then
        log_error "配置文件格式错误或加载失败"
        return 1
    fi
    
    log_info "配置文件检查通过"
    return 0
}

# 获取服务进程 ID
get_pid() {
    if [[ -f "${PID_FILE}" ]]; then
        local pid=$(cat "${PID_FILE}" 2>/dev/null)
        if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
            echo "${pid}"
            return 0
        else
            # PID 文件存在但进程不存在，清理 PID 文件
            rm -f "${PID_FILE}"
        fi
    fi
    return 1
}

# 检查服务状态
check_status() {
    local pid=$(get_pid)
    if [[ -n "${pid}" ]]; then
        log_info "服务正在运行 (PID: ${pid})"
        return 0
    else
        log_info "服务未运行"
        return 1
    fi
}

# 启动服务
start_service() {
    log_info "启动 ${SERVICE_NAME} 服务..."
    
    # 检查服务是否已经运行
    if check_status &>/dev/null; then
        log_warn "服务已经在运行"
        return 1
    fi
    
    # 检查环境
    if ! check_python || ! check_config; then
        log_error "环境检查失败，无法启动服务"
        return 1
    fi
    
    # 切换到脚本目录
    cd "${SCRIPT_DIR}"
    
    # 启动服务（后台运行）
    nohup python3 "${PYTHON_SCRIPT}" >> "${LOG_FILE}" 2>&1 &
    local pid=$!
    
    # 保存 PID
    echo "${pid}" > "${PID_FILE}"
    
    # 创建锁文件
    touch "${LOCK_FILE}"
    
    # 等待服务启动
    sleep 2
    
    # 验证服务是否成功启动
    if kill -0 "${pid}" 2>/dev/null; then
        log_info "服务启动成功 (PID: ${pid})"
        log_info "日志文件: ${LOG_FILE}"
        return 0
    else
        log_error "服务启动失败"
        rm -f "${PID_FILE}" "${LOCK_FILE}"
        return 1
    fi
}

# 停止服务
stop_service() {
    log_info "停止 ${SERVICE_NAME} 服务..."
    
    local pid=$(get_pid)
    if [[ -z "${pid}" ]]; then
        log_warn "服务未运行"
        return 1
    fi
    
    # 发送 TERM 信号
    kill -TERM "${pid}" 2>/dev/null
    
    # 等待进程结束
    local count=0
    while kill -0 "${pid}" 2>/dev/null && [[ ${count} -lt 10 ]]; do
        sleep 1
        ((count++))
    done
    
    # 如果进程仍在运行，强制杀死
    if kill -0 "${pid}" 2>/dev/null; then
        log_warn "强制停止服务"
        kill -KILL "${pid}" 2>/dev/null
        sleep 1
    fi
    
    # 清理文件
    rm -f "${PID_FILE}" "${LOCK_FILE}"
    
    log_info "服务已停止"
    return 0
}

# 重启服务
restart_service() {
    log_info "重启 ${SERVICE_NAME} 服务..."
    stop_service
    sleep 2
    start_service
}

# 前台运行（调试模式）
run_foreground() {
    log_info "前台运行 ${SERVICE_NAME} 服务（调试模式）..."
    
    # 检查环境
    if ! check_python || ! check_config; then
        log_error "环境检查失败，无法启动服务"
        return 1
    fi
    
    # 切换到脚本目录
    cd "${SCRIPT_DIR}"
    
    # 前台运行
    python3 "${PYTHON_SCRIPT}"
}

# 显示帮助信息
show_help() {
    echo "使用方法: $0 {start|stop|restart|status|run|help}"
    echo ""
    echo "命令说明:"
    echo "  start    启动服务（后台运行）"
    echo "  stop     停止服务"
    echo "  restart  重启服务"
    echo "  status   查看服务状态"
    echo "  run      前台运行（调试模式）"
    echo "  help     显示此帮助信息"
    echo ""
    echo "文件位置:"
    echo "  配置文件: ${CONFIG_FILE}"
    echo "  日志文件: ${LOG_FILE}"
    echo "  PID 文件: ${PID_FILE}"
}

# 主函数
main() {
    # 创建必要的目录
    create_directories
    
    case "$1" in
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
            check_status
            ;;
        run)
            run_foreground
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo "错误: 未知命令 '$1'"
            show_help
            exit 1
            ;;
    esac
}

# 脚本入口点
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
