# stage1_slide_builder.py
# Stage 1: Slide结构体生成和格式化

import re
import json
from typing import List, Optional
from pathlib import Path

from .models import SlideStructure, SlideType


class SlideBuilder:
    """
    Slide结构体生成器
    
    功能：
    1. 将演讲稿口语化内容转换为PPT结构化要点
    2. 去除重复内容（如果有公式/代码，text不重复）
    3. 生成/优化标题
    4. 估算讲解时长
    """
    
    def __init__(self, slides: List[SlideStructure], use_llm: bool = True):
        """
        初始化
        
        Args:
            slides: 从Stage 0解析得到的slides列表
            use_llm: 是否使用LLM优化内容
        """
        self.slides = slides
        self.use_llm = use_llm
        self.llm = None
        
        if use_llm:
            try:
                import sys
                sys.path.insert(0, str(Path(__file__).parent.parent.parent))
                from utils.llm import CustomLLM
                self.llm = CustomLLM()
            except Exception as e:
                print(f"  ⚠️ LLM初始化失败: {e}, 将使用规则处理")
                self.use_llm = False
    
    def build(self) -> List[SlideStructure]:
        """
        处理所有slides
        
        Returns:
            处理后的slides列表
        """
        processed = []
        
        for slide in self.slides:
            processed_slide = self._process_slide(slide)
            processed.append(processed_slide)
        
        return processed
    
    def _process_slide(self, slide: SlideStructure) -> SlideStructure:
        """
        处理单个slide
        
        Args:
            slide: 原始slide
        
        Returns:
            处理后的slide
        """
        # 1. 保存原始演讲稿文本（用于TTS和字幕）
        slide.original_text = slide.text
        
        # 2. 清理代码/公式
        if slide.coq_code:
            slide.coq_code = self._clean_code(slide.coq_code)
        if slide.formula:
            slide.formula = self._clean_formula(slide.formula)
        
        # 3. 基础文本处理（Stage 1.5 的 PageDirector 会重新规划 blocks）
        # 注意：不再调用 _plan_pedagogical_visuals，避免与 Stage 1.5 冲突
        slide.text = self._rule_based_convert(slide)
        
        # 4. 优化标题
        slide.title = self._optimize_title(slide.title, slide.text, slide.section_title)
        
        # 5. 基于原始文本估算时长
        slide.estimated_duration = self._estimate_duration(slide)
        
        return slide
    
    def _plan_pedagogical_visuals(self, slide: SlideStructure):
        """
        Agent3: 教学型页面导演 (Pedagogical Visual Planner)
        
        规划每一页的表现原子组合，包括概念陈述、公式展示、代码讲解和关系图。
        """
        original_text = slide.text
        
        prompt = f"""你是一个教学型 PPT 页面设计导演，你的目标是为每一页选择最合适的知识表达形式。
你必须保证页面内容具有学术严谨性、视觉多样性和教学有效性。

你可以使用的页面表现原子包括：
1. **Conceptual Statement（概念陈述文本）**
   - 必须是书面化、完整、可独立成立的陈述。
   - 禁止使用口语化引导语（如“我们先看”、“接下来我们可以看到”、“这个例子能帮助理解”）。
   - 功能：直接承载“知识本体”。
   - 支持关键词强调（加粗/着色）。

2. **Formula Focus（公式展示）**
   - 公式必须完整。
   - 若涉及“方程组 / 系统 / 联立”，需明确表达系统关系。

3. **Code Walkthrough（代码讲解）**
   - 代码页必须至少搭配一条 Conceptual Statement。

4. **Relational / Structural Visualization（关系 / 结构可视化）**
   - 使用 Manim 原生图形元素（箭头、集合、函数图像、流程框）表达逻辑关系。
   - 禁止使用网络图片。

5. **Concept + Visual（概念 + 图示）**
   - 寻找合适的在线图片（如具体的历史对象、举例应用领域）。

页面设计硬约束：
- 每页至少包含 2 种不同表现原子。
- 禁止 bullet point 风格主导页面。
- 禁止只有文本或只有公式的页面。

当前输入信息：
演讲稿文本：
{original_text}

{f"该页包含 LaTeX 公式: {slide.formula}" if slide.formula else ""}
{f"该页包含代码块: {slide.coq_code}" if slide.coq_code else ""}

请输出 JSON 格式（不要输出任何其他文字）：
{{
  "atoms": [
    {{
      "type": "conceptual_statement",
      "content": "完整的书面化陈述内容",
      "emphasis": {{
        "bold": ["关键术语1", "关键术语2"],
        "color": {{"关键术语1": "red"}}
      }}
    }},
    {{
      "type": "relational_visualization",
      "content": "描述需要展现的逻辑关系或函数行为",
      "manim_type": "function_plot/arrow_flow/dependency_map"
    }},
    {{
      "type": "formula",
      "content": "公式内容"
    }}
  ]
}}
"""
        try:
            from .models import SlideBlock
            response = self.llm(prompt)
            # 提取 JSON 部分
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                slide.blocks = []
                # 重新组合文本用于 PPT 显示
                text_parts = []
                
                for atom in data.get("atoms", []):
                    block = SlideBlock(
                        block_type=atom["type"],
                        content=atom["content"],
                        emphasis=atom.get("emphasis")
                    )
                    slide.blocks.append(block)
                    
                    if atom["type"] == "conceptual_statement":
                        text_parts.append(atom["content"])
                
                slide.text = "\n".join(text_parts)
            else:
                # 回退
                slide.text = self._rule_based_convert(slide)
        except Exception as e:
            print(f"    ⚠️ Agent3 规划失败: {e}")
            slide.text = self._rule_based_convert(slide)

    def _convert_to_bullet_points(self, slide: SlideStructure) -> str:
        # 该方法已在 _process_slide 中被 _plan_pedagogical_visuals 替代，保留以防万一
        return self._rule_based_convert(slide)

    def _rule_based_convert(self, slide: SlideStructure) -> str:
        """
        基于规则将演讲稿转换为PPT要点（不使用LLM时的备选方案）
        
        Args:
            slide: slide结构体
        
        Returns:
            结构化的PPT要点内容
        """
        text = slide.text
        
        # 1. 去除口语化表达
        oral_patterns = [
            r'大家[一定都]*', r'同学们', r'你们', r'我们',
            r'我来[^，。]+[，。]', r'我想[^，。]+[，。]',
            r'（停顿）', r'听起来[^，。]+[，。]',
            r'是不是[^？]+[？]', r'对吧[？]?',
            r'别担心[，。]?', r'好了[，。]',
        ]
        for pattern in oral_patterns:
            text = re.sub(pattern, '', text)
        
        # 2. 如果有公式/代码，去除text中的重复内容
        if slide.formula:
            # 去除公式本身
            for formula in slide.formula.split('\n'):
                text = text.replace(formula, '')
        if slide.coq_code:
            # 去除代码本身
            for line in slide.coq_code.split('\n'):
                text = text.replace(line.strip(), '')
        
        # 3. 提取关键句子
        sentences = re.split(r'[。！？]', text)
        key_points = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 10:
                continue
            
            # 去除开头的连接词
            sentence = re.sub(r'^[而且并且所以因此但是然而其实实际上]+', '', sentence)
            sentence = sentence.strip()
            
            if sentence and len(sentence) >= 10:
                # 截断过长的句子
                if len(sentence) > 50:
                    sentence = sentence[:50] + "..."
                key_points.append(sentence)
        
        # 限制要点数量
        key_points = key_points[:5]
        
        return '\n'.join(key_points) if key_points else text[:100]
    
    def _clean_text(self, text: str) -> str:
        """
        清理讲解文本
        
        移除：
        - Markdown符号
        - HTML标签
        - 多余空白
        
        Args:
            text: 原始文本
        
        Returns:
            清理后的文本
        """
        if not text:
            return ""
        
        # 移除HTML标签
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', text)
        
        # 移除Markdown标题标记
        text = re.sub(r'#{1,6}\s*', '', text)
        
        # 移除加粗/斜体标记
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'__([^_]+)__', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)
        
        # 移除代码标记（保留内容）
        text = re.sub(r'`([^`]+)`', r'\1', text)
        
        # 移除特殊标记（之前的code/formula标记可能残留）
        text = re.sub(r'【代码】', '', text)
        
        # 清理多余空白
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        text = text.strip()
        
        return text
    
    def _clean_code(self, code: str) -> str:
        """
        清理代码
        
        Args:
            code: 原始代码
        
        Returns:
            清理后的代码
        """
        if not code:
            return ""
        
        # 移除首尾空白
        code = code.strip()
        
        # 统一换行符
        code = code.replace('\r\n', '\n').replace('\r', '\n')
        
        # 移除过多的连续空行
        code = re.sub(r'\n{3,}', '\n\n', code)
        
        return code
    
    def _clean_formula(self, formula: str) -> str:
        """
        清理公式
        
        Args:
            formula: 原始公式
        
        Returns:
            清理后的公式
        """
        if not formula:
            return ""
        
        formula = formula.strip()
        
        # 移除可能的$符号（MathTex不需要）
        formula = formula.strip('$')
        
        return formula
    
    def _optimize_title(self, title: str, text: str, section_title: str) -> str:
        """
        优化标题 - 使用section_title作为主标题
        
        策略：
        1. 优先使用section_title（去除序号）
        2. 如果section_title太长，提取副标题部分
        
        Args:
            title: 当前标题（不使用）
            text: 讲解文本（不使用）
            section_title: 章节标题
        
        Returns:
            优化后的标题
        """
        if not section_title:
            return "内容页"
        
        # 移除序号
        clean_title = re.sub(r'^\d+[\.\、]\s*', '', section_title)
        
        # 提取副标题（如果有冒号分隔）
        if '：' in clean_title:
            parts = clean_title.split('：')
            main_part = parts[0].strip()
            sub_part = parts[1].strip() if len(parts) > 1 else ""
            
            # 如果主部分太长，用副部分
            if len(main_part) <= 15:
                return main_part
            elif sub_part and len(sub_part) <= 20:
                return sub_part
            else:
                return main_part[:15]
        
        if ':' in clean_title:
            parts = clean_title.split(':')
            main_part = parts[0].strip()
            sub_part = parts[1].strip() if len(parts) > 1 else ""
            
            if len(main_part) <= 15:
                return main_part
            elif sub_part and len(sub_part) <= 20:
                return sub_part
            else:
                return main_part[:15]
        
        # 直接使用清理后的标题
        if len(clean_title) <= 20:
            return clean_title
        
        return clean_title[:18] + "..."
    
    def _estimate_duration(self, slide: SlideStructure) -> float:
        """
        估算slide讲解时长
        
        基于：
        - 文本长度（中文3.5字/秒）
        - 代码/公式复杂度
        
        Args:
            slide: slide结构体
        
        Returns:
            估算时长（秒）
        """
        duration = 0.0
        
        # 文本时长
        if slide.text:
            # 中文字符
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', slide.text))
            # 英文单词
            english_words = len(re.findall(r'[a-zA-Z]+', slide.text))
            duration += chinese_chars / 3.5 + english_words / 2.0
        
        # 代码/公式额外时间
        if slide.coq_code:
            # 代码行数
            lines = slide.coq_code.count('\n') + 1
            duration += lines * 0.5  # 每行0.5秒动画时间
        
        if slide.formula:
            # 公式复杂度（简单估算：字符数）
            duration += len(slide.formula) * 0.1
        
        # 最小5秒，最大30秒
        duration = max(5.0, min(30.0, duration))
        
        return round(duration, 1)


def build_slides(slides: List[SlideStructure]) -> List[SlideStructure]:
    """
    便捷函数：处理slides
    
    Args:
        slides: 原始slides列表
    
    Returns:
        处理后的slides列表
    """
    builder = SlideBuilder(slides)
    return builder.build()


