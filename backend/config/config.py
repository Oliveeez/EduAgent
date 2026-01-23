"""
配置文件
"""

import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

for dir_path in [DATA_DIR, TEMPLATES_DIR, STATIC_DIR]:
    dir_path.mkdir(exist_ok=True, parents=True)

KNOWLEDGE_GRAPHS_DIR = DATA_DIR / "knowledge_graphs"
OUTLINES_DIR = DATA_DIR / "outlines"
PPT_OUTPUT_DIR = DATA_DIR / "ppt_outputs"
LATEX_UPLOADS_DIR = DATA_DIR / "latex_uploads"

for dir_path in [KNOWLEDGE_GRAPHS_DIR, OUTLINES_DIR, PPT_OUTPUT_DIR, LATEX_UPLOADS_DIR]:
    dir_path.mkdir(exist_ok=True, parents=True)

LLM_CONFIG = {
    "model": "claude-sonnet-4-20250514",
    "temperature": 0.7,
    "max_tokens": 4096,
}

# PPT配置
PPT_CONFIG = {
    "default_template": None,  # 用户指定的模板路径
    "slide_width": 10,    # inches
    "slide_height": 7.5,  # inches
    "default_font": "Arial",
    "title_font_size": 44,
    "content_font_size": 18,
    "enable_animations": True,
    "enable_math_rendering": True,
}

# 知识图谱配置
KG_CONFIG = {
    "max_depth": 3,         # 层级深度：章节-知识点-概念
    "min_confidence": 0.7,  # 最小置信度
    "enable_visualization": True,
}

# API配置
API_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "cors_origins": ["http://localhost:3000","http://localhost:3001"],
}

# 日志配置
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
}