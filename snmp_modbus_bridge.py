#!/usr/bin/env python3
"""
SNMP-Modbus 桥接服务

本服务实现了 SNMP 和 Modbus 协议之间的桥接功能，允许通过 SNMP 协议
实时访问 Modbus 设备的数据。

主要功能：
1. SNMP 服务器：监听 SNMP 请求并响应
2. Modbus 客户端：连接 Modbus 设备读取数据
3. 数据转换：支持多种数据类型转换和处理
4. 实时响应：每次 SNMP 请求都实时读取 Modbus 数据
5. 错误处理：完善的错误处理和日志记录

支持的功能：
- Modbus TCP/RTU 连接
- 多种 SNMP 数据类型（Integer, OctetString, Gauge, Counter, TimeTicks）
- 多种 Modbus 数据类型（int16, uint16, int32, uint32, float32）
- 系统 OID（设备信息、时间等）
- 业务 OID（传感器数据、设备状态等）
- 时区配置支持
- 配置化 OID 映射

作者: SNMP-Modbus Bridge Team
版本: 1.0
日期: 2025-09-03
"""

# 标准库导入
import time
import datetime
import logging
import bisect

# SNMP 相关库
from pysnmp.carrier.asyncio.dispatch import AsyncioDispatcher
from pysnmp.carrier.asyncio.dgram import udp, udp6
from pyasn1.codec.ber import encoder, decoder
from pysnmp.proto import api

# Modbus 相关库
from pymodbus.client import ModbusTcpClient, ModbusSerialClient
from pymodbus.exceptions import ModbusException

# 本地配置文件
from config_loader import (
    SNMP_OID_MAPPING, MODBUS_TYPE, MODBUS_TCP_CONFIG, MODBUS_RTU_CONFIG,
    SYSTEM_OID_MAPPING, TIMEZONE_CONFIG, SNMP_BRIDGE_CONFIG
)

