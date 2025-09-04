#!/bin/bash
# =============================================================================
# SNMP-Modbus 桥接服务部署脚本
# =============================================================================
#
# 功能：
# 1. 创建系统用户和目录
# 2. 安装 Python 依赖
# 3. 复制服务文件到系统目录
# 4. 配置 systemd 服务
# 5. 设置权限和防火墙
#
# 使用方法：
#   sudo ./deploy.sh install    # 安装服务
#   sudo ./deploy.sh uninstall  # 卸载服务
#   sudo ./deploy.sh update     # 更新服务文件
#
# 作者: SNMP-Modbus Bridge Team
# 版本: 1.0
# 日期: 2025-09-04
# =============================================================================

# 配置变量
SERVICE_NAME="snmp-modbus-bridge"
SERVICE_USER="snmp-bridge"
SERVICE_GROUP="snmp-bridge"
INSTALL_DIR="/opt/snmp-modbus-bridge"
LOG_DIR="/var/log/snmp-modbus-bridge"
CONFIG_DIR="/etc/snmp-modbus-bridge"
SYSTEMD_DIR="/etc/systemd/system"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 颜色定义
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

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# 检查是否以 root 权限运行
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要 root 权限运行"
        log_info "请使用: sudo $0 $*"
        exit 1
    fi
}

# 检测 Linux 发行版
detect_distro() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        DISTRO=$ID
        VERSION=$VERSION_ID
    else
        log_error "无法检测 Linux 发行版"
        exit 1
    fi
    
    log_info "检测到系统: $PRETTY_NAME"
}

# 安装系统依赖
install_system_deps() {
    log_info "安装系统依赖..."
    
    case $DISTRO in
        ubuntu|debian)
            apt-get update
            apt-get install -y python3 python3-pip python3-venv systemd
            ;;
        centos|rhel|fedora)
            if command -v dnf &> /dev/null; then
                dnf install -y python3 python3-pip systemd
            else
                yum install -y python3 python3-pip systemd
            fi
            ;;
        *)
            log_warn "未知的 Linux 发行版，请手动安装 Python 3 和 systemd"
            ;;
    esac
}

# 安装 Python 依赖
install_python_deps() {
    log_info "安装 Python 依赖..."
    
    # 升级 pip
    python3 -m pip install --upgrade pip
    
    # 安装依赖包
    python3 -m pip install pysnmp pymodbus pyasn1 configparser
    
    # 验证安装
    local required_modules=("pysnmp" "pymodbus" "pyasn1" "configparser")
    for module in "${required_modules[@]}"; do
        if ! python3 -c "import ${module}" &> /dev/null; then
            log_error "Python 模块 ${module} 安装失败"
            return 1
        fi
    done
    
    log_info "Python 依赖安装完成"
}

# 创建系统用户
create_user() {
    log_info "创建系统用户..."
    
    if ! id "${SERVICE_USER}" &>/dev/null; then
        useradd --system --no-create-home --shell /bin/false \
                --home-dir "${INSTALL_DIR}" \
                --comment "SNMP-Modbus Bridge Service" \
                "${SERVICE_USER}"
        log_info "用户 ${SERVICE_USER} 创建成功"
    else
        log_info "用户 ${SERVICE_USER} 已存在"
    fi
}

# 创建目录结构
create_directories() {
    log_info "创建目录结构..."
    
    # 创建安装目录
    mkdir -p "${INSTALL_DIR}"
    mkdir -p "${LOG_DIR}"
    mkdir -p "${CONFIG_DIR}"
    
    # 设置权限
    chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${INSTALL_DIR}"
    chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${LOG_DIR}"
    chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${CONFIG_DIR}"
    
    chmod 755 "${INSTALL_DIR}"
    chmod 755 "${LOG_DIR}"
    chmod 755 "${CONFIG_DIR}"
    
    log_info "目录创建完成"
}

