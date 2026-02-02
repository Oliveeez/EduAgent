# 视频生成Pipeline升级方案
## Multi-Agent System + Block-Level Control

**日期**: 2026-01-25  
**状态**: 设计阶段  
**目标**: 引入多Agent系统，实现内容自主生成、智能排版、精细化时序控制

---

## 一、架构设计

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    Multi-Agent Orchestrator                  │
│                   (多Agent编排器 - 新增)                      │
└────────┬───────────────────────────────────┬────────────────┘
         │                                   │
         ▼                                   ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   Agent 1       │   │   Agent 2       │   │   Agent 3       │
│  内容分析师      │──▶│  元素生成器      │──▶│  页面导演        │
│                 │   │                 │   │                 │
│ - 语义分析      │   │ - 公式提取      │   │ - 原子选择      │
│ - 知识点拆解    │   │ - 代码块识别    │   │ - 布局规划      │
│ - 教学策略      │   │ - 关系图设计    │   │ - 动画编排      │
│ - 分段决策      │   │ - 图片搜索      │   │ - 块级时序      │
└─────────────────┘   └─────────────────┘   └─────────────────┘
         │                     │                     │
         └──────────┬──────────┴──────────┬─────────┘
                    ▼                     ▼
          ┌──────────────────┐  ┌──────────────────┐
          │ Block Manager     │  │ Layout Engine    │
          │ (块管理器 - 新增)  │  │ (排版引擎 - 增强) │
          │                   │  │                   │
          │ - Block定义       │  │ - VLM智能排版     │
          │ - BBox提取        │  │ - 自动分页        │
          │ - 时序分配        │  │ - 碰撞检测        │
          └──────────────────┘  └──────────────────┘
                    │                     │
                    └──────────┬─────────┘
                              ▼
                    ┌──────────────────┐
                    │  Video Composer   │
                    │  (视频合成 - 增强) │
                    │                   │
                    │ - 块级动画控制     │
                    │ - 精细时序对齐     │
                    │ - 字幕同步        │
                    └──────────────────┘
```

### 1.2 数据流

```
JSON输入 
  → Agent1(分析) 
  → Agent2(生成元素) 
  → Agent3(页面设计) 
  → Block Manager(块化) 
  → Layout Engine(排版)
  → Video Composer(合成)
  → 最终视频
```

---

## 二、数据模型升级

### 2.1 新增：Block（内容块）

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any

class BlockType(Enum):
    """内容块类型"""
    TEXT_LINE = "text_line"           # 单行文本
    CONCEPTUAL_STATEMENT = "conceptual_statement"  # 概念陈述
    FORMULA = "formula"               # 公式
    CODE = "code"                     # 代码块
    MANIM_ANIMATION = "manim_animation"  # Manim动画（关系图/函数图）
    IMAGE = "image"                   # 图片/GIF
    TITLE = "title"                   # 标题

class RevealMode(Enum):
    """显示模式"""
    INSTANT = "instant"              # 立即显示
    LINE_BY_LINE = "line_by_line"    # 逐行显示
    FADE_IN = "fade_in"              # 淡入
    CLICK = "click"                  # 点击显示

@dataclass
class Block:
    """
    内容块 - Pipeline的最小原子单位
    
    每个Block对应：
    - PPT中的一个元素（文本框的一行、一个图片、一个动画）
    - 视频中的一个时间片段
    - 字幕中的一个或多个条目
    """
    block_id: str                    # 唯一ID，格式: "slide_{slide_id}_block_{idx}"
    block_type: BlockType            # 块类型
    content: str                     # 内容（文本/LaTeX/代码/文件路径）
    
    # 布局信息
    bbox: Optional[BoundingBox] = None  # 边界框（由Layout Engine填充）
    z_index: int = 0                 # 层级（用于重叠控制）
    
    # 时序信息
    start_time: float = 0.0          # 开始时间（相对于slide开始）
    duration: float = 0.0            # 持续时间
    reveal_mode: RevealMode = RevealMode.INSTANT  # 显示模式
    
    # 样式信息
    emphasis: Optional[Dict[str, Any]] = None  # 强调样式 {"bold": [...], "color": {...}}
    
    # 语音字幕关联
    audio_text: str = ""             # 对应的语音文本
    subtitle_indices: List[int] = field(default_factory=list)  # 关联的字幕索引
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "block_id": self.block_id,
            "block_type": self.block_type.value,
            "content": self.content[:100],  # 截断
            "bbox": self.bbox.to_dict() if self.bbox else None,
            "start_time": self.start_time,
            "duration": self.duration,
            "reveal_mode": self.reveal_mode.value,
            "audio_text": self.audio_text[:50]
        }
```

