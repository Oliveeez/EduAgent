# Multi-Agent PPT增强方案（完整版）

## 新增功能补充

### 功能1: 块级时序对齐（Block-Level Timing Alignment）

**需求**：字幕和语音必须与每个Block精确对齐
- Text Block：与每行文本对齐
- Image Block：与图片显示对齐
- Code Block：与代码块对齐
- Formula Block：与公式对齐
- Manim Block：与动画对齐

**实现位置**：
- Stage 6: TTS生成（为每个Block生成独立音频）
- Stage 7: 字幕生成（为每个Block生成字幕条目）
- Stage 8: 视频合成（按Block时序组装）

### 功能2: 文本强调样式（Text Emphasis）

**需求**：在Conceptual Statement中支持关键词加粗和标红
- LLM在Stage 1.5决策时，识别关键词并标注
- Stage 3生成PPT时，应用加粗和颜色样式
- 支持混合样式（同时加粗+标红）

---

## 完整改动清单（更新版）

### 1. 数据模型升级

**文件**: `models.py`

**新增内容**:

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any

class BlockType(Enum):
    TEXT_LINE = "text_line"
    CONCEPTUAL_STATEMENT = "conceptual_statement"
    FORMULA = "formula"
    CODE = "code"
    MANIM_RELATION = "manim_relation"
    IMAGE = "image"
    TITLE = "title"

class PageAtom(Enum):
    CONCEPTUAL_STATEMENT = "conceptual_statement"
    FORMULA_FOCUS = "formula_focus"
    CODE_WALKTHROUGH = "code_walkthrough"
    RELATIONAL_VISUALIZATION = "relational_visualization"
    CONCEPT_WITH_VISUAL = "concept_with_visual"

class PageIntent(Enum):
    """页面意图（Intent Layer）- 教学叙事中的作用"""
    INTRODUCE_CONCEPT = "introduce_concept"       # 引入新概念
    EXPLAIN_MECHANISM = "explain_mechanism"       # 解释原理或机制
    SHOW_RELATION = "show_relation"               # 展示概念之间的关系
    WALK_THROUGH_PROOF = "walk_through_proof"     # 逐步讲解公式或代码
    MOTIVATE_IMPORTANCE = "motivate_importance"   # 说明为什么重要

class SemanticRole(Enum):
    """Block的语义角色"""
    DEFINITION = "definition"       # 定义
    MOTIVATION = "motivation"       # 动机/重要性说明
    EXAMPLE = "example"            # 举例
    RELATION = "relation"          # 关系展示
    TRANSITION = "transition"      # 过渡
    EXPLANATION = "explanation"    # 解释
    PROOF_STEP = "proof_step"      # 证明步骤

@dataclass
class SlideStructure:
    """升级后的Slide结构"""
    # 现有字段保持不变
    slide_id: int
    slide_type: SlideType
    title: str
    text: str
    coq_code: Optional[str] = None
    formula: Optional[str] = None
    gif_path: Optional[Path] = None
    audio_path: Optional[Path] = None
    duration: Optional[float] = None
    section_title: str = ""
    estimated_duration: float = 0.0
    original_text: str = ""
    
    # 新增字段
    blocks: List[Dict] = field(default_factory=list)  # Block列表
    page_atoms: List[str] = field(default_factory=list)  # 使用的原子类型
    page_intent: Optional[str] = None  # 页面意图（PageIntent）
    needs_split: bool = False  # 是否需要分页
    manim_relation_config: Optional[Dict] = None  # 关系图配置
    image_search_queries: List[str] = field(default_factory=list)  # 图片搜索关键词