# 复制服务文件
copy_files() {
    log_info "复制服务文件..."
    
    # 复制 Python 文件
    cp "${SCRIPT_DIR}/snmp_modbus_bridge.py" "${INSTALL_DIR}/"
    cp "${SCRIPT_DIR}/config_loader.py" "${INSTALL_DIR}/"
    
    # 复制配置文件
    if [[ -f "${SCRIPT_DIR}/config.ini" ]]; then
        cp "${SCRIPT_DIR}/config.ini" "${CONFIG_DIR}/"
        # 在安装目录创建配置文件链接
        ln -sf "${CONFIG_DIR}/config.ini" "${INSTALL_DIR}/config.ini"
    else
        log_warn "配置文件 config.ini 不存在，请手动创建"
    fi
    
    # 复制启动脚本
    cp "${SCRIPT_DIR}/start.sh" "${INSTALL_DIR}/"
    chmod +x "${INSTALL_DIR}/start.sh"
    
    # 复制文档
    [[ -f "${SCRIPT_DIR}/README.md" ]] && cp "${SCRIPT_DIR}/README.md" "${INSTALL_DIR}/"
    [[ -f "${SCRIPT_DIR}/CONFIG_GUIDE.md" ]] && cp "${SCRIPT_DIR}/CONFIG_GUIDE.md" "${INSTALL_DIR}/"
    
    # 设置权限
    chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${INSTALL_DIR}"
    chmod 644 "${INSTALL_DIR}"/*.py
    chmod 644 "${CONFIG_DIR}/config.ini" 2>/dev/null || true
    
    log_info "文件复制完成"
}

# 安装 systemd 服务
install_systemd_service() {
    log_info "安装 systemd 服务..."
    
    # 复制服务文件
    cp "${SCRIPT_DIR}/snmp-modbus-bridge.service" "${SYSTEMD_DIR}/"
    
    # 重新加载 systemd
    systemctl daemon-reload
    
    # 启用服务
    systemctl enable "${SERVICE_NAME}"
    
    log_info "systemd 服务安装完成"
}

# 配置防火墙
configure_firewall() {
    log_info "配置防火墙..."
    
    # 检查防火墙类型
    if command -v ufw &> /dev/null && ufw status | grep -q "Status: active"; then
        # Ubuntu/Debian UFW
        ufw allow 1161/udp comment "SNMP-Modbus Bridge"
        log_info "UFW 防火墙规则已添加"
    elif command -v firewall-cmd &> /dev/null && systemctl is-active firewalld &> /dev/null; then
        # CentOS/RHEL firewalld
        firewall-cmd --permanent --add-port=1161/udp
        firewall-cmd --reload
        log_info "firewalld 防火墙规则已添加"
    elif command -v iptables &> /dev/null; then
        # 通用 iptables
        iptables -A INPUT -p udp --dport 1161 -j ACCEPT
        log_warn "iptables 规则已添加，但可能不会持久化"
        log_info "请考虑使用 iptables-persistent 或其他方式保存规则"
    else
        log_warn "未检测到防火墙，请手动开放 UDP 1161 端口"
    fi
}

# 安装服务
install_service() {
    log_info "开始安装 ${SERVICE_NAME} 服务..."
    
    detect_distro
    install_system_deps
    install_python_deps
    create_user
    create_directories
    copy_files
    install_systemd_service
    configure_firewall
    
    log_info "服务安装完成！"
    log_info ""
    log_info "使用方法："
    log_info "  启动服务: sudo systemctl start ${SERVICE_NAME}"
    log_info "  停止服务: sudo systemctl stop ${SERVICE_NAME}"
    log_info "  查看状态: sudo systemctl status ${SERVICE_NAME}"
    log_info "  查看日志: sudo journalctl -u ${SERVICE_NAME} -f"
    log_info ""
    log_info "配置文件: ${CONFIG_DIR}/config.ini"
    log_info "日志目录: ${LOG_DIR}"
    log_info "安装目录: ${INSTALL_DIR}"
}

# 卸载服务
uninstall_service() {
    log_info "开始卸载 ${SERVICE_NAME} 服务..."
    
    # 停止并禁用服务
    systemctl stop "${SERVICE_NAME}" 2>/dev/null || true
    systemctl disable "${SERVICE_NAME}" 2>/dev/null || true
    
    # 删除 systemd 服务文件
    rm -f "${SYSTEMD_DIR}/${SERVICE_NAME}.service"
    systemctl daemon-reload
    
    # 删除文件和目录
    rm -rf "${INSTALL_DIR}"
    rm -rf "${LOG_DIR}"
    rm -rf "${CONFIG_DIR}"
    
    # 删除用户
    if id "${SERVICE_USER}" &>/dev/null; then
        userdel "${SERVICE_USER}" 2>/dev/null || true
        log_info "用户 ${SERVICE_USER} 已删除"
    fi
    
    log_info "服务卸载完成"
}

# 更新服务文件
update_service() {
    log_info "更新服务文件..."
    
    # 停止服务
    systemctl stop "${SERVICE_NAME}" 2>/dev/null || true
    
    # 复制新文件
    copy_files
    
    # 重新加载 systemd
    systemctl daemon-reload
    
    # 启动服务
    systemctl start "${SERVICE_NAME}"
    
    log_info "服务更新完成"
}

# 显示帮助信息
show_help() {
    echo "使用方法: $0 {install|uninstall|update|help}"
    echo ""
    echo "命令说明:"
    echo "  install    安装服务到系统"
    echo "  uninstall  从系统卸载服务"
    echo "  update     更新服务文件"
    echo "  help       显示此帮助信息"
    echo ""
    echo "注意: 此脚本需要 root 权限运行"
}

# 主函数
main() {
    check_root
    
    case "$1" in
        install)
            install_service
            ;;
        uninstall)
            uninstall_service
            ;;
        update)
            update_service
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