### 2.2 升级：SlideStructure

```python
@dataclass
class SlideStructure:
    """
    单页Slide的完整数据结构（升级版）
    """
    slide_id: int
    slide_type: SlideType
    title: str
    
    # 新增：Block列表（替代原来的单一text/formula/coq_code）
    blocks: List[Block] = field(default_factory=list)
    
    # 页面级元数据
    total_duration: float = 0.0      # 该页总时长（所有blocks之和）
    layout_strategy: str = ""        # Agent3决定的布局策略
    
    # 保留原有字段（用于兼容）
    gif_path: Optional[Path] = None
    audio_path: Optional[Path] = None
    section_title: str = ""
    original_text: str = ""
```

### 2.3 新增：PageAtom（页面表现原子）

```python
class PageAtom(Enum):
    """页面表现原子类型（Agent3决策空间）"""
    CONCEPTUAL_STATEMENT = "conceptual_statement"
    FORMULA_FOCUS = "formula_focus"
    CODE_WALKTHROUGH = "code_walkthrough"
    RELATIONAL_VISUALIZATION = "relational_visualization"  # 新增
    CONCEPT_WITH_VISUAL = "concept_with_visual"           # 新增

@dataclass
class PageDesign:
    """
    Agent3输出：单页的设计方案
    """
    slide_id: int
    atoms: List[PageAtom]            # 使用的原子类型
    blocks: List[Block]              # 生成的块列表
    layout_hints: Dict[str, Any]     # 布局提示（给Layout Engine）
    needs_split: bool = False        # 是否需要分页
    manim_config: Optional[Dict] = None  # Manim配置（如果需要）
```

---

##三、Agent系统设计

### 3.1 Agent 1: 内容分析师（ContentAnalyst）

**职责**：语义理解、知识点拆解、教学策略规划

**输入**：
- 原始演讲稿JSON
- sections列表

**输出**：
```python
@dataclass
class ContentAnalysis:
    """内容分析结果"""
    knowledge_points: List[Dict]     # 知识点列表
    teaching_strategy: str           # 教学策略（精讲/概览）
    relations: List[Dict]            # 概念关系（用于生成关系图）
    complexity_score: float          # 复杂度评分
    recommended_slides: int          # 建议页数
```

**Prompt模板**：
```
你是一个教学内容分析专家。请分析以下教学内容：

{section_text}

请提供：
1. 核心知识点列表（每个知识点包含：名称、定义、重要性）
2. 知识点之间的关系（A→B表示依赖、A↔B表示对比）
3. 教学策略建议（精讲/快速概览/问题驱动）
4. 内容复杂度评分（1-10）
5. 建议拆分成几页slides

返回JSON格式：
{
  "knowledge_points": [...],
  "relations": [{"from": "A", "to": "B", "type": "depends_on"}, ...],
  "teaching_strategy": "精讲",
  "complexity_score": 7.5,
  "recommended_slides": 2
}
```

### 3.2 Agent 2: 元素生成器（ElementGenerator）

**职责**：提取公式、代码、设计关系图、搜索图片

**输入**：
- 原始文本
- ContentAnalysis结果

**输出**：
```python
@dataclass
class GeneratedElements:
    """生成的元素"""
    formulas: List[Dict]             # {"content": "...", "semantic": "..."}
    code_blocks: List[Dict]          # {"language": "coq", "code": "..."}
    manim_specs: List[Dict]          # Manim可视化规格
    images: List[Dict]               # 搜索到的图片
```

**关键功能**：

1. **关系图生成**：
```python
def design_relational_visualization(self, relations: List[Dict]) -> Dict:
    """
    根据概念关系设计Manim可视化
    
    返回Manim场景配置：
    {
      "type": "directed_graph",  # 或 "function_plot", "flowchart"
      "nodes": [{"id": "A", "label": "不确定性"}],
      "edges": [{"from": "A", "to": "B", "label": "导致"}]
    }
    """
```

