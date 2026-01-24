# stage0_parser.py
# Stage 0: 演讲稿解析与分页决策

import json
import re
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass

from .models import SlideStructure, SlideType


@dataclass
class CodeBlock:
    """代码块提取结果"""
    content: str
    start_pos: int
    end_pos: int
    block_type: str  # "coq" or "formula"


class ScriptParser:
    """
    演讲稿解析器
    
    核心功能：
    1. 解析JSON演讲稿
    2. 提取<code_start>...<code_end>和<formula_start>...<formula_end>标记
    3. 为每个block创建独立slide，绑定上下文文本
    """
    
    # 正则模式 - 支持两种格式: <xxx_end> 和 </xxx_end>
    CODE_PATTERN = re.compile(r'<code_start>(.*?)(?:</code_end>|<code_end>)', re.DOTALL)
    FORMULA_PATTERN = re.compile(r'<formula_start>(.*?)(?:</formula_end>|<formula_end>)', re.DOTALL)
    
    def __init__(self, json_path: str):
        """
        初始化解析器
        
        Args:
            json_path: 演讲稿JSON文件路径
        """
        self.json_path = Path(json_path)
        self.raw_data: Dict[str, Any] = {}
        self.slides: List[SlideStructure] = []
        
    def load(self) -> Dict[str, Any]:
        """加载JSON文件"""
        with open(self.json_path, 'r', encoding='utf-8') as f:
            self.raw_data = json.load(f)
        return self.raw_data
    
    def parse(self) -> List[SlideStructure]:
        """
        解析演讲稿，返回Slide结构列表
        
        核心算法：
        1. 遍历每个section和point
        2. 在point.text中查找code/formula blocks
        3. 为每个block创建一个slide，绑定其上下文文本
        """
        if not self.raw_data:
            self.load()
        
        script = self.raw_data.get("script", {})
        sections = script.get("sections", [])
        
        slide_id = 1
        
        for section in sections:
            section_title = section.get("title", "")
            opening = section.get("opening", "")
            closing = section.get("closing", "")
            points = section.get("points", [])
            
            # 收集该section的所有文本和blocks
            section_slides = self._parse_section(
                section_title=section_title,
                opening=opening,
                points=points,
                closing=closing,
                start_slide_id=slide_id
            )
            
            slide_id += len(section_slides)
            self.slides.extend(section_slides)
        
        return self.slides
    
    def _parse_section(
        self,
        section_title: str,
        opening: str,
        points: List[Dict],
        closing: str,
        start_slide_id: int
    ) -> List[SlideStructure]:
        """
        解析单个section
        
        核心改进：
        1. 同一段落中连续的公式合并为一页（如方程组）
        2. 同一段落中连续的代码合并为一页
        
        Args:
            section_title: 章节标题
            opening: 开场白
            points: 要点列表
            closing: 结束语
            start_slide_id: 起始slide ID
        
        Returns:
            该section的所有slides
        """
        slides = []
        current_id = start_slide_id
        
        # 合并所有文本以便进行上下文绑定
        all_text_parts = []
        if opening:
            all_text_parts.append(("opening", opening, []))
        
        for i, point in enumerate(points):
            text = point.get("text", "")
            if text:
                # 提取该point中的所有blocks
                blocks = self._extract_blocks(text)
                all_text_parts.append((f"point_{i}", text, blocks))
        
        if closing:
            all_text_parts.append(("closing", closing, []))
        
        # 为每个part创建slide
        for part_name, text, blocks in all_text_parts:
            if not blocks:
                # 没有code/formula，如果有足够内容，创建intro slide
                clean_text = self._clean_text(text)
                if len(clean_text) > 50:  # 至少50字符才创建单独页
                    slide = SlideStructure(
                        slide_id=current_id,
                        slide_type=SlideType.INTRO,
                        title=self._generate_title(clean_text, section_title),
                        text=clean_text,
                        section_title=section_title,
                        estimated_duration=self._estimate_duration(clean_text)
                    )
                    slides.append(slide)
                    current_id += 1
            else:
                # 有blocks，合并同类型的连续blocks为一页
                merged_blocks = self._merge_consecutive_blocks(blocks)
                
                for merged in merged_blocks:
                    # 获取合并后的上下文文本（整个段落的文本）
                    clean_context = self._clean_text(text)
                    
                    if merged["type"] == "coq":
                        slide = SlideStructure(
                            slide_id=current_id,
                            slide_type=SlideType.COQ,
                            title=section_title,  # 使用section标题
                            text=clean_context,
                            coq_code=merged["content"],  # 可能是多段代码
                            section_title=section_title,
                            estimated_duration=self._estimate_duration(clean_context)
                        )
                    else:  # formula - 可能是多个公式（如方程组）
                        slide = SlideStructure(
                            slide_id=current_id,
                            slide_type=SlideType.FORMULA,
                            title=section_title,  # 使用section标题
                            text=clean_context,
                            formula=merged["content"],  # 多个公式用换行分隔
                            section_title=section_title,
                            estimated_duration=self._estimate_duration(clean_context)
                        )
                    
                    slides.append(slide)
                    current_id += 1
        
        return slides
    
    def _merge_consecutive_blocks(self, blocks: List[CodeBlock]) -> List[Dict]:
        """
        合并同一段落中连续的同类型blocks
        
        例如：方程组 x+y=35 和 2x+4y=94 应该合并为一页
        
        Args:
            blocks: 提取的blocks列表（已按位置排序）
        
        Returns:
            合并后的blocks列表
        """
        if not blocks:
            return []
        
        merged = []
        current_group = {
            "type": blocks[0].block_type,
            "contents": [blocks[0].content.strip()],
            "start_pos": blocks[0].start_pos,
            "end_pos": blocks[0].end_pos
        }
        
        for block in blocks[1:]:
            # 检查是否应该合并：
            # 1. 类型相同
            # 2. 位置相近（中间文本少于50字符，说明是连续的）
            gap = block.start_pos - current_group["end_pos"]
            
            if block.block_type == current_group["type"] and gap < 50:
                # 合并
                current_group["contents"].append(block.content.strip())
                current_group["end_pos"] = block.end_pos
            else:
                # 保存当前组，开始新组
                merged.append({
                    "type": current_group["type"],
                    "content": "\n".join(current_group["contents"])
                })
                current_group = {
                    "type": block.block_type,
                    "contents": [block.content.strip()],
                    "start_pos": block.start_pos,
                    "end_pos": block.end_pos
                }
        
        # 保存最后一组
        merged.append({
            "type": current_group["type"],
            "content": "\n".join(current_group["contents"])
        })
        
        return merged
    
    def _extract_blocks(self, text: str) -> List[CodeBlock]:
        """
        从文本中提取所有code和formula blocks
        
        Args:
            text: 原始文本
        
        Returns:
            按位置排序的blocks列表
        """
        blocks = []
        
        # 提取code blocks
        for match in self.CODE_PATTERN.finditer(text):
            blocks.append(CodeBlock(
                content=match.group(1),
                start_pos=match.start(),
                end_pos=match.end(),
                block_type="coq"
            ))
        
        # 提取formula blocks
        for match in self.FORMULA_PATTERN.finditer(text):
            blocks.append(CodeBlock(
                content=match.group(1),
                start_pos=match.start(),
                end_pos=match.end(),
                block_type="formula"
            ))
        
        # 按位置排序
        blocks.sort(key=lambda b: b.start_pos)
        
        return blocks
    
    def _bind_context(self, text: str, block: CodeBlock) -> str:
        """
        为block绑定上下文文本
        
        算法：
        1. 向上查找直到遇到上一个block或文本开头
        2. 向下查找直到遇到下一个block或文本结尾
        3. 将block内容保留，其他标记清除
        
        Args:
            text: 完整文本
            block: 当前block
        
        Returns:
            绑定了上下文的文本
        """
        all_blocks = self._extract_blocks(text)
        block_index = next(
            (i for i, b in enumerate(all_blocks) if b.start_pos == block.start_pos),
            0
        )
        
        # 确定上下文范围
        if block_index == 0:
            start = 0
        else:
            prev_block = all_blocks[block_index - 1]
            start = prev_block.end_pos
        
        if block_index == len(all_blocks) - 1:
            end = len(text)
        else:
            next_block = all_blocks[block_index + 1]
            end = next_block.start_pos
        
        # 提取上下文
        context = text[start:end]
        
        return context
    
    def _clean_text(self, text: str) -> str:
        """
        清理文本，移除标记但保留可读内容
        
        Args:
            text: 原始文本
        
        Returns:
            清理后的文本
        """
        # 移除code/formula标记，但保留内容（用于显示）
        cleaned = re.sub(r'<code_start>', '【代码】', text)
        cleaned = re.sub(r'(?:</code_end>|<code_end>)', '', cleaned)
        cleaned = re.sub(r'<formula_start>', '', cleaned)
        cleaned = re.sub(r'(?:</formula_end>|<formula_end>)', '', cleaned)
        
        # 清理多余空白
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip()
        
        return cleaned
    
    def _generate_title(self, text: str, section_title: str) -> str:
        """
        从文本生成标题
        
        Args:
            text: 上下文文本
            section_title: 章节标题
        
        Returns:
            生成的标题
        """
        # 简单策略：取前20个字符或使用section标题
        if len(text) > 20:
            # 尝试找到第一个句号或逗号
            for sep in ['。', '，', '：', ':', '、']:
                idx = text.find(sep)
                if 0 < idx <= 30:
                    return text[:idx]
            return text[:20] + "..."
        elif text:
            return text
        else:
            # 从section_title提取
            if '：' in section_title:
                return section_title.split('：')[1][:20]
            return section_title[:20] if section_title else "内容页"
    
    def _estimate_duration(self, text: str) -> float:
        """
        估算讲解时长
        
        基于中文语速：约3-4字/秒
        
        Args:
            text: 文本内容
        
        Returns:
            估算时长（秒）
        """
        # 中文字符数
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        # 英文单词数（粗略）
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        
        # 中文3字/秒，英文2词/秒
        duration = chinese_chars / 3.5 + english_words / 2.0
        
        # 最小5秒，最大30秒
        return max(5.0, min(30.0, duration))
    
    def save_slides(self, output_path: str) -> None:
        """
        保存解析结果到JSON
        
        Args:
            output_path: 输出文件路径
        """
        data = {
            "source_file": str(self.json_path),
            "slide_count": len(self.slides),
            "slides": [s.to_dict() for s in self.slides]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def parse_script(json_path: str) -> List[SlideStructure]:
    """
    便捷函数：解析演讲稿
    
    Args:
        json_path: JSON文件路径
    
    Returns:
        Slide结构列表
    """
    parser = ScriptParser(json_path)
    return parser.parse()

