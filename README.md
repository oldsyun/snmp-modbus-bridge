# SNMP-Modbus 桥接服务

一个高性能的 SNMP-Modbus 协议桥接服务，允许通过 SNMP 协议实时访问 Modbus 设备的数据。

## 🚀 功能特性

### 核心功能
- **实时数据桥接**：每次 SNMP 请求都实时读取 Modbus 数据
- **多协议支持**：支持 Modbus TCP 和 RTU 连接
- **配置化管理**：通过配置文件管理所有 OID 映射
- **多数据类型**：支持多种 Modbus 和 SNMP 数据类型转换

### 支持的数据类型

#### Modbus 数据类型
- `int16`：有符号 16 位整数 (-32768 到 32767)
- `uint16`：无符号 16 位整数 (0 到 65535)
- `int32`：有符号 32 位整数
- `uint32`：无符号 32 位整数
- `float32`：32 位浮点数

#### SNMP 数据类型
- `Integer`：整数类型
- `OctetString`：字符串类型
- `Gauge`：仪表类型
- `Counter`：计数器类型
- `TimeTicks`：时间戳类型

### 数据处理方式
- **multiply**：乘法处理（原值 × 系数 + 偏移量）
- **direct**：直接映射
- **communication_status**：通讯状态（固定返回 1）

## 📁 文件结构

```
SNMP-Modbus-Bridge/
├── snmp_modbus_bridge.py    # 主服务程序
├── config.ini               # 配置文件 (INI 格式)
├── config_loader.py         # 配置加载器
├── README.md                # 说明文档
├── test_*.py                # 测试脚本
└── requirements.txt         # 依赖包列表
```

## 🛠️ 安装和配置

### 1. 安装依赖

```bash
pip install pysnmp pymodbus pyasn1
```

### 2. 配置文件说明

配置文件采用 INI 格式 (`config.ini`)，便于阅读和修改。

#### SNMP 桥接服务配置

```ini
[SNMP_BRIDGE_CONFIG]
# SNMP 服务器配置
listen_ip = 0.0.0.0
listen_port = 1161
community = public

# Modbus 连接类型：TCP 或 RTU
modbus_type = TCP

# 时区偏移配置：+08 表示 UTC+8，-01 表示 UTC-1
timezone_offset = -01

# 其他配置
startup_delay = 2
error_value = -99998
```

#### Modbus TCP 配置

```ini
[MODBUS_TCP_CONFIG]
server_ip = 127.0.0.1
port = 502
timeout = 3
retry_interval = 10
update_interval = 5
```

#### Modbus RTU 配置

```ini
[MODBUS_RTU_CONFIG]
port = COM1                    # Windows: COM1, Linux: /dev/ttyUSB0
baudrate = 9600
bytesize = 8
parity = N                     # N=无校验, E=偶校验, O=奇校验
stopbits = 1
timeout = 3
retry_interval = 10
update_interval = 5
```

### 3. OID 映射配置

#### 系统 OID 配置

```ini
[SYSTEM_OID_1]
oid = .1.3.6.1.2.1.1.1.0
description = System Description
type = fixed_value
value = SNMP-Modbus Bridge v1.0
snmp_data_type = OctetString

[SYSTEM_OID_5]
oid = .1.3.6.1.4.1.41475.3.2.11.1.4.0
description = udSystemTime
type = utc_time
snmp_data_type = OctetString
```

#### 业务 OID 配置

```ini
[SNMP_OID_1]
oid = .1.3.6.1.4.1.41475.3.2.3.10.1.1.2.0
description = temp
register_address = 0x100
unit_id = 1
function_code = 3
data_type = int16
processing_type = multiply
coefficient = 0.1
offset = 0
decimal_places = 1
snmp_data_type = OctetString
```

## 🚀 使用方法

### 1. 启动服务

```bash
python snmp_modbus_bridge.py
```

### 2. 测试 SNMP 查询

使用 SNMP 客户端工具查询：

```bash
# 查询温度数据
snmpget -v2c -c public 127.0.0.1:1161 .1.3.6.1.4.1.41475.3.2.3.10.1.1.2.0

# 查询系统时间
snmpget -v2c -c public 127.0.0.1:1161 .1.3.6.1.4.1.41475.3.2.11.1.4.0
```

### 3. 使用 Python 客户端

