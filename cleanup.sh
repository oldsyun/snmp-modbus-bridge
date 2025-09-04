#!/bin/bash
# =============================================================================
# 清理测试文件脚本
# =============================================================================
#
# 功能：删除开发和测试过程中产生的临时文件
#
# 使用方法：
#   ./cleanup.sh
#
# 作者: SNMP-Modbus Bridge Team
# 版本: 1.0
# 日期: 2025-09-04
# =============================================================================

echo "🧹 清理测试和临时文件..."

# 删除测试脚本
echo "删除测试脚本..."
rm -f test_*.py
rm -f example_usage.py
rm -f snmp_client_test.py

# 删除旧的配置文件
echo "删除旧的配置文件..."
rm -f config.py

# 删除 Python 缓存文件
echo "删除 Python 缓存文件..."
rm -rf __pycache__/
rm -f *.pyc
rm -f *.pyo

# 删除日志文件
echo "删除日志文件..."
rm -rf logs/
rm -f *.log

# 删除临时文件
echo "删除临时文件..."
rm -f *.tmp
rm -f *.bak
rm -f *~
rm -f .DS_Store

# 删除 PID 文件
echo "删除 PID 文件..."
rm -f *.pid
rm -f *.lock

echo "✅ 清理完成！"
echo ""
echo "📁 保留的文件："
echo "  - snmp_modbus_bridge.py    (主服务程序)"
echo "  - config_loader.py         (配置加载器)"
echo "  - config.ini               (Windows 配置文件)"
echo "  - config.linux.ini         (Linux 配置文件)"
echo "  - start.sh                 (启动脚本)"
echo "  - deploy.sh                (部署脚本)"
echo "  - snmp-modbus-bridge.service (systemd 服务文件)"
echo "  - README.md                (说明文档)"
echo "  - CONFIG_GUIDE.md          (配置指南)"
echo "  - LINUX_DEPLOYMENT.md     (Linux 部署指南)"
echo "  - requirements.txt         (依赖列表)"
echo "  - cleanup.sh               (清理脚本)"