2. **图片搜索**：
```python
def search_concept_image(self, concept: str, context: str) -> Optional[str]:
    """
    使用搜索API为概念查找合适的图片
    
    Args:
        concept: 概念名（如"孙子算经"）
        context: 上下文（用于筛选）
    
    Returns:
        图片URL或None
    """
```

### 3.3 Agent 3: 页面导演（PageDirector） ⭐⭐⭐

**职责**：决定每页使用哪些原子、块级编排、时序规划

**输入**：
- ContentAnalysis
- GeneratedElements
- 原始文本

**输出**：
- `List[PageDesign]`

**决策逻辑**：

```python
class PageDirector:
    """页面导演 - Agent3实现"""
    
    def __init__(self):
        self.llm = CustomLLM()
        
    def design_pages(self, 
                     content_analysis: ContentAnalysis,
                     elements: GeneratedElements,
                     text: str) -> List[PageDesign]:
        """
        设计页面布局
        
        核心决策：
        1. 选择页面原子组合
        2. 生成Block列表
        3. 分配时序
        4. 决定是否分页
        """
        
        # Prompt给LLM
        prompt = self._build_director_prompt(content_analysis, elements, text)
        response = self.llm(prompt)
        
        # 解析LLM输出
        designs = self._parse_llm_response(response)
        
        # 验证和优化
        designs = self._validate_designs(designs)
        
        return designs
    
    def _build_director_prompt(self, ...) -> str:
        return f"""
你是一个教学型PPT页面设计导演。你的目标是为每一页选择最合适的知识表达形式。

可用的页面表现原子（可组合2-3个）：

1. **Conceptual Statement（概念陈述文本）**
   - 书面化、完整、可独立成立
   - 禁止："我们将看到"、"接下来"等口语化
   - 支持关键词强调（加粗/颜色）

2. **Formula Focus（公式展示）**
   - 完整公式，来自GeneratedElements
   - 若涉及方程组，使用大括号

3. **Code Walkthrough（代码讲解）**
   - 代码块 + 至少一条Conceptual Statement

4. **Relational/Structural Visualization（关系/结构可视化）** ⭐NEW
   - 使用Manim图形（箭头、函数图、结构图）
   - 表达：概念关系、函数行为、系统结构
   - 不使用网络图片

5. **Concept + Visual（概念+图示）** ⭐NEW
   - 在线搜索图片
   - 用于：抽象概念、举例应用

硬约束：
- 每页至少2种原子
- 禁止连续页面相同原子组合
- 禁止只有文本/公式/代码/图像的页面
- 禁止bullet point主导

当前内容：
{content_analysis}

可用元素：
{elements}

请输出JSON格式的页面设计：
{{
  "pages": [
    {{
      "slide_id": 1,
      "atoms": ["Conceptual Statement", "Relational Visualization"],
      "blocks": [
        {{
          "block_type": "conceptual_statement",
          "content": "大模型的不确定性是指...",
          "reveal_mode": "line_by_line",
          "emphasis": {{"bold": ["不确定性"], "color": {{"不确定性": "red"}}}}
        }},
        {{
          "block_type": "manim_animation",
          "content": "uncertainty_function_plot",
          "manim_config": {{"type": "function_plot", "x_label": "distance", "y_label": "uncertainty"}}
        }}
      ],
      "layout_hints": {{"text_position": "left", "visual_position": "right"}},
      "needs_split": false
    }}
  ]
}}
"""
```

**关键创新**：
- LLM自主决定原子组合
- 自动生成Block列表（包括类型、内容、样式）
- 判断是否需要分页（内容过多时）

---

## 四、核心模块实现

### 4.1 BlockManager（块管理器）- 新增

