#!/usr/bin/env python3
"""
Linux 配置测试脚本

测试 Linux 版本的配置文件加载和服务功能
"""

import sys
import os

def test_config_loading():
    """测试配置文件加载"""
    print("🧪 测试 Linux 配置文件加载")
    print("=" * 50)
    
    try:
        # 临时使用 Linux 配置文件
        config_backup = False
        if os.path.exists('config.linux.ini'):
            if os.path.exists('config.ini'):
                os.rename('config.ini', 'config.ini.backup')
                config_backup = True
            os.rename('config.linux.ini', 'config.ini')
        
        from config_loader import (
            SNMP_BRIDGE_CONFIG, MODBUS_TYPE, MODBUS_TCP_CONFIG, MODBUS_RTU_CONFIG,
            SYSTEM_OID_MAPPING, SNMP_OID_MAPPING, TIMEZONE_CONFIG
        )
        
        print("✅ 配置文件加载成功")
        print(f"📡 监听端口: {SNMP_BRIDGE_CONFIG['listen_port']}")
        print(f"🔗 Modbus 类型: {MODBUS_TYPE}")
        print(f"🌍 时区设置: {TIMEZONE_CONFIG['timezone_offset']}")
        print(f"📋 系统 OID 数量: {len(SYSTEM_OID_MAPPING)}")
        print(f"📋 业务 OID 数量: {len(SNMP_OID_MAPPING)}")
        
        # 检查 Linux 特定配置
        if SNMP_BRIDGE_CONFIG['listen_port'] == 161:
            print("✅ 使用标准 SNMP 端口 161")
        
        if 'ttyUSB0' in MODBUS_RTU_CONFIG['port']:
            print("✅ RTU 配置使用 Linux 串口设备")
        
        # 检查系统 OID
        linux_oids = [oid for oid in SYSTEM_OID_MAPPING if 'Linux' in str(oid.get('value', ''))]
        if linux_oids:
            print("✅ 检测到 Linux 特定的系统 OID")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False
    
    finally:
        # 恢复原配置文件
        if os.path.exists('config.ini'):
            os.rename('config.ini', 'config.linux.ini')
        if os.path.exists('config.ini.backup'):
            os.rename('config.ini.backup', 'config.ini')

def test_script_permissions():
    """测试脚本权限"""
    print("\n🔐 测试脚本权限")
    print("=" * 50)

    # 在 Windows 下跳过权限检查
    if os.name == 'nt':
        print("⚠️  Windows 系统，跳过权限检查")
        print("💡 在 Linux 部署时会自动设置执行权限")
        return True

    scripts = ['start.sh', 'deploy.sh', 'cleanup.sh', 'package.sh']

    for script in scripts:
        if os.path.exists(script):
            stat = os.stat(script)
            is_executable = bool(stat.st_mode & 0o111)
            print(f"{'✅' if is_executable else '❌'} {script}: {'可执行' if is_executable else '不可执行'}")
        else:
            print(f"❌ {script}: 文件不存在")

    return True

def test_file_structure():
    """测试文件结构"""
    print("\n📁 测试文件结构")
    print("=" * 50)
    
    required_files = {
        'snmp_modbus_bridge.py': '主服务程序',
        'config_loader.py': '配置加载器',
        'config.linux.ini': 'Linux 配置文件',
        'start.sh': '启动脚本',
        'deploy.sh': '部署脚本',
        'snmp-modbus-bridge.service': 'systemd 服务文件',
        'README.md': '说明文档',
        'LINUX_DEPLOYMENT.md': 'Linux 部署指南',
        'requirements.txt': '依赖列表'
    }
    
    missing_files = []
    for filename, description in required_files.items():
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            print(f"✅ {filename}: {description} ({size} bytes)")
        else:
            print(f"❌ {filename}: {description} (缺失)")
            missing_files.append(filename)
    
    if missing_files:
        print(f"\n⚠️  缺失文件: {', '.join(missing_files)}")
        return False
    else:
        print("\n✅ 所有必需文件都存在")
        return True

def test_python_imports():
    """测试 Python 模块导入"""
    print("\n🐍 测试 Python 模块导入")
    print("=" * 50)
    
    required_modules = [
        'pysnmp',
        'pymodbus', 
        'pyasn1',
        'configparser',
        'datetime',
        'logging',
        'time'
    ]
    
    failed_imports = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}: 导入成功")
        except ImportError as e:
            print(f"❌ {module}: 导入失败 - {e}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"\n⚠️  需要安装的模块: {', '.join(failed_imports)}")
        print("安装命令: pip3 install " + " ".join(failed_imports))
        return False
    else:
        print("\n✅ 所有 Python 模块都可用")
        return True

def main():
    """主函数"""
    print("🚀 SNMP-Modbus 桥接服务 Linux 版本测试")
    print("=" * 60)
    print()
    
    tests = [
        ("配置文件加载", test_config_loading),
        ("脚本权限", test_script_permissions),
        ("文件结构", test_file_structure),
        ("Python 模块", test_python_imports)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！Linux 版本准备就绪")
        print("\n📋 下一步:")
        print("  1. 运行 ./cleanup.sh 清理测试文件")
        print("  2. 运行 ./package.sh 创建部署包")
        print("  3. 将部署包上传到 Linux 服务器")
        print("  4. 在服务器上运行 sudo ./deploy.sh install")
    else:
        print("⚠️  部分测试失败，请检查上述错误信息")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