# Block结构定义（存储在blocks列表中）
# {
#     "block_id": "slide_1_block_0",
#     "block_type": "text_line",
#     "content": "大模型的不确定性是指...",
#     "position_hint": "left",
#     
#     # 核心新增：语义角色
#     "semantic_role": "definition",  # definition | motivation | example | relation | transition
#     
#     # 文本强调样式
#     "emphasis": {
#         "bold": ["不确定性", "概率分布"],  # 关键词数量 ≤ 5
#         "color": {
#             "不确定性": "red",
#             "概率分布": "blue"
#         }
#     },
#     
#     # 时序信息（Stage 1.5估计 → Stage 6修正）
#     "estimated_duration": 3.5,  # Stage 1.5认知时长估计
#     "start_time": 0.0,          # 相对于slide开始（秒）
#     "duration": 3.5,            # Stage 6物理时长修正后
#     "audio_path": "path/to/block_audio.mp3",
#     "subtitle_text": "对应的字幕文本"
# }
```

---

### 2. Stage 1.5: PageDirector Agent（增强版）

**新文件**: `stage1_5_page_director.py`

**核心功能补充**:

#### 2.1 关键词识别与标注

```python
class PageDirectorAgent:
    def _get_atom_decision(self, slide: SlideStructure) -> Dict:
        """
        调用LLM决定该slide使用哪些原子（增强版）
        """
        prompt = f"""你是PPT页面设计专家。请为以下内容选择合适的页面表现原子。

可用原子（必须选择2-3个）：
1. Conceptual Statement - 书面化概念陈述
   - 必须标注关键词（用于加粗或标红）
   - 禁止口语化（"我们"、"接下来"等）
2. Formula Focus - 公式展示
3. Code Walkthrough - 代码讲解
4. Relational Visualization - 关系图/函数图
5. Concept + Visual - 概念+图片

当前内容：
标题: {slide.title}
文本: {slide.text}
公式: {slide.formula or "无"}
代码: {slide.coq_code or "无"}

硬约束：
- 至少选择2种原子
- 如果选择Conceptual Statement，必须：
  1. 将文本改写为书面化陈述
  2. 标注关键概念词（用于加粗）
  3. 标注核心术语（用于标红）

返回JSON格式：
{{
  "atoms": ["Conceptual Statement", "Formula Focus"],
  "reasoning": "选择理由",
  
  "conceptual_statements": [
    {{
      "content": "大模型的不确定性（uncertainty）是指模型在既定训练分布基础上，在生成或预测过程中，对输入样本'知道'或'不知道'的程度。",
      "emphasis": {{
        "bold": ["不确定性", "训练分布", "知道", "不知道"],
        "color": {{
          "不确定性": "red"
        }}
      }}
    }},
    {{
      "content": "该概念通常体现为模型内部概率分布的离散性、不同候选输出之间的不一致性，或模型自身知识覆盖范围的不完整性。",
      "emphasis": {{
        "bold": ["概率分布", "离散性", "不一致性", "不完整性"],
        "color": {{}}
      }}
    }}
  ],
  
  "manim_config": null,
  "needs_image": false
}}
"""
        
        response = self.llm(prompt)
        return self._parse_llm_response(response)
    
    def _generate_blocks(self, slide: SlideStructure, decision: Dict) -> List[Dict]:
        """
        根据决策生成blocks列表（增强版）
        """
        blocks = []
        
        # 1. Conceptual Statement - 逐行生成，带样式
        if "Conceptual Statement" in decision['atoms']:
            statements = decision.get('conceptual_statements', [])
            for idx, stmt in enumerate(statements):
                blocks.append({
                    "block_id": f"slide_{slide.slide_id}_block_{len(blocks)}",
                    "block_type": "text_line",
                    "content": stmt['content'],
                    "position_hint": "left",
                    "emphasis": stmt.get('emphasis', {}),
                    # 时序信息（后续Stage 6填充）
                    "start_time": 0.0,
                    "duration": 0.0,
                    "audio_path": None,
                    "subtitle_text": stmt['content']  # 默认用content，Stage 6可能调整
                })
        
        # 2. Formula Focus
        if "Formula Focus" in decision['atoms'] and slide.formula:
            blocks.append({
                "block_id": f"slide_{slide.slide_id}_block_{len(blocks)}",
                "block_type": "formula",
                "content": slide.formula,
                "position_hint": "right",
                "emphasis": {},
                "start_time": 0.0,
                "duration": 0.0,
                "audio_path": None,
                "subtitle_text": f"这是公式：{slide.formula[:20]}..."  # 简化描述
            })
        
        # 3. Code Walkthrough
        if "Code Walkthrough" in decision['atoms'] and slide.coq_code:
            blocks.append({
                "block_id": f"slide_{slide.slide_id}_block_{len(blocks)}",
                "block_type": "code",
                "content": slide.coq_code,
                "position_hint": "right",
                "emphasis": {},
                "start_time": 0.0,
                "duration": 0.0,
                "audio_path": None,
                "subtitle_text": "以下是代码示例"
            })
        
        # 4. Relational Visualization
        if "Relational Visualization" in decision['atoms']:
            blocks.append({
                "block_id": f"slide_{slide.slide_id}_block_{len(blocks)}",
                "block_type": "manim_relation",
                "content": decision.get('manim_config', {}),
                "position_hint": "right",
                "emphasis": {},
                "start_time": 0.0,
                "duration": 0.0,
                "audio_path": None,
                "subtitle_text": decision.get('manim_config', {}).get('description', '关系图')
            })
        
        # 5. Concept + Visual
        if "Concept + Visual" in decision['atoms'] and decision.get('image_url'):
            blocks.append({
                "block_id": f"slide_{slide.slide_id}_block_{len(blocks)}",
                "block_type": "image",
                "content": decision['image_url'],
                "position_hint": "right",
                "emphasis": {},
                "start_time": 0.0,
                "duration": 0.0,
                "audio_path": None,
                "subtitle_text": decision.get('image_search_query', '示例图片')
            })
        
        return blocks
