# Linux 部署指南

本文档详细说明如何在 Linux 系统上部署 SNMP-Modbus 桥接服务。

## 📋 系统要求

### 支持的 Linux 发行版
- Ubuntu 18.04+ / Debian 9+
- CentOS 7+ / RHEL 7+
- Fedora 30+
- 其他支持 systemd 的 Linux 发行版

### 系统依赖
- Python 3.6+
- systemd
- 网络访问权限（用于安装 Python 包）

## 🚀 快速部署

### 1. 下载部署包

```bash
# 下载或复制部署文件到服务器
scp -r snmp-modbus-bridge/ user@server:/tmp/
```

### 2. 运行部署脚本

```bash
cd /tmp/snmp-modbus-bridge/
sudo chmod +x deploy.sh start.sh
sudo ./deploy.sh install
```

### 3. 配置服务

```bash
# 编辑配置文件
sudo nano /etc/snmp-modbus-bridge/config.ini

# 启动服务
sudo systemctl start snmp-modbus-bridge
sudo systemctl enable snmp-modbus-bridge
```

## 📁 部署后的文件结构

```
/opt/snmp-modbus-bridge/          # 服务安装目录
├── snmp_modbus_bridge.py         # 主服务程序
├── config_loader.py              # 配置加载器
├── start.sh                      # 启动脚本
├── config.ini -> /etc/snmp-modbus-bridge/config.ini
├── README.md                     # 说明文档
└── CONFIG_GUIDE.md               # 配置指南

/etc/snmp-modbus-bridge/          # 配置目录
└── config.ini                    # 主配置文件

/var/log/snmp-modbus-bridge/      # 日志目录
└── service.log                   # 服务日志

/etc/systemd/system/              # systemd 服务
└── snmp-modbus-bridge.service    # 服务定义文件
```

## 🔧 服务管理

### systemd 命令

```bash
# 启动服务
sudo systemctl start snmp-modbus-bridge

# 停止服务
sudo systemctl stop snmp-modbus-bridge

# 重启服务
sudo systemctl restart snmp-modbus-bridge

# 查看服务状态
sudo systemctl status snmp-modbus-bridge

# 开机自启动
sudo systemctl enable snmp-modbus-bridge

# 禁用开机自启动
sudo systemctl disable snmp-modbus-bridge
```

### 日志查看

```bash
# 查看实时日志
sudo journalctl -u snmp-modbus-bridge -f

# 查看最近日志
sudo journalctl -u snmp-modbus-bridge -n 100

# 查看服务日志文件
sudo tail -f /var/log/snmp-modbus-bridge/service.log
```

### 手动启动脚本

```bash
# 进入安装目录
cd /opt/snmp-modbus-bridge

# 前台运行（调试模式）
sudo -u snmp-bridge ./start.sh run

# 后台启动
sudo -u snmp-bridge ./start.sh start

# 停止服务
sudo -u snmp-bridge ./start.sh stop

# 查看状态
sudo -u snmp-bridge ./start.sh status
```

## ⚙️ 配置说明

### 主要配置文件

配置文件位置：`/etc/snmp-modbus-bridge/config.ini`

```ini
[SNMP_BRIDGE_CONFIG]
listen_ip = 0.0.0.0              # 监听所有网络接口
listen_port = 161                # 标准 SNMP 端口
community = public               # SNMP 社区字符串
modbus_type = TCP                # Modbus 连接类型
timezone_offset = +08            # 时区设置
```

### 网络配置

```bash
# 检查端口占用
sudo netstat -ulnp | grep :161

# 开放防火墙端口（Ubuntu/Debian）
sudo ufw allow 161/udp

# 开放防火墙端口（CentOS/RHEL）
sudo firewall-cmd --permanent --add-port=161/udp
sudo firewall-cmd --reload
```

### 权限配置

服务以专用用户 `snmp-bridge` 运行，具有最小权限：

```bash
# 查看服务用户
id snmp-bridge

# 查看文件权限
ls -la /opt/snmp-modbus-bridge/
ls -la /etc/snmp-modbus-bridge/
ls -la /var/log/snmp-modbus-bridge/
```

## 🧪 测试和验证

### 1. 服务状态检查

```bash
# 检查服务是否运行
sudo systemctl is-active snmp-modbus-bridge

# 检查端口监听
sudo netstat -ulnp | grep :161
```

