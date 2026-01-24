# stage7_subtitle_generator.py
# Stage 7: SRT字幕生成

import re
from typing import List
from pathlib import Path

from .models import SlideStructure, SubtitleEntry


class SubtitleGenerator:
    """
    字幕生成器
    
    功能：
    1. 生成SRT格式字幕
    2. 与slide时间对齐
    3. 控制字幕长度和换行
    """
    
    # 字幕配置
    MAX_CHARS_PER_LINE = 40    # 单行最大字符数
    MAX_LINES = 2              # 最大行数
    
    def __init__(self, output_dir: str):
        """
        初始化字幕生成器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.subtitles_dir = self.output_dir / "subtitles"
        self.subtitles_dir.mkdir(parents=True, exist_ok=True)
        
        self.entries: List[SubtitleEntry] = []
    
    def generate(self, slides: List[SlideStructure], cover_duration: float = 0.0) -> Path:
        """
        生成字幕文件
        
        Args:
            slides: 包含text和duration的slides列表
            cover_duration: 封面页时长（秒），现在为0因为视频已截掉开头
        
        Returns:
            生成的SRT文件路径
        """
        self.entries = []
        
        # 字幕从0秒开始（视频开头已截掉启动画面）
        current_time = 0.0
        subtitle_index = 1
        
        for slide in slides:
            # 使用原始演讲稿文本作为字幕（不是PPT要点）
            raw_text = slide.original_text if slide.original_text else slide.text
            if not raw_text or not slide.duration:
                continue
            
            # 获取该slide的字幕文本
            subtitle_text = self._process_text(raw_text)
            
            # 分割成多个字幕条目（如果文本太长）
            segments = self._split_into_segments(subtitle_text, slide.duration)
            
            segment_duration = slide.duration / len(segments) if segments else slide.duration
            
            for seg_text in segments:
                entry = SubtitleEntry(
                    index=subtitle_index,
                    start_time=current_time,
                    end_time=current_time + segment_duration,
                    text=seg_text
                )
                self.entries.append(entry)
                
                current_time += segment_duration
                subtitle_index += 1
        
        # 写入SRT文件
        output_path = self.subtitles_dir / "subtitles.srt"
        self._write_srt(output_path)
        
        print(f"  📝 字幕已生成: {output_path}")
        print(f"     共 {len(self.entries)} 条字幕")
        
        return output_path
    
    def _process_text(self, text: str) -> str:
        """
        处理字幕文本
        
        Args:
            text: 原始文本
        
        Returns:
            处理后的文本
        """
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # 移除特殊标记
        text = re.sub(r'【[^】]*】', '', text)
        
        # 移除code/formula标记残留
        text = re.sub(r'<[^>]+>', '', text)
        
        # 清理孤立的标点符号
        text = re.sub(r'^[，。、；：！？,.\'"\'\"]+', '', text)
        text = re.sub(r'[，。、；：！？,.\'"\'\"]+$', '', text)
        
        return text.strip()
    
    def _split_into_segments(self, text: str, total_duration: float) -> List[str]:
        """
        将文本分割成适合字幕显示的段落
        
        Args:
            text: 完整文本
            total_duration: 总时长
        
        Returns:
            分割后的文本列表
        """
        # 每条字幕最多显示时间
        max_duration_per_segment = 5.0
        
        # 计算需要分成几段
        num_segments = max(1, int(total_duration / max_duration_per_segment))
        
        # 先清理掉孤立的引号（与标点组合的情况，如 '。 或 "，）
        text = re.sub(r"['\"""'']+([。？！；，,.!?;])", r'\1', text)
        text = re.sub(r"([。？！；，,.!?;])['\"""'']+", r'\1', text)
        
        # 按句子分割
        sentences = re.split(r'([。？！；，,.!?;])', text)
        
        # 重新组合（保留标点）
        combined_sentences = []
        current = ""
        for i, part in enumerate(sentences):
            current += part
            # 如果是标点符号后面，或者是最后一个
            if i % 2 == 1 or i == len(sentences) - 1:
                # 清理并检查内容
                cleaned = current.strip()
                # 跳过只有标点或引号的段落
                if cleaned and len(re.sub(r'[。？！；，,.!?;\s\'\"""'']+', '', cleaned)) > 0:
                    combined_sentences.append(cleaned)
                current = ""
        
        if not combined_sentences:
            combined_sentences = [text]
        
        # 按段数分配句子
        segments = []
        sentences_per_segment = max(1, len(combined_sentences) // num_segments)
        
        for i in range(0, len(combined_sentences), sentences_per_segment):
            segment_text = ''.join(combined_sentences[i:i + sentences_per_segment])
            
            # 清理并检查
            segment_text = segment_text.strip()
            
            # 跳过太短的段落（少于3个字符，可能只是标点）
            if len(segment_text) < 3:
                continue
            
            # 换行处理
            segment_text = self._wrap_text(segment_text)
            
            segments.append(segment_text)
        
        return segments if segments else [text]
    
    def _wrap_text(self, text: str) -> str:
        """
        对长文本进行换行
        
        Args:
            text: 原始文本
        
        Returns:
            换行后的文本
        """
        if len(text) <= self.MAX_CHARS_PER_LINE:
            return text
        
        # 简单的换行策略：在中间位置找标点或空格
        lines = []
        current_line = ""
        
        words = list(text)  # 中文按字符分
        
        for char in words:
            current_line += char
            
            if len(current_line) >= self.MAX_CHARS_PER_LINE:
                # 找合适的断点
                break_point = -1
                for sep in ['，', '。', '、', '；', ' ', ',', '.']:
                    idx = current_line.rfind(sep)
                    if idx > len(current_line) // 2:
                        break_point = idx + 1
                        break
                
                if break_point > 0:
                    lines.append(current_line[:break_point])
                    current_line = current_line[break_point:]
                else:
                    lines.append(current_line)
                    current_line = ""
                
                if len(lines) >= self.MAX_LINES:
                    # 截断，添加省略号
                    if current_line:
                        lines[-1] = lines[-1].rstrip() + "..."
                    break
        
        if current_line and len(lines) < self.MAX_LINES:
            lines.append(current_line)
        
        return '\n'.join(lines)
    
    def _write_srt(self, output_path: Path):
        """
        写入SRT文件
        
        Args:
            output_path: 输出文件路径
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            for entry in self.entries:
                f.write(entry.to_srt_format())
                f.write('\n')
    
    def get_subtitle_style(self) -> str:
        """
        获取FFmpeg字幕样式参数
        
        Returns:
            FFmpeg force_style参数
        """
        return (
            "Alignment=2,"          # 底部居中
            "MarginV=40,"           # 底部边距
            "FontName=Microsoft YaHei,"  # 微软雅黑
            "FontSize=24,"          # 字体大小
            "PrimaryColour=&HFFFFFF,"    # 白色文字
            "OutlineColour=&H000000,"    # 黑色描边
            "Outline=2,"            # 描边宽度
            "Shadow=1"              # 阴影
        )


def generate_subtitles(slides: List[SlideStructure], output_dir: str) -> Path:
    """
    便捷函数：生成字幕
    
    Args:
        slides: slide列表
        output_dir: 输出目录
    
    Returns:
        SRT文件路径
    """
    generator = SubtitleGenerator(output_dir)
    return generator.generate(slides)