```

---

### 3. Stage 3: PPTXGenerator（支持文本样式）

**文件**: `stage3_pptx_generator.py`

**改动内容**:

```python
class PPTXGenerator:
    def _add_text_block(self, slide, block: Dict):
        """
        添加单行文本框（支持强调样式）
        
        Args:
            block: {
                "content": "大模型的不确定性是指...",
                "emphasis": {
                    "bold": ["不确定性"],
                    "color": {"不确定性": "red"}
                }
            }
        """
        content = block['content']
        emphasis = block.get('emphasis', {})
        
        # 创建文本框
        text_box = slide.shapes.add_textbox(
            Inches(self.CONTENT_LEFT),
            Inches(self.current_left_y),
            Inches(self.TEXT_WIDTH),
            Inches(0.5)
        )
        text_frame = text_box.text_frame
        text_frame.word_wrap = True
        
        # 如果没有强调样式，直接设置文本
        if not emphasis or (not emphasis.get('bold') and not emphasis.get('color')):
            text_frame.text = content
            self._format_text_run(text_frame.paragraphs[0].runs[0])
            return
        
        # 有强调样式：逐词处理
        bold_words = set(emphasis.get('bold', []))
        color_map = emphasis.get('color', {})
        
        # 分词并应用样式
        para = text_frame.paragraphs[0]
        
        # 简单策略：按关键词分割
        remaining = content
        first = True
        
        for keyword in bold_words:
            if keyword in remaining:
                # 分割：keyword前 + keyword + keyword后
                parts = remaining.split(keyword, 1)
                
                # 添加keyword前的部分
                if parts[0]:
                    run = para.add_run() if not first else para.runs[0]
                    run.text = parts[0]
                    self._format_text_run(run, bold=False, color=None)
                    first = False
                
                # 添加keyword（带样式）
                run = para.add_run()
                run.text = keyword
                keyword_color = color_map.get(keyword)
                self._format_text_run(
                    run, 
                    bold=True, 
                    color=keyword_color
                )
                
                # 更新remaining
                remaining = parts[1] if len(parts) > 1 else ""
        
        # 添加剩余部分
        if remaining:
            run = para.add_run()
            run.text = remaining
            self._format_text_run(run, bold=False, color=None)
        
        self.current_left_y += 0.5
    
    def _format_text_run(self, run, bold=False, color=None):
        """格式化文本run"""
        run.font.name = '微软雅黑'
        run.font.size = Pt(18)
        
        if bold:
            run.font.bold = True
        
        if color:
            color_rgb = self._parse_color(color)
            run.font.color.rgb = color_rgb
        else:
            run.font.color.rgb = RGBColor(0, 0, 0)
    
    def _parse_color(self, color_name: str) -> RGBColor:
        """解析颜色名称为RGB"""
        color_map = {
            "red": RGBColor(192, 0, 0),      # 深红色
            "blue": RGBColor(0, 0, 128),     # 深蓝色
            "green": RGBColor(0, 100, 0),    # 深绿色
            "orange": RGBColor(255, 140, 0), # 橙色
        }
        return color_map.get(color_name, RGBColor(0, 0, 0))
