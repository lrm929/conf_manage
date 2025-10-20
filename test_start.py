#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试启动脚本
"""

import os
import sys
from pathlib import Path

# 添加backend目录到Python路径
backend_dir = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_dir))

# 导入并运行Flask应用
from app import app

if __name__ == '__main__':
    print("启动游戏配置管理系统...")
    print("访问地址: http://localhost:5000")
    # 不切换到backend目录，保持当前目录
    app.run(host='0.0.0.0', port=5000, debug=False)
