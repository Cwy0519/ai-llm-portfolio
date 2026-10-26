# -*- coding: utf-8 -*-
"""让 pytest 从项目根目录导入模块（无需安装成包）。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