```

---

### 4. Stage 6: TTSGenerator（块级音频生成）

**文件**: `stage6_tts_generator.py`

**改动内容**:

```python
class TTSGenerator:
    """TTS生成器（块级音频支持）"""
    
    def generate_all(self, slides: List[SlideStructure]) -> List[SlideStructure]:
        """
        为所有slides生成TTS音频（块级）
        
        新逻辑：
        1. 为每个slide的每个block生成独立音频
        2. 记录每个block的audio_path和实际duration
        3. 计算block的start_time（累加）
        """
        print("  🎤 开始生成TTS音频（块级）...")
        
        for slide in slides:
            if not slide.blocks:
                # 回退到旧逻辑（整页音频）
                self._generate_slide_audio_legacy(slide)
                continue
            
            # 新逻辑：逐block生成
            slide_start_time = 0.0
            
            for block_idx, block in enumerate(slide.blocks):
                # 获取该block的语音文本
                audio_text = block.get('subtitle_text') or block.get('content', '')
                
                if not audio_text or block['block_type'] in ['formula', 'code', 'image']:
                    # 非语音block（公式/代码/图片），只分配时长
                    block['start_time'] = slide_start_time
                    block['duration'] = self._estimate_block_duration(block)
                    block['audio_path'] = None
                    slide_start_time += block['duration']
                    continue
                
                # 生成音频
                audio_path = self.audio_dir / f"slide_{slide.slide_id}_block_{block_idx}.mp3"
                success = self._generate_audio(audio_text, audio_path)
                
                if success:
                    # 获取实际音频时长
                    actual_duration = self._get_audio_duration(audio_path)
                    
                    # 更新block信息
                    block['audio_path'] = str(audio_path)
                    block['duration'] = actual_duration
                    block['start_time'] = slide_start_time
                    
                    slide_start_time += actual_duration
                else:
                    # 生成失败，使用估算时长
                    block['start_time'] = slide_start_time
                    block['duration'] = len(audio_text) / 3.5
                    block['audio_path'] = None
                    slide_start_time += block['duration']
            
            # 更新slide总时长
            slide.duration = slide_start_time
            
            print(f"    Slide {slide.slide_id}: {len(slide.blocks)} blocks, 总时长 {slide.duration:.1f}秒")
        
        return slides
    
    def _estimate_block_duration(self, block: Dict) -> float:
        """估算非语音block的时长"""
        block_type = block['block_type']
        
        if block_type == 'formula':
            return 3.0  # 公式停留3秒
        elif block_type == 'code':
            lines = block['content'].count('\n') + 1
            return lines * 0.5  # 每行代码0.5秒
        elif block_type == 'manim_relation':
            return 5.0  # 动画5秒
        elif block_type == 'image':
            return 2.0  # 图片2秒
        else:
            return 2.0
    
    def merge_audio(self, slides: List[SlideStructure]) -> Path:
        """
        合并所有音频（块级版本）
        
        新逻辑：
        1. 按时序收集所有block的音频
        2. 对于没有音频的block（公式/代码/图片），插入静音
        3. 合并为完整音频
        """
        audio_segments = []
        
        # 封面静音3秒
        from pydub import AudioSegment
        cover_silence = AudioSegment.silent(duration=3000)
        audio_segments.append(cover_silence)
        
        for slide in slides:
            for block in slide.blocks:
                audio_path = block.get('audio_path')
                duration_ms = int(block['duration'] * 1000)
                
                if audio_path and Path(audio_path).exists():
                    # 加载block音频
                    audio = AudioSegment.from_mp3(audio_path)
                    audio_segments.append(audio)
                else:
                    # 插入静音
                    silence = AudioSegment.silent(duration=duration_ms)
                    audio_segments.append(silence)
        
        # 合并所有音频
        final_audio = sum(audio_segments)
        
        # 保存
        output_path = self.audio_dir / "merged_audio.mp3"
        final_audio.export(str(output_path), format="mp3")
        
        print(f"  ✅ 音频合并完成，总时长 {len(final_audio)/1000:.1f}秒")
        return output_path
