# Video Pipeline Module
# 从演讲稿生成教学视频的完整Pipeline

from .models import SlideStructure, SlideType
from .main_pipeline import VideoPipeline

__all__ = [
    'SlideStructure',
    'SlideType', 
    'VideoPipeline'
]