```python
class BlockManager:
    """
    Block管理器
    
    功能：
    1. 从PageDesign生成Block列表
    2. 分配时序（start_time, duration）
    3. 提取Block级别的BBox
    4. 管理Block之间的依赖关系
    """
    
    def __init__(self):
        self.blocks: List[Block] = []
        
    def create_blocks_from_design(self, design: PageDesign) -> List[Block]:
        """从PageDesign创建Block列表"""
        blocks = []
        cumulative_time = 0.0
        
        for i, block_spec in enumerate(design.blocks):
            block = Block(
                block_id=f"slide_{design.slide_id}_block_{i}",
                block_type=BlockType(block_spec["block_type"]),
                content=block_spec["content"],
                start_time=cumulative_time,
                duration=self._estimate_block_duration(block_spec),
                reveal_mode=RevealMode(block_spec.get("reveal_mode", "instant")),
                emphasis=block_spec.get("emphasis")
            )
            
            blocks.append(block)
            cumulative_time += block.duration
        
        return blocks
    
    def _estimate_block_duration(self, block_spec: Dict) -> float:
        """估算Block时长"""
        block_type = block_spec["block_type"]
        content = block_spec["content"]
        
        if block_type == "text_line":
            # 中文3.5字/秒
            return len(content) / 3.5
        elif block_type == "formula":
            return 3.0  # 公式停留3秒
        elif block_type == "manim_animation":
            return 5.0  # 动画5秒
        elif block_type == "image":
            return 2.0  # 图片2秒
        else:
            return 2.0
    
    def extract_block_bboxes(self, pptx_path: Path, blocks: List[Block]) -> List[Block]:
        """
        提取每个Block的BBox
        
        关键：需要知道PPT中每个元素对应哪个Block
        """
        prs = Presentation(str(pptx_path))
        
        for slide_idx, slide in enumerate(prs.slides):
            slide_blocks = [b for b in blocks if b.block_id.startswith(f"slide_{slide_idx}_")]
            
            # 按元素索引匹配Block（需要在生成PPT时记录对应关系）
            for block_idx, shape in enumerate(slide.shapes):
                if block_idx < len(slide_blocks):
                    bbox = self._extract_shape_bbox(shape)
                    if bbox:
                        slide_blocks[block_idx].bbox = bbox
        
        return blocks
```

### 4.2 LayoutEngine（排版引擎）- 增强

```python
class LayoutEngine:
    """
    智能排版引擎
    
    新增功能：
    1. 基于Block的BBox进行VLM排版
    2. 检测内容过多，自动分页
    3. 多轮优化直到无重叠
    """
    
    def __init__(self):
        self.llm = CustomLLM()
        self.page_width = 13.33
        self.page_height = 7.5
        
    def optimize_layout(self, 
                       design: PageDesign, 
                       blocks: List[Block]) -> Tuple[List[Block], bool]:
        """
        优化布局
        
        Returns:
            (优化后的blocks, 是否需要分页)
        """
        
        # 1. 初始布局（基于layout_hints）
        blocks = self._apply_initial_layout(blocks, design.layout_hints)
        
        # 2. 检测重叠
        overlaps = self._detect_overlaps(blocks)
        
        if not overlaps:
            return blocks, False
        
        # 3. VLM优化
        max_iterations = 3
        for i in range(max_iterations):
            # 调用VLM
            adjustments = self._get_vlm_adjustments(blocks, overlaps)
            
            if not adjustments:
                break
            
            # 应用调整
            blocks = self._apply_adjustments(blocks, adjustments)
            
            # 重新检测
            overlaps = self._detect_overlaps(blocks)
            if not overlaps:
                break
        
        # 4. 如果仍然重叠，判断是否需要分页
        if overlaps:
            needs_split = self._check_if_needs_split(blocks)
            return blocks, needs_split
        
        return blocks, False
    
    def _get_vlm_adjustments(self, blocks: List[Block], overlaps: List) -> List[Dict]:
        """
        调用VLM获取调整建议
        
        Prompt：给出每个Block的bbox和重叠情况，让VLM决定如何调整
        """
        prompt = f"""
你是PPT布局优化专家。当前页面有 {len(blocks)} 个Block，存在重叠。

页面尺寸：{self.page_width} x {self.page_height} 英寸

Block列表：
{json.dumps([{
    "block_id": b.block_id,
    "type": b.block_type.value,
    "bbox": b.bbox.to_dict() if b.bbox else None,
    "content_preview": b.content[:30]
} for b in blocks], indent=2)}

重叠情况：
{json.dumps(overlaps, indent=2)}

请提供调整方案（移动或缩放），确保：
1. 无重叠
2. 不超出页面边界
3. 保持视觉平衡

返回JSON：
{{
  "adjustments": [
    {{"block_id": "...", "action": "move", "new_left": 1.0, "new_top": 2.0}},
    {{"block_id": "...", "action": "resize", "new_width": 5.0}}
  ]
}}

如果无法调整（空间不足），返回空数组。
"""
        
        response = self.llm(prompt)
        result = json.loads(response)
        return result.get("adjustments", [])
    
    def _check_if_needs_split(self, blocks: List[Block]) -> bool:
        """
        判断是否需要分页
        
        策略：
        1. 计算所有blocks的总面积
        2. 如果超过页面70%，建议分页
        """
        total_area = sum(b.bbox.width * b.bbox.height for b in blocks if b.bbox)
        page_area = self.page_width * self.page_height
        
        return total_area > page_area * 0.7
    
    def split_page(self, design: PageDesign, blocks: List[Block]) -> List[PageDesign]:
        """
        分页
        
        策略：
        1. 将blocks分成两组（优先保持完整的Block）
        2. 生成两个新的PageDesign
        """
        # 简单策略：按时间顺序分一半
        mid = len(blocks) // 2
        
        page1 = PageDesign(
            slide_id=design.slide_id,
            atoms=design.atoms,
            blocks=blocks[:mid],
            layout_hints=design.layout_hints,
            needs_split=False
        )
        
        page2 = PageDesign(
            slide_id=design.slide_id + 1,  # 新页ID
            atoms=design.atoms,
            blocks=blocks[mid:],
            layout_hints=design.layout_hints,
            needs_split=False
        )
        
        return [page1, page2]
```