```python
from pysnmp.hlapi import *

for (errorIndication, errorStatus, errorIndex, varBinds) in getCmd(
    SnmpEngine(),
    CommunityData('public'),
    UdpTransportTarget(('127.0.0.1', 1161)),
    ContextData(),
    ObjectType(ObjectIdentity('.1.3.6.1.4.1.41475.3.2.3.10.1.1.2.0'))):
    
    if errorIndication:
        print(f'错误: {errorIndication}')
    elif errorStatus:
        print(f'错误: {errorStatus.prettyPrint()}')
    else:
        for varBind in varBinds:
            print(f'温度: {varBind[1]}°C')
```

## 📊 数据流程

```
SNMP 请求 → OID 解析 → Modbus 读取 → 数据类型转换 → 数据处理 → SNMP 响应
```

### 详细流程

1. **SNMP 请求接收**：服务监听 SNMP GET/GETNEXT 请求
2. **OID 匹配**：根据请求的 OID 查找对应的处理器
3. **Modbus 连接**：建立或复用 Modbus 连接
4. **数据读取**：从指定寄存器读取原始数据
5. **数据类型转换**：根据配置转换数据类型（如 int16 有符号转换）
6. **数据处理**：应用处理规则（乘法、偏移等）
7. **SNMP 转换**：转换为 SNMP 数据类型
8. **响应发送**：返回处理后的数据

## 🔧 错误代码

- **-99997**：未定义的 OID
- **-99998**：Modbus 通讯中断或读取失败

## 📝 日志说明

服务运行时会输出详细的日志信息：

```
2025-09-03 14:34:04,123 - INFO - 🚀 启动 SNMP-Modbus 桥接服务
2025-09-03 14:34:04,124 - INFO - 📋 注册 OID: .1.3.6.1.4.1.41475.3.2.3.10.1.1.2.0 -> temp
2025-09-03 14:34:04,125 - INFO - 🎯 SNMP-Modbus 桥接服务已启动
2025-09-03 14:34:10,456 - INFO - 🔍 SNMP 请求: temp (.1.3.6.1.4.1.41475.3.2.3.10.1.1.2.0)
2025-09-03 14:34:10,457 - DEBUG - 📥 Modbus 读取成功: temp = 27495
2025-09-03 14:34:10,458 - DEBUG - 📊 数据类型转换 (int16): 27495 → 27495
2025-09-03 14:34:10,459 - DEBUG - 🔄 数据处理: 27495 × 0.1 + 0 = 2749.5
2025-09-03 14:34:10,460 - INFO - ✅ SNMP 响应: temp = 2749.5°C (原值: 27495)
```

## 🧪 测试脚本

项目包含多个测试脚本：

- `test_data_types.py`：测试数据类型转换
- `test_timezone_config.py`：测试时区配置
- `test_fixed_oids.py`：测试固定值 OID
- `snmp_client_test.py`：SNMP 客户端测试

## 📋 配置示例

### 温度传感器配置

```ini
[SNMP_OID_1]
oid = .1.3.6.1.4.1.41475.3.2.3.10.1.1.2.0
description = temp
register_address = 0x100
unit_id = 1
function_code = 3
data_type = int16                    # 有符号 16 位
processing_type = multiply
coefficient = 0.1                    # 缩放系数
offset = 0
decimal_places = 1
snmp_data_type = OctetString
```

### 湿度传感器配置

```ini
[SNMP_OID_2]
oid = .1.3.6.1.4.1.41475.3.2.3.10.1.1.3.0
description = humidity
register_address = 0x101
unit_id = 1
function_code = 3
data_type = uint16                   # 无符号 16 位
processing_type = multiply
coefficient = 0.01                   # 缩放系数
offset = 0
decimal_places = 2
snmp_data_type = OctetString
```

## 🔍 故障排除

### 常见问题

1. **端口被占用**
   - 修改 `SNMP_CONFIG['listen_port']` 为其他端口

2. **Modbus 连接失败**
   - 检查 Modbus 设备 IP 和端口
   - 确认网络连通性

3. **权限问题**
   - Linux 下使用 1161 端口避免权限问题
   - 或使用 sudo 运行

4. **数据格式错误**
   - 检查 `data_type` 配置是否正确
   - 确认 Modbus 寄存器地址

## 📞 技术支持

如有问题，请检查：
1. 配置文件语法是否正确
2. Modbus 设备是否正常运行
3. 网络连接是否正常
4. 日志输出的错误信息

## 📄 许可证

本项目采用 MIT 许可证。

---

**SNMP-Modbus Bridge Team**  
版本: 1.0  
日期: 2025-09-03