```

---

### 5. Stage 7: SubtitleGenerator（块级字幕生成）

**文件**: `stage7_subtitle_generator.py`

**改动内容**:

```python
class SubtitleGenerator:
    """字幕生成器（块级对齐）"""
    
    def generate(self, slides: List[SlideStructure]) -> Path:
        """
        生成字幕文件（块级对齐）
        
        新逻辑：
        1. 遍历所有block
        2. 每个block生成一个或多个字幕条目
        3. 时间戳精确对齐block的start_time和duration
        """
        print("  📝 开始生成字幕（块级对齐）...")
        
        subtitles = []
        subtitle_index = 1
        
        # 封面字幕（0-3秒）
        cover_title = slides[0].section_title if slides else "教学课件"
        subtitles.append(SubtitleEntry(
            index=subtitle_index,
            start_time=0.0,
            end_time=3.0,
            text=cover_title
        ))
        subtitle_index += 1
        
        # 计算全局时间偏移（封面3秒）
        global_time_offset = 3.0
        
        # 遍历所有slides和blocks
        for slide in slides:
            slide_start_time = global_time_offset
            
            for block in slide.blocks:
                # 计算block的绝对时间
                block_start = slide_start_time + block['start_time']
                block_end = block_start + block['duration']
                
                # 获取字幕文本
                subtitle_text = block.get('subtitle_text') or block.get('content', '')
                
                # 如果字幕太长，分割为多个条目
                if len(subtitle_text) > 40:
                    # 简单策略：按句号分割
                    sentences = subtitle_text.split('。')
                    sentence_duration = block['duration'] / len(sentences)
                    
                    for i, sentence in enumerate(sentences):
                        if not sentence.strip():
                            continue
                        
                        sub_start = block_start + i * sentence_duration
                        sub_end = min(sub_start + sentence_duration, block_end)
                        
                        subtitles.append(SubtitleEntry(
                            index=subtitle_index,
                            start_time=sub_start,
                            end_time=sub_end,
                            text=sentence.strip() + '。'
                        ))
                        subtitle_index += 1
                else:
                    # 短文本，整体作为一个字幕条目
                    subtitles.append(SubtitleEntry(
                        index=subtitle_index,
                        start_time=block_start,
                        end_time=block_end,
                        text=subtitle_text
                    ))
                    subtitle_index += 1
            
            # 更新全局时间偏移
            global_time_offset += slide.duration
        
        # 保存SRT文件
        output_path = self.subtitle_dir / "subtitles.srt"
        with open(output_path, 'w', encoding='utf-8') as f:
            for sub in subtitles:
                f.write(sub.to_srt_format())
                f.write('\n')
        
        print(f"  ✅ 字幕生成完成，共 {len(subtitles)} 条")
        return output_path
