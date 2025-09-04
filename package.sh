#!/bin/bash
# =============================================================================
# SNMP-Modbus 桥接服务打包脚本
# =============================================================================
#
# 功能：创建生产环境部署包
#
# 使用方法：
#   ./package.sh
#
# 作者: SNMP-Modbus Bridge Team
# 版本: 1.0
# 日期: 2025-09-04
# =============================================================================

PACKAGE_NAME="snmp-modbus-bridge"
VERSION="1.0"
DATE=$(date +%Y%m%d)
PACKAGE_DIR="${PACKAGE_NAME}-${VERSION}-${DATE}"
ARCHIVE_NAME="${PACKAGE_DIR}.tar.gz"

echo "📦 创建 SNMP-Modbus 桥接服务部署包..."
echo "版本: ${VERSION}"
echo "日期: ${DATE}"
echo ""

# 清理旧的打包目录
rm -rf "${PACKAGE_DIR}"
rm -f "${ARCHIVE_NAME}"

# 创建打包目录
mkdir -p "${PACKAGE_DIR}"

echo "📁 复制核心文件..."

# 复制核心程序文件
cp snmp_modbus_bridge.py "${PACKAGE_DIR}/"
cp config_loader.py "${PACKAGE_DIR}/"

# 复制配置文件
cp config.linux.ini "${PACKAGE_DIR}/config.ini"
cp CONFIG_GUIDE.md "${PACKAGE_DIR}/"

# 复制部署脚本
cp start.sh "${PACKAGE_DIR}/"
cp deploy.sh "${PACKAGE_DIR}/"
cp snmp-modbus-bridge.service "${PACKAGE_DIR}/"

# 复制文档
cp README.md "${PACKAGE_DIR}/"
cp LINUX_DEPLOYMENT.md "${PACKAGE_DIR}/"
cp requirements.txt "${PACKAGE_DIR}/"

# 设置脚本执行权限
chmod +x "${PACKAGE_DIR}/start.sh"
chmod +x "${PACKAGE_DIR}/deploy.sh"

echo "📝 创建版本信息文件..."

# 创建版本信息文件
cat > "${PACKAGE_DIR}/VERSION" << EOF
SNMP-Modbus Bridge Service
Version: ${VERSION}
Build Date: $(date '+%Y-%m-%d %H:%M:%S')
Platform: Linux
Architecture: x86_64

Components:
- snmp_modbus_bridge.py    : Main service program
- config_loader.py         : Configuration loader
- config.ini               : Configuration file
- start.sh                 : Service start script
- deploy.sh                : Deployment script
- snmp-modbus-bridge.service : systemd service file

Documentation:
- README.md                : General documentation
- CONFIG_GUIDE.md          : Configuration guide
- LINUX_DEPLOYMENT.md     : Linux deployment guide
- requirements.txt         : Python dependencies

Support:
- Email: support@company.com
- Documentation: https://github.com/company/snmp-modbus-bridge
EOF

echo "📋 创建安装说明..."

# 创建快速安装说明
cat > "${PACKAGE_DIR}/INSTALL.md" << EOF
# 快速安装指南

## 1. 解压部署包
\`\`\`bash
tar -xzf ${ARCHIVE_NAME}
cd ${PACKAGE_DIR}
\`\`\`

## 2. 运行部署脚本
\`\`\`bash
sudo ./deploy.sh install
\`\`\`

## 3. 配置服务
\`\`\`bash
sudo nano /etc/snmp-modbus-bridge/config.ini
\`\`\`

## 4. 启动服务
\`\`\`bash
sudo systemctl start snmp-modbus-bridge
sudo systemctl enable snmp-modbus-bridge
\`\`\`

## 5. 验证服务
\`\`\`bash
sudo systemctl status snmp-modbus-bridge
snmpget -v2c -c public localhost .1.3.6.1.2.1.1.1.0
\`\`\`

详细说明请参考 LINUX_DEPLOYMENT.md
EOF

echo "🗜️  创建压缩包..."

# 创建压缩包
tar -czf "${ARCHIVE_NAME}" "${PACKAGE_DIR}"

# 计算文件大小和校验和
PACKAGE_SIZE=$(du -h "${ARCHIVE_NAME}" | cut -f1)
PACKAGE_MD5=$(md5sum "${ARCHIVE_NAME}" | cut -d' ' -f1)

echo ""
echo "✅ 打包完成！"
echo ""
echo "📦 部署包信息:"
echo "  文件名: ${ARCHIVE_NAME}"
echo "  大小: ${PACKAGE_SIZE}"
echo "  MD5: ${PACKAGE_MD5}"
echo ""
echo "📁 包含文件:"
ls -la "${PACKAGE_DIR}/"
echo ""
echo "🚀 部署方法:"
echo "  1. 将 ${ARCHIVE_NAME} 上传到目标服务器"
echo "  2. 解压: tar -xzf ${ARCHIVE_NAME}"
echo "  3. 安装: cd ${PACKAGE_DIR} && sudo ./deploy.sh install"
echo ""
echo "📖 详细文档请参考 LINUX_DEPLOYMENT.md"

# 清理临时目录
rm -rf "${PACKAGE_DIR}"

echo ""
echo "🎉 打包完成！部署包已保存为: ${ARCHIVE_NAME}"