# ============================================================================
# 日志配置
# ============================================================================
logging.basicConfig(
    level=logging.INFO,  # 日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# 核心类定义
# ============================================================================

class ModbusOIDHandler:
    """
    Modbus OID 处理器

    负责处理 SNMP OID 到 Modbus 寄存器的映射和数据转换。
    每个实例对应一个 OID，包含该 OID 的所有配置信息和处理逻辑。

    主要功能：
    1. 存储 OID 配置信息（寄存器地址、数据类型、处理方式等）
    2. 实时读取 Modbus 数据
    3. 数据类型转换（int16/uint16/int32/uint32/float32）
    4. 数据处理（乘法、直接映射、通讯状态等）
    5. SNMP 数据类型转换
    6. 错误处理和日志记录
    """

    def __init__(self, oid_config):
        """
        初始化 OID 处理器
        
        Args:
            oid_config: 来自 config.py 的 OID 配置
        """
        self.oid_str = oid_config['oid']
        self.name = tuple(int(x) for x in oid_config['oid'].strip('.').split('.'))
        self.description = oid_config['description']
        self.modbus_config = oid_config.get('modbus_config')  # 可能为 None（通讯状态 OID）
        self.data_processing = oid_config['data_processing']
        self.snmp_config = {'data_type': oid_config.get('snmp_data_type', 'Integer32')}
        
        # Modbus 客户端（延迟初始化）
        self.modbus_client = None
        self.last_value = None
        self.last_error = None
        
        logger.info(f"📋 注册 OID: {self.oid_str} -> {self.description}")
        if self.modbus_config is not None:
            logger.info(f"   Modbus: 单元{self.modbus_config['unit_id']}, "
                       f"寄存器0x{self.modbus_config['register_address']:X}, "
                       f"功能码{self.modbus_config['function_code']}")
        else:
            logger.info(f"   Modbus: 无需读取寄存器（通讯状态 OID）")
        logger.info(f"   数据处理: {self.data_processing['type']}")
        logger.info(f"   SNMP类型: {self.snmp_config.get('data_type', 'Integer32')}")

    def __eq__(self, other):
        return self.name == other

    def __ne__(self, other):
        return self.name != other

    def __lt__(self, other):
        return self.name < other

    def __le__(self, other):
        return self.name <= other

    def __gt__(self, other):
        return self.name > other

    def __ge__(self, other):
        return self.name >= other

    def _get_modbus_client(self):
        """获取或创建 Modbus 客户端"""
        if self.modbus_client is None:
            try:
                # 从全局配置中获取 Modbus 连接信息
                if MODBUS_TYPE == 'TCP':
                    modbus_host = MODBUS_TCP_CONFIG['server_ip']
                    modbus_port = MODBUS_TCP_CONFIG['port']
                    timeout = MODBUS_TCP_CONFIG['timeout']

                    self.modbus_client = ModbusTcpClient(
                        host=modbus_host,
                        port=modbus_port,
                        timeout=timeout
                    )
                    logger.debug(f"🔗 创建 Modbus TCP 客户端: {modbus_host}:{modbus_port}")

                elif MODBUS_TYPE == 'RTU':
                    port = MODBUS_RTU_CONFIG['port']
                    baudrate = MODBUS_RTU_CONFIG['baudrate']
                    bytesize = MODBUS_RTU_CONFIG['bytesize']
                    parity = MODBUS_RTU_CONFIG['parity']
                    stopbits = MODBUS_RTU_CONFIG['stopbits']
                    timeout = MODBUS_RTU_CONFIG['timeout']

                    self.modbus_client = ModbusSerialClient(
                        port=port,
                        baudrate=baudrate,
                        bytesize=bytesize,
                        parity=parity,
                        stopbits=stopbits,
                        timeout=timeout
                    )
                    logger.debug(f"🔗 创建 Modbus RTU 客户端: {port} ({baudrate},{bytesize},{parity},{stopbits})")

                else:
                    logger.error(f"❌ 不支持的 Modbus 类型: {MODBUS_TYPE}")
                    return None
            except Exception as e:
                logger.error(f"❌ 创建 Modbus 客户端失败: {e}")
                return None
        return self.modbus_client

    def _read_modbus_value(self):
        """从 Modbus 设备读取原始值"""
        # 如果是通讯状态 OID，不需要读取 Modbus
        if self.modbus_config is None:
            return 1  # 通讯状态固定返回 1（正常）

        client = self._get_modbus_client()
        if client is None:
            return None
            
        try:
            # 连接到 Modbus 设备
            if not client.connected:
                if not client.connect():
                    logger.error(f"❌ Modbus 连接失败: {self.description}")
                    return None
            
            # 读取寄存器
            unit_id = self.modbus_config['unit_id']
            register = self.modbus_config['register_address']
            function_code = self.modbus_config['function_code']

            logger.debug(f"🔍 读取 Modbus: {self.description} "
                        f"(单元{unit_id}, 寄存器0x{register:X}, 功能码{function_code})")
            
            if function_code == 3:  # 读保持寄存器
                result = client.read_holding_registers(register, count=1, device_id=unit_id)
            elif function_code == 4:  # 读输入寄存器
                result = client.read_input_registers(register, count=1, device_id=unit_id)
            elif function_code == 1:  # 读线圈
                result = client.read_coils(register, count=1, device_id=unit_id)
            elif function_code == 2:  # 读离散输入
                result = client.read_discrete_inputs(register, count=1, device_id=unit_id)
            else:
                logger.error(f"❌ 不支持的功能码: {function_code}")
                return None
            
            if result.isError():
                logger.error(f"❌ Modbus 读取错误: {result}")
                return None
            
            # 获取原始值
            if function_code in [1, 2]:  # 布尔值
                raw_value = result.bits[0]
            else:  # 寄存器值
                raw_value = result.registers[0]
            
            logger.debug(f"📥 Modbus 读取成功: {self.description} = {raw_value}")
            return raw_value
            
        except ModbusException as e:
            logger.error(f"❌ Modbus 异常: {self.description} - {e}")
            return None
        except Exception as e:
            logger.error(f"❌ 读取异常: {self.description} - {e}")
            return None

    def _process_value(self, raw_value):
        """处理原始值"""
        if raw_value is None:
            return None

        try:
            # 首先根据数据类型处理原始值
            processed_raw_value = self._convert_raw_data_type(raw_value)

            processing_type = self.data_processing['type']

            if processing_type == 'multiply':
                # 乘法处理
                coefficient = self.data_processing['coefficient']
                offset = self.data_processing['offset']
                processed_value = processed_raw_value * coefficient + offset

                # 小数位处理
                decimal_places = self.data_processing.get('decimal_places', 0)
                if decimal_places > 0:
                    processed_value = round(processed_value, decimal_places)

                logger.debug(f"🔄 数据处理: {raw_value} → {processed_raw_value} × {coefficient} + {offset} = {processed_value}")

            elif processing_type == 'direct':
                # 直接映射
                processed_value = processed_raw_value
                logger.debug(f"➡️  直接映射: {raw_value} → {processed_raw_value}")

            elif processing_type == 'communication_status':
                # 通讯状态（固定返回1表示正常）
                processed_value = 1
                logger.debug(f"📡 通讯状态: {processed_value}")

            else:
                logger.warning(f"⚠️  未知处理类型: {processing_type}")
                processed_value = processed_raw_value

            return processed_value

        except Exception as e:
            logger.error(f"❌ 数据处理异常: {self.description} - {e}")
            return None

    def _convert_raw_data_type(self, raw_value):
        """根据配置的数据类型转换原始值"""
        if self.modbus_config is None:
            return raw_value

        try:
            data_type = self.modbus_config.get('data_type', 'uint16')

            if data_type == 'int16':
                # 有符号 16 位整数 (-32768 到 32767)
                if raw_value > 32767:
                    converted_value = raw_value - 65536
                else:
                    converted_value = raw_value
                logger.debug(f"📊 数据类型转换 (int16): {raw_value} → {converted_value}")

            elif data_type == 'uint16':
                # 无符号 16 位整数 (0 到 65535)
                converted_value = raw_value
                logger.debug(f"📊 数据类型转换 (uint16): {raw_value} → {converted_value}")

            elif data_type == 'int32':
                # 有符号 32 位整数（需要读取两个寄存器）
                # 这里假设 raw_value 已经是组合后的 32 位值
                if raw_value > 2147483647:
                    converted_value = raw_value - 4294967296
                else:
                    converted_value = raw_value
                logger.debug(f"📊 数据类型转换 (int32): {raw_value} → {converted_value}")

            elif data_type == 'uint32':
                # 无符号 32 位整数
                converted_value = raw_value
                logger.debug(f"📊 数据类型转换 (uint32): {raw_value} → {converted_value}")

            elif data_type == 'float32':
                # 32 位浮点数（需要特殊处理）
                # 这里假设 raw_value 是已经转换的浮点数
                converted_value = float(raw_value)
                logger.debug(f"📊 数据类型转换 (float32): {raw_value} → {converted_value}")

            else:
                # 默认按 uint16 处理
                converted_value = raw_value
                logger.debug(f"📊 数据类型转换 (默认 uint16): {raw_value} → {converted_value}")

            return converted_value

        except Exception as e:
            logger.error(f"❌ 数据类型转换异常: {self.description} - {e}")
            return raw_value

    def _convert_to_snmp_value(self, processed_value, proto_ver):
        """将处理后的值转换为 SNMP 值"""
        if processed_value is None:
            # 返回 Modbus 通讯中断错误代码
            return api.PROTOCOL_MODULES[proto_ver].Integer(-99998)
        
        try:
            snmp_data_type = self.snmp_config.get('data_type', 'Integer32')
            scale_factor = self.snmp_config.get('scale_factor', 1)
            
            if snmp_data_type == 'Integer32':
                if isinstance(processed_value, float):
                    int_value = int(processed_value * scale_factor)
                    snmp_value = api.PROTOCOL_MODULES[proto_ver].Integer(int_value)
                    logger.debug(f"🔄 SNMP转换: {processed_value} × {scale_factor} = {int_value} (Integer)")
                else:
                    snmp_value = api.PROTOCOL_MODULES[proto_ver].Integer(int(processed_value))
                    logger.debug(f"🔄 SNMP转换: {processed_value} → {int(processed_value)} (Integer)")
                    
            elif snmp_data_type == 'OctetString':
                if isinstance(processed_value, float):
                    str_value = f"{processed_value:.2f}"
                    snmp_value = api.PROTOCOL_MODULES[proto_ver].OctetString(str_value)
                    logger.debug(f"🔄 SNMP转换: {processed_value} → '{str_value}' (OctetString)")
                else:
                    str_value = str(processed_value)
                    snmp_value = api.PROTOCOL_MODULES[proto_ver].OctetString(str_value)
                    logger.debug(f"🔄 SNMP转换: {processed_value} → '{str_value}' (OctetString)")
                    
            elif snmp_data_type == 'Gauge32':
                if isinstance(processed_value, float):
                    int_value = int(processed_value * scale_factor)
                    snmp_value = api.PROTOCOL_MODULES[proto_ver].Gauge(int_value)
                    logger.debug(f"🔄 SNMP转换: {processed_value} × {scale_factor} = {int_value} (Gauge)")
                else:
                    snmp_value = api.PROTOCOL_MODULES[proto_ver].Gauge(int(processed_value))
                    logger.debug(f"🔄 SNMP转换: {processed_value} → {int(processed_value)} (Gauge)")

            elif snmp_data_type == 'Counter32':
                if isinstance(processed_value, float):
                    int_value = int(processed_value * scale_factor)
                    snmp_value = api.PROTOCOL_MODULES[proto_ver].Counter(int_value)
                    logger.debug(f"🔄 SNMP转换: {processed_value} × {scale_factor} = {int_value} (Counter)")
                else:
                    snmp_value = api.PROTOCOL_MODULES[proto_ver].Counter(int(processed_value))
                    logger.debug(f"🔄 SNMP转换: {processed_value} → {int(processed_value)} (Counter)")
            else:
                # 默认使用 Integer
                snmp_value = api.PROTOCOL_MODULES[proto_ver].Integer(int(processed_value))
                logger.debug(f"🔄 SNMP转换: 未知类型，使用默认 Integer: {processed_value} → {int(processed_value)}")
            
            return snmp_value
            
        except Exception as e:
            logger.error(f"❌ SNMP 值转换异常: {self.description} - {e}")
            return api.PROTOCOL_MODULES[proto_ver].Integer(-99998)  # Modbus 通讯中断错误代码

    def __call__(self, proto_ver):
        """
        SNMP 回调函数：当收到对此 OID 的请求时调用
        实时从 Modbus 设备读取数据并返回
        """
        logger.info(f"🔍 SNMP 请求: {self.description} ({self.oid_str})")
        
        # 从 Modbus 设备读取原始值
        raw_value = self._read_modbus_value()
        
        # 处理数据
        processed_value = self._process_value(raw_value)
        
        # 转换为 SNMP 值
        snmp_value = self._convert_to_snmp_value(processed_value, proto_ver)
        
        # 缓存结果
        self.last_value = processed_value
        if processed_value is None:
            self.last_error = f"读取失败: {raw_value}"
        else:
            self.last_error = None
        
        logger.info(f"✅ SNMP 响应: {self.description} = {processed_value} "
                   f"(原值: {raw_value})")
        
        return snmp_value

    def cleanup(self):
        """清理资源"""
        if self.modbus_client and self.modbus_client.connected:
            self.modbus_client.close()
            logger.debug(f"🔌 关闭 Modbus 连接: {self.description}")


# 系统 OID 处理器（基于配置的通用处理器）
class SystemOIDHandler:
    """处理系统 OID 和固定值 OID"""

    def __init__(self, oid_config):
        """
        初始化系统 OID 处理器

        Args:
            oid_config: 来自 config.py 的系统 OID 配置
        """
        self.oid_str = oid_config['oid']
        self.name = tuple(int(x) for x in oid_config['oid'].strip('.').split('.'))
        self.description = oid_config['description']
        self.oid_type = oid_config['type']
        self.snmp_data_type = oid_config['snmp_data_type']

        # 固定值类型的配置
        if self.oid_type == 'fixed_value':
            self.value = oid_config['value']
        elif self.oid_type == 'uptime':
            self.birthday = time.time()

        logger.info(f"📋 注册系统 OID: {self.oid_str} -> {self.description}")
        logger.info(f"   类型: {self.oid_type}")
        logger.info(f"   SNMP数据类型: {self.snmp_data_type}")
        if self.oid_type == 'fixed_value':
            logger.info(f"   固定值: {self.value}")

    def __eq__(self, other): return self.name == other
    def __ne__(self, other): return self.name != other
    def __lt__(self, other): return self.name < other
    def __le__(self, other): return self.name <= other
    def __gt__(self, other): return self.name > other
    def __ge__(self, other): return self.name >= other

    def __call__(self, proto_ver):
        """
        SNMP 回调函数：返回配置的固定值或计算值
        """
        logger.debug(f"🔍 系统 OID 请求: {self.description} ({self.oid_str})")

        try:
            if self.oid_type == 'fixed_value':
                # 返回固定值
                if self.snmp_data_type == 'OctetString':
                    snmp_value = api.PROTOCOL_MODULES[proto_ver].OctetString(str(self.value))
                elif self.snmp_data_type == 'Integer':
                    snmp_value = api.PROTOCOL_MODULES[proto_ver].Integer(int(self.value))
                else:
                    # 默认使用 OctetString
                    snmp_value = api.PROTOCOL_MODULES[proto_ver].OctetString(str(self.value))

                logger.debug(f"✅ 系统 OID 响应: {self.description} = {self.value}")

            elif self.oid_type == 'uptime':
                # 计算运行时间
                uptime_ticks = int((time.time() - self.birthday) * 100)
                snmp_value = api.PROTOCOL_MODULES[proto_ver].TimeTicks(uptime_ticks)

                logger.debug(f"✅ 系统 OID 响应: {self.description} = {uptime_ticks} ticks")

            elif self.oid_type == 'utc_time':
                # 返回 UTC 时间格式：YYYYMMDDTHHMMSSZ+08，举例20100607T152000+08
                # 根据配置的时区偏移生成时间字符串

                # 获取时区偏移配置
                timezone_offset = TIMEZONE_CONFIG.get('timezone_offset', '+00')

                # 解析时区偏移
                if timezone_offset.startswith('+') or timezone_offset.startswith('-'):
                    sign = 1 if timezone_offset[0] == '+' else -1
                    hours = int(timezone_offset[1:3])
                    offset_minutes = sign * hours * 60
                else:
                    offset_minutes = 0

                # 创建时区对象
                target_timezone = datetime.timezone(datetime.timedelta(minutes=offset_minutes))

                # 获取当前时间并转换到目标时区
                utc_now = datetime.datetime.now(datetime.timezone.utc)
                local_time = utc_now.astimezone(target_timezone)

                # 生成时间字符串：YYYYMMDDTHHMMSS+时区偏移
                time_str = local_time.strftime('%Y%m%dT%H%M%S')
                utc_time_str = f"{time_str}{timezone_offset}"

                snmp_value = api.PROTOCOL_MODULES[proto_ver].OctetString(utc_time_str)

                logger.debug(f"✅ 系统 OID 响应: {self.description} = {utc_time_str} (时区: {timezone_offset})")

            else:
                # 未知类型，返回错误
                logger.error(f"❌ 未知的系统 OID 类型: {self.oid_type}")
                snmp_value = api.PROTOCOL_MODULES[proto_ver].OctetString("Unknown Type")

            return snmp_value

        except Exception as e:
            logger.error(f"❌ 系统 OID 处理异常: {self.description} - {e}")
            return api.PROTOCOL_MODULES[proto_ver].OctetString("Error")


def create_mib_handlers():
    """根据配置创建 MIB 处理器"""
    handlers = []

    # 添加系统 OID 处理器（基于配置）
    for oid_config in SYSTEM_OID_MAPPING:
        try:
            handler = SystemOIDHandler(oid_config)
            handlers.append(handler)
        except Exception as e:
            logger.error(f"❌ 创建系统 OID 处理器失败: {oid_config.get('oid', 'unknown')} - {e}")

    # 添加 Modbus OID 处理器
    for oid_config in SNMP_OID_MAPPING:
        try:
            handler = ModbusOIDHandler(oid_config)
            handlers.append(handler)
        except Exception as e:
            logger.error(f"❌ 创建 Modbus OID 处理器失败: {oid_config.get('oid', 'unknown')} - {e}")

    # 按 OID 排序
    handlers.sort(key=lambda x: x.name)

    logger.info(f"📋 成功创建 {len(handlers)} 个 OID 处理器")
    logger.info(f"   - 系统 OID: {len(SYSTEM_OID_MAPPING)} 个")
    logger.info(f"   - Modbus OID: {len([h for h in handlers if isinstance(h, ModbusOIDHandler)])} 个")
    return handlers


def snmp_callback(transport_dispatcher, transport_domain, transport_address, whole_msg):
    """SNMP 请求回调函数"""
    logger.debug(f"📨 收到 SNMP 请求: {transport_address}")
    
    while whole_msg:
        msg_ver = api.decodeMessageVersion(whole_msg)
        if msg_ver in api.PROTOCOL_MODULES:
            p_mod = api.PROTOCOL_MODULES[msg_ver]
        else:
            logger.error(f"❌ 不支持的 SNMP 版本: {msg_ver}")
            return
        
        req_msg, whole_msg = decoder.decode(whole_msg, asn1Spec=p_mod.Message())
        rsp_msg = p_mod.apiMessage.get_response(req_msg)
        rsp_pdu = p_mod.apiMessage.get_pdu(rsp_msg)
        req_pdu = p_mod.apiMessage.get_pdu(req_msg)
        var_binds = []
        pending_errors = []
        error_index = 0
        
        # 处理 GETNEXT PDU
        if req_pdu.isSameTypeWith(p_mod.GetNextRequestPDU()):
            logger.debug("🔍 处理 GETNEXT 请求")
            for oid, val in p_mod.apiPDU.get_varbinds(req_pdu):
                error_index += 1
                next_idx = bisect.bisect(mib_handlers, oid)
                if next_idx == len(mib_handlers):
                    var_binds.append((oid, val))
                    pending_errors.append((p_mod.apiPDU.set_end_of_mib_error, error_index))
                else:
                    handler = mib_handlers[next_idx]
                    var_binds.append((handler.name, handler(msg_ver)))
        
        # 处理 GET PDU
        elif req_pdu.isSameTypeWith(p_mod.GetRequestPDU()):
            logger.debug("🔍 处理 GET 请求")
            for oid, val in p_mod.apiPDU.get_varbinds(req_pdu):
                error_index += 1
                if oid in mib_handlers_idx:
                    handler = mib_handlers_idx[oid]
                    var_binds.append((oid, handler(msg_ver)))
                else:
                    logger.warning(f"⚠️  未找到 OID: {oid}")
                    # 返回未定义 OID 错误代码 -99997
                    undefined_value = api.PROTOCOL_MODULES[msg_ver].Integer(-99997)
                    var_binds.append((oid, undefined_value))
        else:
            logger.error("❌ 不支持的请求类型")
            p_mod.apiPDU.set_error_status(rsp_pdu, "genErr")
        
        p_mod.apiPDU.set_varbinds(rsp_pdu, var_binds)
        
        # 提交错误索引到响应 PDU
        for f, i in pending_errors:
            f(rsp_pdu, i)
        
        transport_dispatcher.send_message(
            encoder.encode(rsp_msg), transport_domain, transport_address
        )
    
    return whole_msg


# ============================================================================
# 主函数和服务启动
# ============================================================================

def main():
    """
    主函数 - 启动 SNMP-Modbus 桥接服务

    功能：
    1. 初始化 MIB 处理器
    2. 创建 SNMP 传输调度器
    3. 注册 UDP 传输（IPv4/IPv6）
    4. 启动服务并处理异常
    5. 优雅关闭和资源清理
    """
    global mib_handlers, mib_handlers_idx

    logger.info("🚀 启动 SNMP-Modbus 桥接服务")

    # 从配置文件获取监听参数
    listen_ip = SNMP_BRIDGE_CONFIG.get('listen_ip', '0.0.0.0')
    listen_port = SNMP_BRIDGE_CONFIG.get('listen_port', 1161)

    # 创建 MIB 处理器
    mib_handlers = create_mib_handlers()
    mib_handlers_idx = {handler.name: handler for handler in mib_handlers}

    # 创建传输调度器
    transport_dispatcher = AsyncioDispatcher()
    transport_dispatcher.register_recv_callback(snmp_callback)

    # 注册 UDP/IPv4 传输
    transport_dispatcher.register_transport(
        udp.DOMAIN_NAME,
        udp.UdpAsyncioTransport().open_server_mode((listen_ip, listen_port))
    )

    # 注册 UDP/IPv6 传输（可选）
    try:
        transport_dispatcher.register_transport(
            udp6.DOMAIN_NAME,
            udp6.Udp6AsyncioTransport().open_server_mode(("::", listen_port))
        )
        logger.debug("✅ IPv6 传输注册成功")
    except Exception as e:
        logger.warning(f"⚠️  IPv6 传输注册失败: {e}")

    transport_dispatcher.job_started(1)
    
    # 显示服务启动信息
    logger.info("🎯 SNMP-Modbus 桥接服务已启动")
    logger.info(f"📡 监听地址: {listen_ip}:{listen_port} (UDP)")
    logger.info(f"🔗 Modbus 类型: {MODBUS_TYPE}")
    if MODBUS_TYPE == 'TCP':
        logger.info(f"🔗 Modbus 服务器: {MODBUS_TCP_CONFIG['server_ip']}:{MODBUS_TCP_CONFIG['port']}")
    else:
        logger.info(f"🔗 Modbus 串口: {MODBUS_RTU_CONFIG['port']} ({MODBUS_RTU_CONFIG['baudrate']})")

    logger.info("🔗 支持的 OID:")
    for handler in mib_handlers:
        if hasattr(handler, 'description'):
            logger.info(f"   {'.'.join(map(str, handler.name))} -> {handler.description}")
        else:
            logger.info(f"   {'.'.join(map(str, handler.name))} -> 系统信息")
    
    try:
        # 运行调度器
        transport_dispatcher.run_dispatcher()
    except KeyboardInterrupt:
        logger.info("🛑 收到中断信号，正在关闭...")
    except Exception as e:
        logger.error(f"❌ 运行异常: {e}")
    finally:
        # 清理资源
        for handler in mib_handlers:
            if hasattr(handler, 'cleanup'):
                handler.cleanup()
        transport_dispatcher.close_dispatcher()
        logger.info("✅ SNMP-Modbus 桥接服务已关闭")


# ============================================================================
# 程序入口点
# ============================================================================

if __name__ == "__main__":
    """
    程序入口点

    直接运行此脚本将启动 SNMP-Modbus 桥接服务。
    确保在运行前已正确配置 config.py 文件。

    使用方法：
        python snmp_modbus_bridge.py

    停止服务：
        Ctrl+C 或发送 SIGINT 信号
    """
    main()