```

---

### 6. Stage 8: VideoComposer（块级动画同步）

**文件**: `stage8_video_composer.py`

**改动内容**:

```python
class VideoComposer:
    """视频合成器（块级动画支持）"""
    
    def _record_pptx_playback(self, pptx_path: Path, slides: List[SlideStructure], 
                              total_duration: float, cover_duration: float = 3.0) -> Optional[Path]:
        """
        使用Xvfb + LibreOffice Impress + FFmpeg录制PPTX放映（块级控制）
        
        新逻辑：
        1. 启动放映后，按block时序控制动画
        2. 对于每个block，模拟点击或键盘事件触发显示
        3. 确保每个block的显示时机与音频/字幕对齐
        """
        # ... 前面的Xvfb和LibreOffice启动逻辑保持不变 ...
        
        # Step 4: 控制翻页和块级动画（新逻辑）
        print("      📄 控制翻页和块级动画...")
        
        # 封面页等待
        print(f"        封面页: 等待 {cover_duration:.1f}秒")
        time.sleep(cover_duration)
        
        # 翻到第一个内容页
        print("        翻到第1页...")
        subprocess.run(["xdotool", "key", "Right"], env=env, capture_output=True)
        time.sleep(0.3)
        
        # 遍历所有slides和blocks
        for slide_idx, slide in enumerate(slides):
            print(f"        Slide {slide_idx+1}:")
            
            # 如果该slide使用了块级动画（有多个blocks）
            if slide.blocks:
                for block_idx, block in enumerate(slide.blocks):
                    block_duration = block['duration']
                    block_type = block['block_type']
                    
                    print(f"          Block {block_idx+1} ({block_type}): 等待 {block_duration:.1f}秒")
                    
                    # 触发该block显示（模拟点击或按键）
                    # 注意：这需要PPT支持逐元素动画
                    # 可以在Stage 3生成PPT时为每个block设置"点击触发"动画
                    if block_idx > 0:  # 第一个block自动显示
                        subprocess.run(["xdotool", "click", "1"], env=env, capture_output=True)
                        time.sleep(0.2)
                    
                    # 等待该block的时长
                    time.sleep(block_duration)
            else:
                # 没有blocks，使用整页时长
                duration = slide.duration or 5.0
                print(f"          整页: 等待 {duration:.1f}秒")
                time.sleep(duration)
            
            # 翻到下一页
            if slide_idx < len(slides) - 1:
                print(f"        翻到第{slide_idx+2}页...")
                subprocess.run(["xdotool", "key", "Right"], env=env, capture_output=True)
                time.sleep(0.3)
        
        # 最后一页再等待1秒
        time.sleep(1)
        
        print("      ✅ 录制完成")
        
        # ... 后续清理和截取逻辑保持不变 ...
```

**关键改进**：为了支持块级动画，需要在Stage 3生成PPT时为每个block设置动画效果：

```python
# 在stage3_pptx_generator.py中添加
class PPTXGenerator:
    def _add_content_slide(self, slide_data: SlideStructure):
        """添加内容页（支持块级动画）"""
        slide = self.prs.slides.add_slide(self.blank_layout)
        
        # ... 添加标题 ...
        
        # 遍历blocks并添加元素
        shapes_added = []
        for block in slide_data.blocks:
            shape = self._add_block_element(slide, block)
            if shape:
                shapes_added.append(shape)
        
        # 为每个元素设置动画（从第二个开始设置"点击触发"）
        if len(shapes_added) > 1:
            self._add_click_animations(slide, shapes_added)
    
    def _add_click_animations(self, slide, shapes: List):
        """
        为shapes添加点击触发动画
        
        注意：python-pptx不直接支持动画，需要操作XML
        """
        # 获取slide的XML
        from pptx.oxml import parse_xml
        
        # 构建动画序列XML
        for idx, shape in enumerate(shapes[1:], start=1):  # 跳过第一个
            # 添加entrance动画（淡入效果）
            # XML结构：
            # <p:timing>
            #   <p:tnLst>
            #     <p:par>
            #       <p:cTn ...>
            #         <p:stCondLst>
            #           <p:cond evt="onClick" .../>
            #         </p:stCondLst>
            #       </p:cTn>
            #     </p:par>
            #   </p:tnLst>
            # </p:timing>
            
            # 简化方案：使用pptx库的低级API
            # 这部分较复杂，可能需要使用python-pptx-interface或直接操作XML
            pass