### 2. SNMP 查询测试

```bash
# 安装 SNMP 工具（如果未安装）
sudo apt-get install snmp-utils  # Ubuntu/Debian
sudo yum install net-snmp-utils  # CentOS/RHEL

# 测试系统描述 OID
snmpget -v2c -c public localhost .1.3.6.1.2.1.1.1.0

# 测试自定义 OID
snmpget -v2c -c public localhost .1.3.6.1.4.1.41475.3.2.3.10.1.1.2.0
```

### 3. Python 测试脚本

```python
#!/usr/bin/env python3
from pysnmp.hlapi import *

def test_snmp_query():
    for (errorIndication, errorStatus, errorIndex, varBinds) in getCmd(
        SnmpEngine(),
        CommunityData('public'),
        UdpTransportTarget(('localhost', 161)),
        ContextData(),
        ObjectType(ObjectIdentity('.1.3.6.1.2.1.1.1.0'))):
        
        if errorIndication:
            print(f'错误: {errorIndication}')
        elif errorStatus:
            print(f'错误: {errorStatus.prettyPrint()}')
        else:
            for varBind in varBinds:
                print(f'系统描述: {varBind[1]}')

if __name__ == "__main__":
    test_snmp_query()
```

## 🔄 更新和维护

### 更新服务

```bash
# 停止服务
sudo systemctl stop snmp-modbus-bridge

# 更新文件
sudo ./deploy.sh update

# 启动服务
sudo systemctl start snmp-modbus-bridge
```

### 备份配置

```bash
# 备份配置文件
sudo cp /etc/snmp-modbus-bridge/config.ini /etc/snmp-modbus-bridge/config.ini.backup

# 备份整个配置目录
sudo tar -czf snmp-modbus-bridge-config-$(date +%Y%m%d).tar.gz /etc/snmp-modbus-bridge/
```

### 日志轮转

创建日志轮转配置：

```bash
sudo tee /etc/logrotate.d/snmp-modbus-bridge << EOF
/var/log/snmp-modbus-bridge/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 snmp-bridge snmp-bridge
    postrotate
        systemctl reload snmp-modbus-bridge || true
    endscript
}
EOF
```

## 🚨 故障排除

### 常见问题

1. **服务启动失败**
   ```bash
   # 查看详细错误信息
   sudo journalctl -u snmp-modbus-bridge -n 50
   
   # 检查配置文件语法
   python3 -c "
   import sys
   sys.path.insert(0, '/opt/snmp-modbus-bridge')
   from config_loader import SNMP_BRIDGE_CONFIG
   print('配置文件正常')
   "
   ```

2. **端口被占用**
   ```bash
   # 查找占用端口的进程
   sudo lsof -i :161
   
   # 修改配置文件中的端口
   sudo nano /etc/snmp-modbus-bridge/config.ini
   ```

3. **权限问题**
   ```bash
   # 重新设置权限
   sudo chown -R snmp-bridge:snmp-bridge /opt/snmp-modbus-bridge
   sudo chown -R snmp-bridge:snmp-bridge /var/log/snmp-modbus-bridge
   ```

4. **Modbus 连接失败**
   ```bash
   # 检查网络连通性
   ping modbus_device_ip
   
   # 检查端口连通性
   telnet modbus_device_ip 502
   ```

### 调试模式

```bash
# 前台运行服务（查看详细日志）
sudo systemctl stop snmp-modbus-bridge
cd /opt/snmp-modbus-bridge
sudo -u snmp-bridge python3 snmp_modbus_bridge.py
```

## 🗑️ 卸载服务

```bash
# 停止并卸载服务
sudo ./deploy.sh uninstall

# 手动清理（如果需要）
sudo rm -rf /opt/snmp-modbus-bridge
sudo rm -rf /etc/snmp-modbus-bridge
sudo rm -rf /var/log/snmp-modbus-bridge
sudo userdel snmp-bridge
```

## 📞 技术支持

如遇问题，请检查：
1. 系统日志：`sudo journalctl -u snmp-modbus-bridge`
2. 服务日志：`/var/log/snmp-modbus-bridge/service.log`
3. 配置文件：`/etc/snmp-modbus-bridge/config.ini`
4. 网络连通性和防火墙设置

---

**Linux 部署版本**: 1.0  
**更新日期**: 2025-09-04
