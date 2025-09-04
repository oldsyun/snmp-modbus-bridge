# 配置文件指南

本文档详细说明 `config.ini` 配置文件的各个参数和使用方法。

## 📁 配置文件结构

```
config.ini                    # 主配置文件 (INI 格式)
config_loader.py             # 配置加载器 (自动转换为 Python 对象)
```

## 🔧 配置文件格式

配置文件采用标准 INI 格式，具有以下优势：
- 易于阅读和编辑
- 支持注释（使用 # 或 ;）
- 分组管理配置项
- 跨平台兼容

## 📋 配置部分说明

### 1. SNMP 桥接服务配置

```ini
[SNMP_BRIDGE_CONFIG]
listen_ip = 0.0.0.0          # 监听 IP 地址
listen_port = 1161           # 监听端口
community = public           # SNMP 社区字符串
modbus_type = TCP            # Modbus 类型：TCP 或 RTU
timezone_offset = -01        # 时区偏移：+08=UTC+8, -01=UTC-1
startup_delay = 2            # 启动延迟（秒）
error_value = -99998         # 默认错误值
```

**参数说明：**
- `listen_ip`: 服务监听的 IP 地址，`0.0.0.0` 表示监听所有网络接口
- `listen_port`: SNMP 服务端口，标准端口为 161，这里使用 1161 避免权限问题
- `community`: SNMP 社区字符串，用于简单认证
- `modbus_type`: Modbus 连接类型，支持 `TCP` 和 `RTU`
- `timezone_offset`: 时区偏移，格式为 `±HH`，如 `+08`、`-01`
- `startup_delay`: 服务启动延迟时间
- `error_value`: 当 Modbus 通讯失败时返回的错误值

### 2. Modbus TCP 配置

```ini
[MODBUS_TCP_CONFIG]
server_ip = 127.0.0.1        # Modbus TCP 服务器 IP
port = 502                   # Modbus TCP 端口
timeout = 3                  # 连接超时时间（秒）
retry_interval = 10          # 重试间隔（秒）
update_interval = 5          # 更新间隔（秒）
```

### 3. Modbus RTU 配置

```ini
[MODBUS_RTU_CONFIG]
port = COM1                  # 串口端口
baudrate = 9600              # 波特率
bytesize = 8                 # 数据位
parity = N                   # 校验位
stopbits = 1                 # 停止位
timeout = 3                  # 超时时间（秒）
retry_interval = 10          # 重试间隔（秒）
update_interval = 5          # 更新间隔（秒）
```

**串口参数说明：**
- `port`: 串口设备名（Windows: `COM1`, Linux: `/dev/ttyUSB0`）
- `baudrate`: 通讯波特率（常用值：9600, 19200, 38400, 115200）
- `bytesize`: 数据位数（通常为 8）
- `parity`: 校验位（`N`=无校验, `E`=偶校验, `O`=奇校验）
- `stopbits`: 停止位数（通常为 1）

### 4. 系统 OID 配置

系统 OID 提供设备基本信息和状态，格式如下：

```ini
[SYSTEM_OID_<序号>]
oid = <OID 字符串>
description = <描述>
type = <类型>
value = <固定值>             # 仅 fixed_value 类型需要
snmp_data_type = <SNMP 数据类型>
```

**类型说明：**
- `fixed_value`: 固定值，需要配置 `value` 参数
- `uptime`: 系统运行时间，自动计算
- `utc_time`: UTC 时间，根据 `timezone_offset` 生成

**示例：**
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

### 5. 业务 OID 配置

业务 OID 用于读取 Modbus 设备数据，格式如下：

```ini
[SNMP_OID_<序号>]
oid = <OID 字符串>
description = <描述>
register_address = <寄存器地址>    # 十六进制格式，如 0x100
unit_id = <单元 ID>
function_code = <功能码>
data_type = <数据类型>
processing_type = <处理类型>
coefficient = <系数>              # 仅 multiply 类型需要
offset = <偏移量>                 # 仅 multiply 类型需要
decimal_places = <小数位数>       # 仅 multiply 类型需要
snmp_data_type = <SNMP 数据类型>
```

**数据类型说明：**
- `int16`: 有符号 16 位整数 (-32768 到 32767)
- `uint16`: 无符号 16 位整数 (0 到 65535)
- `int32`: 有符号 32 位整数
- `uint32`: 无符号 32 位整数
- `float32`: 32 位浮点数

**处理类型说明：**
- `multiply`: 乘法处理（原值 × 系数 + 偏移量）
- `direct`: 直接映射
- `communication_status`: 通讯状态（固定返回 1，无需 Modbus 读取）

**示例：**
```ini
# 温度传感器（有符号数据，需要缩放）
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

# 设备状态（直接映射）
[SNMP_OID_3]
oid = .1.3.6.1.4.1.41475.3.2.11.21.1.1.10.4.0
description = udFanControlSupplyMode
register_address = 0x102
unit_id = 1
function_code = 3
data_type = uint16
processing_type = direct
snmp_data_type = Integer32

# 通讯状态（无需 Modbus 读取）
[SNMP_OID_4]
oid = .1.3.6.1.4.1.41475.3.2.11.21.1.1.5.0
description = udFanControlStsCommFault
processing_type = communication_status
snmp_data_type = Integer32
```

## 🔄 配置修改和重载

1. **修改配置文件**：直接编辑 `config.ini` 文件
2. **重启服务**：配置修改后需要重启服务生效
3. **验证配置**：可以运行 `python config_loader.py` 测试配置加载

## 🧪 配置测试

```bash
# 测试配置加载
python config_loader.py

# 启动服务
python snmp_modbus_bridge.py

# 测试 SNMP 查询
snmpget -v2c -c public 127.0.0.1:1161 .1.3.6.1.2.1.1.1.0
```

## ⚠️ 注意事项

1. **OID 唯一性**：确保每个 OID 在配置中只出现一次
2. **寄存器地址**：使用十六进制格式（如 `0x100`）
3. **数据类型匹配**：确保 Modbus 数据类型与实际设备匹配
4. **时区格式**：时区偏移必须是 `±HH` 格式
5. **端口权限**：Linux 下使用端口 1161 避免权限问题

## 🔧 故障排除

1. **配置文件语法错误**：检查 INI 格式是否正确
2. **OID 重复**：确保没有重复的 OID 定义
3. **数据类型错误**：检查 Modbus 数据类型配置
4. **网络连接**：确认 Modbus 设备网络连通性

---

**配置文件版本**: 1.0  
**更新日期**: 2025-09-04