### 4.3 EnhancedVideoComposer（增强视频合成）

```python
class EnhancedVideoComposer:
    """
    增强版视频合成器
    
    新增功能：
    1. 块级动画控制（每个Block独立出现/消失）
    2. 精细时序对齐（Block与字幕同步）
    3. 支持逐行reveal动画
    """
    
    def compose_with_blocks(self,
                           pptx_path: Path,
                           slides: List[SlideStructure],
                           audio_path: Path,
                           subtitle_path: Path) -> Path:
        """
        基于Block的视频合成
        
        核心思路：
        1. 对每个Slide，按Block时序生成多个视频片段
        2. 每个Block对应一个动画事件（出现/高亮）
        3. 使用FFmpeg的overlay滤镜实现逐个Block显示
        """
        
        segments = []
        
        for slide in slides:
            # 为该Slide的每个Block生成片段
            slide_segments = self._create_slide_with_blocks(
                pptx_path, slide
            )
            segments.extend(slide_segments)
        
        # 合并所有片段
        video_no_audio = self._concat_segments(segments)
        
        # 添加音频和字幕
        final_video = self._add_audio_and_subtitles(
            video_no_audio, audio_path, subtitle_path
        )
        
        return final_video
    
    def _create_slide_with_blocks(self, 
                                  pptx_path: Path, 
                                  slide: SlideStructure) -> List[Path]:
        """
        为单个Slide生成按Block分段的视频
        
        实现方式：
        1. 导出Slide的静态背景图
        2. 对每个Block，生成"添加该Block"的视频片段
        3. 使用FFmpeg的drawtext/overlay实现逐个Block出现
        """
        
        # 提取Slide背景（不含Block）
        bg_image = self._export_slide_background(pptx_path, slide.slide_id)
        
        segments = []
        accumulated_blocks = []  # 已显示的blocks
        
        for block in slide.blocks:
            accumulated_blocks.append(block)
            
            # 生成包含当前所有blocks的帧
            segment = self._render_blocks_on_background(
                bg_image,
                accumulated_blocks,
                block.duration
            )
            
            segments.append(segment)
        
        return segments
    
    def _render_blocks_on_background(self,
                                     bg_image: Path,
                                     blocks: List[Block],
                                     duration: float) -> Path:
        """
        在背景上渲染Blocks
        
        使用FFmpeg的复杂滤镜实现：
        - drawtext: 渲染文本Block
        - overlay: 叠加图片/GIF Block
        """
        
        output = self.temp_dir / f"segment_{uuid.uuid4()}.mp4"
        
        # 构建FFmpeg滤镜链
        filters = [f"[0:v]null[bg]"]
        
        for i, block in enumerate(blocks):
            if block.block_type == BlockType.TEXT_LINE:
                # 添加文本
                text_filter = self._create_text_filter(block)
                filters.append(text_filter)
            elif block.block_type == BlockType.IMAGE:
                # 添加图片overlay
                overlay_filter = self._create_overlay_filter(block, i)
                filters.append(overlay_filter)
        
        filter_complex = ";".join(filters)
        
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(bg_image),
            "-filter_complex", filter_complex,
            "-t", str(duration),
            "-c:v", "libx264",
            str(output)
        ]
        
        subprocess.run(cmd, capture_output=True)
        
        return output
    
    def _align_subtitles_with_blocks(self,
                                     slides: List[SlideStructure]) -> List[SubtitleEntry]:
        """
        生成Block级别对齐的字幕
        
        每个Block对应一个或多个字幕条目
        """
        subtitles = []
        subtitle_index = 1
        
        for slide in slides:
            slide_start_time = slide.start_time  # 该Slide在视频中的起始时间
            
            for block in slide.blocks:
                if block.audio_text:
                    # 为该Block生成字幕
                    start = slide_start_time + block.start_time
                    end = start + block.duration
                    
                    subtitle = SubtitleEntry(
                        index=subtitle_index,
                        start_time=start,
                        end_time=end,
                        text=block.audio_text
                    )
                    
                    subtitles.append(subtitle)
                    subtitle_index += 1
        
        return subtitles
```

