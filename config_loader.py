#!/usr/bin/env python3
"""
配置文件加载器

从 config.ini 文件加载配置并转换为 Python 对象格式，
保持与原有代码的兼容性。

作者: SNMP-Modbus Bridge Team
版本: 1.0
日期: 2025-09-03
"""

import configparser
import os
from typing import Dict, List, Any

class ConfigLoader:
    """配置文件加载器"""
    
    def __init__(self, config_file='config.ini'):
        """
        初始化配置加载器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"配置文件不存在: {self.config_file}")
        
        self.config.read(self.config_file, encoding='utf-8')
    
    def get_snmp_bridge_config(self) -> Dict[str, Any]:
        """获取 SNMP 桥接配置"""
        section = 'SNMP_BRIDGE_CONFIG'
        if section not in self.config:
            raise ValueError(f"配置文件中缺少 [{section}] 部分")
        
        config = dict(self.config[section])
        
        # 类型转换
        config['listen_port'] = int(config.get('listen_port', 1161))
        config['startup_delay'] = int(config.get('startup_delay', 2))
        config['error_value'] = int(config.get('error_value', -99998))
        
        return config
    
    def get_modbus_tcp_config(self) -> Dict[str, Any]:
        """获取 Modbus TCP 配置"""
        section = 'MODBUS_TCP_CONFIG'
        if section not in self.config:
            raise ValueError(f"配置文件中缺少 [{section}] 部分")
        
        config = dict(self.config[section])
        
        # 类型转换
        config['port'] = int(config.get('port', 502))
        config['timeout'] = int(config.get('timeout', 3))
        config['retry_interval'] = int(config.get('retry_interval', 10))
        config['update_interval'] = int(config.get('update_interval', 5))
        
        return config
    
    def get_modbus_rtu_config(self) -> Dict[str, Any]:
        """获取 Modbus RTU 配置"""
        section = 'MODBUS_RTU_CONFIG'
        if section not in self.config:
            raise ValueError(f"配置文件中缺少 [{section}] 部分")
        
        config = dict(self.config[section])
        
        # 类型转换
        config['baudrate'] = int(config.get('baudrate', 9600))
        config['bytesize'] = int(config.get('bytesize', 8))
        config['stopbits'] = int(config.get('stopbits', 1))
        config['timeout'] = int(config.get('timeout', 3))
        config['retry_interval'] = int(config.get('retry_interval', 10))
        config['update_interval'] = int(config.get('update_interval', 5))
        
        return config
    
    def get_system_oid_mapping(self) -> List[Dict[str, Any]]:
        """获取系统 OID 映射配置"""
        system_oids = []
        
        # 查找所有 SYSTEM_OID_* 部分
        for section_name in self.config.sections():
            if section_name.startswith('SYSTEM_OID_'):
                section = self.config[section_name]
                oid_config = {
                    'oid': section.get('oid'),
                    'description': section.get('description'),
                    'type': section.get('type'),
                    'snmp_data_type': section.get('snmp_data_type', 'OctetString')
                }
                
                # 如果是固定值类型，添加 value 字段
                if oid_config['type'] == 'fixed_value':
                    value = section.get('value')
                    # 尝试转换为整数，如果失败则保持字符串
                    try:
                        if oid_config['snmp_data_type'] == 'Integer':
                            oid_config['value'] = int(value)
                        else:
                            oid_config['value'] = value
                    except (ValueError, TypeError):
                        oid_config['value'] = value
                
                system_oids.append(oid_config)
        
        # 按 OID 排序
        system_oids.sort(key=lambda x: x['oid'])
        return system_oids
    
    def get_snmp_oid_mapping(self) -> List[Dict[str, Any]]:
        """获取 SNMP OID 映射配置"""
        snmp_oids = []
        
        # 查找所有 SNMP_OID_* 部分
        for section_name in self.config.sections():
            if section_name.startswith('SNMP_OID_'):
                section = self.config[section_name]
                
                oid_config = {
                    'oid': section.get('oid'),
                    'description': section.get('description'),
                    'snmp_data_type': section.get('snmp_data_type', 'OctetString')
                }
                
                # Modbus 配置
                processing_type = section.get('processing_type')
                if processing_type != 'communication_status':
                    # 需要 Modbus 读取的 OID
                    register_address = section.get('register_address')
                    if register_address:  # 只有当存在寄存器地址时才添加 modbus_config
                        modbus_config = {
                            'register_address': int(register_address, 16),
                            'unit_id': int(section.get('unit_id', 1)),
                            'function_code': int(section.get('function_code', 3)),
                            'data_type': section.get('data_type', 'uint16')
                        }
                        oid_config['modbus_config'] = modbus_config
                
                # 数据处理配置
                data_processing = {
                    'type': processing_type
                }
                
                if processing_type == 'multiply':
                    data_processing.update({
                        'coefficient': float(section.get('coefficient', 1.0)),
                        'offset': float(section.get('offset', 0.0)),
                        'decimal_places': int(section.get('decimal_places', 0))
                    })
                
                oid_config['data_processing'] = data_processing
                snmp_oids.append(oid_config)
        
        # 按 OID 排序
        snmp_oids.sort(key=lambda x: x['oid'])
        return snmp_oids

# 全局配置加载器实例
_config_loader = ConfigLoader()

# 导出配置变量（保持与原有代码的兼容性）
SNMP_BRIDGE_CONFIG = _config_loader.get_snmp_bridge_config()
MODBUS_TYPE = SNMP_BRIDGE_CONFIG['modbus_type']
MODBUS_TCP_CONFIG = _config_loader.get_modbus_tcp_config()
MODBUS_RTU_CONFIG = _config_loader.get_modbus_rtu_config()
SYSTEM_OID_MAPPING = _config_loader.get_system_oid_mapping()
SNMP_OID_MAPPING = _config_loader.get_snmp_oid_mapping()

# 时区配置（从 SNMP_BRIDGE_CONFIG 中提取）
TIMEZONE_CONFIG = {
    'timezone_offset': SNMP_BRIDGE_CONFIG['timezone_offset'],
    'timezone_name': 'Custom Timezone'
}

# 其他配置
MISC_CONFIG = {
    'startup_delay': SNMP_BRIDGE_CONFIG['startup_delay'],
    'error_value': SNMP_BRIDGE_CONFIG['error_value']
}

# 为了兼容性，保留 SNMP_CONFIG 别名
SNMP_CONFIG = {
    'listen_ip': SNMP_BRIDGE_CONFIG['listen_ip'],
    'listen_port': SNMP_BRIDGE_CONFIG['listen_port'],
    'community': SNMP_BRIDGE_CONFIG['community']
}

if __name__ == "__main__":
    """测试配置加载"""
    print("🧪 测试配置加载")
    print("=" * 50)
    
    print("SNMP 桥接配置:")
    for key, value in SNMP_BRIDGE_CONFIG.items():
        print(f"  {key}: {value}")
    
    print(f"\nModbus 类型: {MODBUS_TYPE}")
    
    print(f"\n系统 OID 数量: {len(SYSTEM_OID_MAPPING)}")
    print(f"业务 OID 数量: {len(SNMP_OID_MAPPING)}")
    
    print(f"\n时区配置: {TIMEZONE_CONFIG}")
    
    print("\n✅ 配置加载测试完成")