```

**注意**：由于python-pptx对动画支持有限，可能需要：
1. 使用`python-pptx-interface`库（提供更多动画支持）
2. 或者直接操作OOXML（较复杂）
3. 或者在视频合成阶段手动控制块的显示时机（通过FFmpeg滤镜）

---

## 更新后的TODO列表

### Phase 1: 数据模型和Agent决策（3-4天）
1. 修改`models.py`：添加BlockType、PageAtom枚举和blocks字段
2. 实现`stage1_5_page_director.py`：
   - Agent决策核心逻辑
   - 关键词识别和emphasis标注
   - Block生成逻辑
3. 实现ImageSearcher（集成Unsplash API）

### Phase 2: PPT生成增强（2-3天）
4. 修改`stage3_pptx_generator.py`：
   - 基于blocks生成PPT元素（每个block独立元素）
   - 支持文本强调样式（逐词处理，加粗+颜色）
   - Image Block作为二等公民（不能单独成页）
   - （可选）添加块级点击动画

### Phase 3: Manim增强（2天）
5. 增强`stage2_manim_renderer.py`：
   - 支持关系图渲染（function_plot、directed_graph、flowchart）

### Phase 4: 音频和字幕块级对齐（3-4天）⭐核心
6. 修改`stage6_tts_generator.py`：
   - 块级音频生成
   - **物理时长修正**（Stage 1.5的estimated_duration → 实际duration）
   - 合并音频时处理静音块
7. 修改`stage7_subtitle_generator.py`：
   - 块级字幕生成
   - 时间戳精确对齐
   - 长文本自动分割

### Phase 5: 视频合成增强（2-3天）
8. 修改`stage8_video_composer.py`：
   - 块级时序控制
   - 支持逐block触发动画

### Phase 6: 自动分页和集成（2天）
9. 增强`stage5_vlm_optimizer.py`：自动分页功能
10. 更新`main_pipeline.py`：集成Stage 1.5

### Phase 7: 测试和优化（2-3天）
11. 端到端测试：使用test.json验证完整流程
12. Prompt调优：优化Agent决策质量
13. 性能优化和错误处理

**总计：17-24天**（因范式级重构增加1-2天）

---

## 核心设计理念

### 设计理念1: Block是"时间与认知单位"，不是UI结构

Block不仅定义"PPT上放什么元素"，更重要的是定义：
- **认知单位**：一个完整的教学信息片段
- **时序单位**：一个独立的时间片段（可配音、可字幕、可控制出现）

### 设计理念2: Intent Layer（意图层）

在传统的"内容→原子→Block"流程中插入意图层：
```
内容 → 意图判别 → 原子选择 → Block生成
      (Intent)
```

这确保每页都有明确的教学目的，而不是机械地拼凑元素。

### 设计理念3: Planner/Executor分离

- **Planner**：专注结构正确（what & why）
- **Executor**：专注语言质量（how & polish）

这避免了"一次prompt干所有事"导致的质量不稳定。

### 设计理念4: 结构不可逃逸（Schema Lock）

通过validate_plan函数强制约束：
- page_intent必须合法
- 至少2个blocks
- 每个block必须有semantic_role
- Image不能单独成页（二等公民）

### 设计理念5: 编译管线（只读合同）

```
Stage 1.5: blocks = WHAT & WHEN & WHY
Stage 3:   blocks → WHERE & HOW (PPT)
Stage 6:   blocks → SOUND & TIME (物理时长修正)
Stage 7:   blocks → TEXT & TIME (字幕)
Stage 8:   blocks → VIDEO & TIME (合成)
```

每个Stage只"消费"blocks结构，不"理解"教学内容。

## 关键技术点

### 1. 块级时序对齐的数据流（两阶段时长估计）

```
Stage 1.5 → 生成blocks（estimated_duration=认知时长估计）
    ↓
Stage 6 → 为每个block生成音频，物理时长修正（duration=实际时长）
    ↓
Stage 7 → 基于block的start_time和duration生成字幕
    ↓
Stage 8 → 按block时序控制视频录制或合成
```

**关键**：estimated_duration在Stage 1.5由Planner估算（基于认知负荷），duration在Stage 6由TTS实测。

### 2. 文本强调样式的处理流程（关键词数量≤5）

```
Stage 1.5 Executor → LLM识别关键词，生成emphasis字段（最多5个）
                     - bold: 关键概念词
                     - color: 核心术语（0-2个，标红）
    ↓
Stage 3 → 在PPT中应用加粗和颜色样式（逐词处理）
    ↓