---

## 五、实现路线图

### Phase 1: 数据模型升级（2-3天）

- [ ] 实现`Block`类
- [ ] 升级`SlideStructure`
- [ ] 实现`PageDesign`类
- [ ] 修改序列化/反序列化

### Phase 2: Agent 1 & 2 实现（3-4天）

- [ ] 实现`ContentAnalyst` Agent
- [ ] 实现`ElementGenerator` Agent
- [ ] 编写Agent Prompt模板
- [ ] 测试Agent输出质量

### Phase 3: Agent 3 实现（5-6天）⭐核心

- [ ] 实现`PageDirector` Agent
- [ ] 设计完整的Director Prompt
- [ ] 实现原子组合逻辑
- [ ] 实现Block生成逻辑
- [ ] 多轮测试优化

### Phase 4: BlockManager实现（2-3天）

- [ ] 实现Block创建
- [ ] 实现时序分配
- [ ] 实现Block级BBox提取
- [ ] PPT生成时记录Block-元素映射

### Phase 5: LayoutEngine增强（3-4天）

- [ ] 实现Block级VLM排版
- [ ] 实现自动分页逻辑
- [ ] 实现分页函数
- [ ] 多轮优化测试

### Phase 6: VideoComposer增强（4-5天）

- [ ] 实现Block级视频片段生成
- [ ] 实现逐Block动画
- [ ] 实现Block-字幕对齐
- [ ] FFmpeg滤镜调试

### Phase 7: 集成测试（3-4天）

- [ ] 端到端测试
- [ ] 性能优化
- [ ] Prompt调优
- [ ] 文档完善

**总计：约 3-4 周**

---

## 六、技术难点与解决方案

### 6.1 Prompt工程

**难点**：Agent3的Prompt非常复杂，需要让LLM理解5种原子类型、硬约束、输出JSON格式

**解决方案**：
1. Few-shot Learning：提供3-5个标准示例
2. 分步引导：先选原子，再生成Block，最后规划布局
3. Chain-of-Thought：让LLM先分析内容，再做决策
4. 迭代优化：根据输出质量不断调整Prompt

### 6.2 Block级BBox提取

**难点**：PPT中每个文本框可能包含多行，如何区分每一行的BBox？

**解决方案**：
1. **方案A（推荐）**：在生成PPT时，每个Block生成独立的文本框/形状
   - 优点：BBox提取简单，一一对应
   - 缺点：PPT元素较多

2. **方案B**：使用python-pptx的段落（Paragraph）级别分析
   ```python
   for shape in slide.shapes:
       if hasattr(shape, 'text_frame'):
           for para_idx, para in enumerate(shape.text_frame.paragraphs):
               # 计算该段落的相对位置
               line_bbox = self._calculate_paragraph_bbox(shape, para_idx)
   ```

### 6.3 Block级视频动画

**难点**：如何在视频中实现"逐个Block出现"的动画效果？

**解决方案**：
1. **方案A（静态）**：每个Block生成一帧图片，拼接成视频
   - 实现简单，但动画效果差

2. **方案B（FFmpeg滤镜）**：使用drawtext + fade实现淡入效果
   ```bash
   ffmpeg -i bg.png -filter_complex "
     drawtext=text='Block 1':enable='between(t,0,5)':fade=in:0:1,
     drawtext=text='Block 2':enable='between(t,5,10)':fade=in:5:1
   " output.mp4
   ```

