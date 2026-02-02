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


class BlockType(Enum):
    """Block类型枚举"""
    TEXT_LINE = "text_line"                       # 单行文本
    CONCEPTUAL_STATEMENT = "conceptual_statement"  # 概念陈述
    FORMULA = "formula"                           # 公式
    CODE = "code"                                 # 代码块
    MANIM_RELATION = "manim_relation"             # Manim关系图/函数图
    IMAGE = "image"                               # 图片/GIF
    TITLE = "title"                               # 标题


class PageIntent(Enum):
    """页面意图枚举（Intent Layer）- 教学叙事中的作用"""
    INTRODUCE_CONCEPT = "introduce_concept"       # 引入新概念
    EXPLAIN_MECHANISM = "explain_mechanism"       # 解释原理或机制
    SHOW_RELATION = "show_relation"               # 展示概念之间的关系
    WALK_THROUGH_PROOF = "walk_through_proof"     # 逐步讲解公式或代码
    MOTIVATE_IMPORTANCE = "motivate_importance"   # 说明为什么重要


class PageAtom(Enum):
    """页面表现原子枚举"""
    CONCEPTUAL_STATEMENT = "conceptual_statement"
    FORMULA_FOCUS = "formula_focus"
    CODE_WALKTHROUGH = "code_walkthrough"
    RELATIONAL_VISUALIZATION = "relational_visualization"
    CONCEPT_WITH_VISUAL = "concept_with_visual"


class SemanticRole(Enum):
    """Block的语义角色"""
    DEFINITION = "definition"         # 定义
    MOTIVATION = "motivation"         # 动机/重要性说明
    EXAMPLE = "example"              # 举例
    RELATION = "relation"            # 关系展示
    TRANSITION = "transition"        # 过渡
    EXPLANATION = "explanation"      # 解释
    PROOF_STEP = "proof_step"        # 证明步骤


@dataclass
class SlideBlock:
    """
    Slide内容块（升级版）
    
    每个Block是一个"认知+时序"单位：
    - 认知单位：一个完整的教学信息片段
    - 时序单位：一个独立的时间片段（可配音、可字幕、可控制出现）
    """
    block_id: str                              # 唯一ID，格式: "slide_{slide_id}_block_{idx}"
    block_type: str                            # BlockType的值
    content: Any                               # 文本、LaTeX、代码、Manim配置或图片URL
    
    # 语义信息
    semantic_role: str = "explanation"         # SemanticRole的值
    position_hint: str = "left"                # 布局提示：left/right/center
    
    # 样式信息（文本block专用）
    emphasis: Optional[Dict[str, Any]] = None  # {"bold": [...], "color": {"word": "red"}}
    
    # 时序信息（两阶段估计）
    estimated_duration: float = 0.0            # Stage 1.5认知时长估计（秒）
    start_time: float = 0.0                    # 相对于slide开始的时间（秒）
    duration: float = 0.0                      # Stage 6物理时长修正后（秒）
    
    # 音频和字幕
    audio_path: Optional[str] = None           # 该block的音频文件路径
    subtitle_text: str = ""                    # 对应的字幕文本
    
    # 布局信息（由Stage 4/5填充）
    bbox: Optional[Dict[str, float]] = None    # {"left": 0, "top": 0, "width": 0, "height": 0}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "block_id": self.block_id,
            "block_type": self.block_type,
            "content": str(self.content) if not isinstance(self.content, (dict, list)) else self.content,
            "semantic_role": self.semantic_role,
            "position_hint": self.position_hint,
            "emphasis": self.emphasis,
            "estimated_duration": self.estimated_duration,
            "start_time": self.start_time,
            "duration": self.duration,
            "audio_path": self.audio_path,
            "subtitle_text": self.subtitle_text,
            "bbox": self.bbox
        }


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
    
    # 块级内容（Stage 1.5生成）
    blocks: List[SlideBlock] = field(default_factory=list)
    
    # Stage 1.5决策信息
    page_intent: Optional[str] = None           # PageIntent的值
    page_atoms: List[str] = field(default_factory=list)  # PageAtom的值列表
    needs_split: bool = False                   # 是否需要分页
    
    # Manim关系图配置
    manim_relation_config: Optional[Dict[str, Any]] = None
    
    # 图片搜索关键词
    image_search_queries: List[str] = field(default_factory=list)
    
    # 内容字段（保留兼容性）
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
            "blocks": [b.to_dict() for b in self.blocks] if self.blocks else [],
            "page_intent": self.page_intent,
            "page_atoms": self.page_atoms,
            "needs_split": self.needs_split,
            "manim_relation_config": self.manim_relation_config,
            "image_search_queries": self.image_search_queries,
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
        blocks_data = data.get("blocks", [])
        blocks = [
            SlideBlock(
                block_id=b.get("block_id", ""),
                block_type=b["block_type"],
                content=b["content"],
                semantic_role=b.get("semantic_role", "explanation"),
                position_hint=b.get("position_hint", "left"),
                emphasis=b.get("emphasis"),
                estimated_duration=b.get("estimated_duration", 0.0),
                start_time=b.get("start_time", 0.0),
                duration=b.get("duration", 0.0),
                audio_path=b.get("audio_path"),
                subtitle_text=b.get("subtitle_text", ""),
                bbox=b.get("bbox")
            ) for b in blocks_data
        ]
        
        return cls(
            slide_id=data["slide_id"],
            slide_type=SlideType(data["slide_type"]),
            title=data["title"],
            text=data["text"],
            blocks=blocks,
            page_intent=data.get("page_intent"),
            page_atoms=data.get("page_atoms", []),
            needs_split=data.get("needs_split", False),
            manim_relation_config=data.get("manim_relation_config"),
            image_search_queries=data.get("image_search_queries", []),
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
    """元素边界框（增强版：支持block关联）"""
    element_type: str      # "text" 或 "image"
    left: float           # 左边距（英寸）
    top: float            # 上边距（英寸）
    width: float          # 宽度（英寸）
    height: float         # 高度（英寸）
    content: str = ""     # 内容（用于调试）
    block_id: Optional[str] = None  # 关联的block ID
    block_type: Optional[str] = None  # block类型（用于VLM理解）
    semantic_role: Optional[str] = None  # 语义角色（用于VLM理解）
    shape_index: Optional[int] = None  # PPT中的实际shape索引（用于调整）
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": self.element_type,
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
            "content": self.content[:50] if self.content else ""
        }
        if self.block_id:
            result["block_id"] = self.block_id
        if self.block_type:
            result["block_type"] = self.block_type
        if self.semantic_role:
            result["semantic_role"] = self.semantic_role
        return result
    
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