视频中显示 → 用户看到标红加粗的关键词
```

**约束**：关键词过多会干扰阅读，强制≤5个。

### 3. 块级动画的两种实现方案

**方案A（推荐）**：PPT点击动画
- Stage 3生成PPT时，为每个block设置"点击触发"的淡入动画
- Stage 8录制时，模拟点击事件触发每个block显示
- 优点：动画效果好，与PPT原生行为一致
- 缺点：python-pptx对动画支持有限，需要XML操作

**方案B（备用）**：FFmpeg滤镜叠加
- Stage 8不使用PPT放映，而是：
  1. 导出每个slide为静态背景图
  2. 使用FFmpeg的drawtext和overlay滤镜逐个叠加blocks
  3. 根据block的start_time控制显示时机
- 优点：完全可控，无需处理PPT动画
- 缺点：实现复杂，动画效果可能不如原生PPT

---

### 3. PageIntent驱动的决策逻辑

```
introduce_concept → 大概率选择 Conceptual Statement + Visual
motivate_importance → Concept + Visual（图片强化重要性）
explain_mechanism → Conceptual Statement + Relational Visualization
show_relation → Relational Visualization必选
walk_through_proof → Formula/Code + Conceptual Statement
```

**示例**：孙子算经页面
- Intent: motivate_importance + show_relation
- Atoms: Conceptual Statement + Concept + Visual
- Blocks:
  1. [text] 定义：鸡兔同笼问题（definition）
  2. [text] 为什么重要：形式化验证的典型案例（motivation）
  3. [image] 孙子算经插图（example，语境强化）
  4. [formula] 方程组（relation）

## 风险与缓解

**风险1**: LLM Planner决策不稳定
- 缓解：使用范式级Prompt（Planning Contract），固定决策框架
- 缓解：Schema Lock验证，不合格计划reject重采样
- Fallback：返回默认计划（introduce_concept + Conceptual Statement）

**风险2**: LLM Executor识别关键词不准确
- 缓解：提供Few-shot示例，明确什么是"关键概念词"（≤5个）
- 缓解：在Executor的prompt中强调"关键词数量≤5"
- Fallback：如果LLM未返回emphasis，不添加强调样式

**风险3**: 块级音频时长与认知估算差异大
- 缓解：两阶段时长估计（Stage 1.5认知估算 → Stage 6物理修正）
- 缓解：使用实际TTS时长，动态调整后续blocks的start_time
- 影响：可能导致视频总时长略有变化（但更符合实际）

**风险4**: PPT点击动画实现困难
- 缓解：如果python-pptx无法实现，改用方案B（FFmpeg滤镜）
- 或者：使用LibreOffice的宏命令控制动画

**风险5**: 字幕分割逻辑不完善
- 缓解：支持多种分割策略（按标点、按字数、按时长）
- 人工审核：提供字幕编辑接口

**风险6**: Image Block被滥用（违反二等公民原则）
- 缓解：在validate_plan中强制约束（Image不能单独成页）
- 缓解：在Planner的prompt中明确"Image只能作为语境强化"

---

## 总结

此方案在原有方案基础上实现了**范式级重构**：

### 核心创新

1. **Intent Layer（意图层）**：
   - 引入PageIntent枚举（5种教学意图）
   - 从"内容→原子"升级为"内容→意图→原子→Block"

2. **Planner/Executor分离**：
   - PagePlanner：专注结构正确（决策page_intent、page_atoms、block blueprint）
   - BlockExecutor：专注语言质量（生成具体文本和emphasis）

3. **Block作为认知与时序单位**：
   - 每个Block = 独立教学片段 + 独立时间片段
   - semantic_role标注（definition/motivation/example/relation/transition）
   - 两阶段时长估计（认知估算 → 物理修正）

4. **结构不可逃逸（Schema Lock）**：
   - validate_plan强制约束
   - Image Block作为二等公民
   - 关键词数量≤5

5. **块级时序对齐**：
   - Stage 6为每个block生成独立音频
   - Stage 7基于block时序生成字幕
   - Stage 8按block时序控制视频录制

6. **文本强调样式**：
   - BlockExecutor识别关键词（最多5个）
   - Stage 3逐词应用加粗+颜色
   - 支持混合样式

### 改动文件

- **新增**：`stage1_5_page_director.py`（含PagePlanner和BlockExecutor）
- **修改**：`models.py`, `stage2_manim_renderer.py`, `stage3_pptx_generator.py`, `stage5_vlm_optimizer.py`, `stage6_tts_generator.py`, `stage7_subtitle_generator.py`, `stage8_video_composer.py`, `main_pipeline.py`
- **总计**：1个新增，8个修改

### 预计工作量

**17-24天**（范式级重构增加1-2天）

### 技术债务

- PPT点击动画（可能需要XML操作或FFmpeg方案）
- Unsplash API配额管理
- LLM输出稳定性（需要多轮prompt调优）

