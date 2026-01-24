# models.py
# 视频Pipeline核心数据模型

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from pathlib import Path


class SlideType(Enum):
    """Slide类型枚举"""
    COQ = "coq"           # Coq代码块
    FORMULA = "formula"   # 数学公式
    INTRO = "intro"       # 引言/过渡页（无代码/公式）


@dataclass
class SlideStructure:
    """
    单页Slide的完整数据结构
    
    这是Pipeline的核心数据单元，所有Stage都围绕它工作
    """
    slide_id: int                           # 唯一标识（从1开始）
    slide_type: SlideType                   # 类型：coq/formula/intro
    title: str                              # 页面标题
    text: str                               # PPT显示文本（结构化要点）
    
    # 内容字段（根据type填充）
    coq_code: Optional[str] = None          # Coq代码（type=coq时）
    formula: Optional[str] = None           # LaTeX公式（type=formula时）
    
    # 由后续Stage填充的字段
    gif_path: Optional[Path] = None         # Manim生成的GIF路径
    audio_path: Optional[Path] = None       # TTS生成的音频路径
    duration: Optional[float] = None        # 该页的时长（秒）
    
    # 元数据
    section_title: str = ""                 # 所属章节标题
    estimated_duration: float = 0.0         # 估算时长（基于文本长度）
    original_text: str = ""                 # 原始演讲稿文本（用于TTS和字幕）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "slide_id": self.slide_id,
            "slide_type": self.slide_type.value,
            "title": self.title,
            "text": self.text,
            "original_text": self.original_text,
            "coq_code": self.coq_code,
            "formula": self.formula,
            "gif_path": str(self.gif_path) if self.gif_path else None,
            "audio_path": str(self.audio_path) if self.audio_path else None,
            "duration": self.duration,
            "section_title": self.section_title,
            "estimated_duration": self.estimated_duration
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SlideStructure':
        """从字典创建实例"""
        return cls(
            slide_id=data["slide_id"],
            slide_type=SlideType(data["slide_type"]),
            title=data["title"],
            text=data["text"],
            coq_code=data.get("coq_code"),
            formula=data.get("formula"),
            gif_path=Path(data["gif_path"]) if data.get("gif_path") else None,
            audio_path=Path(data["audio_path"]) if data.get("audio_path") else None,
            duration=data.get("duration"),
            section_title=data.get("section_title", ""),
            estimated_duration=data.get("estimated_duration", 0.0),
            original_text=data.get("original_text", "")
        )


@dataclass
class BoundingBox:
    """元素边界框"""
    element_type: str      # "text" 或 "image"
    left: float           # 左边距（英寸）
    top: float            # 上边距（英寸）
    width: float          # 宽度（英寸）
    height: float         # 高度（英寸）
    content: str = ""     # 内容（用于调试）
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.element_type,
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
            "content": self.content[:50] if self.content else ""
        }
    
    def overlaps_with(self, other: 'BoundingBox') -> bool:
        """检测是否与另一个边界框重叠"""
        return not (
            self.left + self.width < other.left or
            other.left + other.width < self.left or
            self.top + self.height < other.top or
            other.top + other.height < self.top
        )


@dataclass
class SlideBBoxes:
    """单页的所有边界框"""
    slide_id: int
    elements: List[BoundingBox] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "slide_id": self.slide_id,
            "elements": [e.to_dict() for e in self.elements]
        }
    
    def has_overlaps(self) -> bool:
        """检测页面内是否有元素重叠"""
        for i, elem1 in enumerate(self.elements):
            for elem2 in self.elements[i+1:]:
                if elem1.overlaps_with(elem2):
                    return True
        return False


@dataclass
class SubtitleEntry:
    """字幕条目"""
    index: int           # 序号
    start_time: float    # 开始时间（秒）
    end_time: float      # 结束时间（秒）
    text: str            # 字幕文本
    
    def to_srt_format(self) -> str:
        """转换为SRT格式"""
        def format_time(seconds: float) -> str:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            millis = int((seconds % 1) * 1000)
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
        
        return f"{self.index}\n{format_time(self.start_time)} --> {format_time(self.end_time)}\n{self.text}\n"


@dataclass 
class PipelineResult:
    """Pipeline执行结果"""
    success: bool
    video_path: Optional[Path] = None
    pptx_path: Optional[Path] = None
    audio_path: Optional[Path] = None
    subtitle_path: Optional[Path] = None
    total_duration: float = 0.0
    slides: List[SlideStructure] = field(default_factory=list)
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "video_path": str(self.video_path) if self.video_path else None,
            "pptx_path": str(self.pptx_path) if self.pptx_path else None,
            "audio_path": str(self.audio_path) if self.audio_path else None,
            "subtitle_path": str(self.subtitle_path) if self.subtitle_path else None,
            "total_duration": self.total_duration,
            "slide_count": len(self.slides),
            "error_message": self.error_message
        }