3. **方案C（Manim渲染）** ⭐推荐
   - 将整个Slide作为Manim场景
   - 使用Manim的`Write`、`FadeIn`等动画
   - 优点：动画效果最好，支持复杂效果
   - 缺点：渲染时间较长

### 6.4 字幕精细对齐

**难点**：如何确保每个Block的字幕与语音、动画完全同步？

**解决方案**：
1. **TTS时记录时间戳**：使用支持word-level时间戳的TTS（如Azure TTS）
2. **强制对齐**：使用Montreal Forced Aligner等工具
3. **Block时长调整**：根据实际TTS时长反向调整Block的duration

---

## 七、配置与参数

### 7.1 Agent配置

```python
AGENT_CONFIG = {
    "agent1_content_analyst": {
        "model": "qwen-max",
        "temperature": 0.3,  # 分析需要稳定性
        "max_tokens": 2000
    },
    "agent2_element_generator": {
        "model": "qwen-max",
        "temperature": 0.5,
        "max_tokens": 3000
    },
    "agent3_page_director": {
        "model": "qwen-max",
        "temperature": 0.7,  # 设计需要创造性
        "max_tokens": 4000
    },
    "vlm_layout_optimizer": {
        "model": "qwen-vl-max",  # 如果有VLM
        "temperature": 0.4,
        "max_iterations": 3
    }
}
```

### 7.2 布局参数

```python
LAYOUT_CONFIG = {
    "page_width": 13.33,
    "page_height": 7.5,
    "min_block_spacing": 0.2,  # 最小Block间距（英寸）
    "max_blocks_per_page": 8,  # 每页最多Block数
    "split_threshold": 0.7,    # 面积占比超过70%分页
}
```

### 7.3 时序参数

```python
TIMING_CONFIG = {
    "text_speed": 3.5,         # 中文字/秒
    "formula_duration": 3.0,   # 公式停留时间
    "animation_duration": 5.0, # 动画时长
    "image_duration": 2.0,     # 图片停留
    "fade_in_duration": 0.5,   # 淡入时长
}
```

---

## 八、测试策略

### 8.1 单元测试

```python
def test_block_manager():
    """测试BlockManager"""
    pass

def test_agent3_decision():
    """测试Agent3的决策质量"""
    pass

def test_layout_optimization():
    """测试布局优化"""
    pass
```

### 8.2 集成测试

- 使用`test.json`作为标准测试用例
- 验证生成的视频是否符合预期
- 人工评审页面设计质量

### 8.3 性能测试

- 单页处理时间 < 30秒
- 完整Pipeline时间 < 10分钟（10页内容）

---

## 九、风险与挑战

### 风险1：Agent输出不稳定

**缓解措施**：
- 使用较低的temperature
- 添加输出验证和fallback逻辑
- 迭代优化Prompt

### 风险2：VLM排版效果差

**缓解措施**：
- 提供详细的约束和示例
- 限制调整范围（如只允许移动，不允许大幅缩放）
- 人工审核选项

### 风险3：Block级动画实现复杂

**缓解措施**：
- 先实现静态版本（方案A）
- 逐步升级到动画版本（方案C）
- 提供配置选项切换

---

## 十、后续扩展

### 扩展1：更多页面原子

- Interactive Quiz（交互式测验）
- Timeline（时间轴）
- Comparison Table（对比表格）

### 扩展2：样式学习

- 从示例PPT学习样式
- 用户自定义主题

### 扩展3：多模态输入

- 支持PDF、Markdown输入
- 语音输入转文稿

---

## 总结

这个升级方案是**完全可行**的，核心优势：

✅ **模块化设计**：Agent、BlockManager、LayoutEngine独立，易于开发和测试  
✅ **渐进式实现**：可以先实现基础功能，再逐步增强  
✅ **向后兼容**：保留原有数据结构，新旧并存  
✅ **可配置**：通过配置文件控制行为  

关键成功因素：
1. **Prompt工程**：Agent3的Prompt质量直接决定效果
2. **时序同步**：Block级时序对齐需要精细调试
3. **迭代优化**：需要多轮测试和调整

**建议优先级**：
1. 先实现Agent3（页面导演）- 这是核心
2. 再实现BlockManager（块管理）
3. 最后增强VideoComposer（块级动画）

---

*文档版本: 1.0*  
*最后更新: 2026-01-25*



