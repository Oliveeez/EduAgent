"""
LaTeX解析工具
从LaTeX文档中提取章节、公式、内容等
"""

import re
import logging
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class LaTeXParser:
    """LaTeX文档解析器"""
    
    def __init__(self):
        self.content = ""
        self.structure = {}
        
    def parse_file(self, latex_path: str) -> Dict:
        """
        解析LaTeX文件
        
        Args:
            latex_path: LaTeX文件路径
            
        Returns:
            解析后的结构化数据
        """
        try:
            with open(latex_path, 'r', encoding='utf-8') as f:
                self.content = f.read()
            
            logger.info(f"📖 开始解析LaTeX文件: {latex_path}")
            
            # 提取文档信息
            doc_info = self._extract_document_info()
            
            # 提取章节结构
            chapters = self._extract_chapters()
            
            # 提取数学公式
            equations = self._extract_equations()
            
            # 提取图表
            figures = self._extract_figures()
            
            result = {
                "document_info": doc_info,
                "chapters": chapters,
                "equations": equations,
                "figures": figures,
                "total_chapters": len(chapters),
                "total_equations": len(equations),
                "total_figures": len(figures)
            }
            
            logger.info(f"✅ 解析完成: {len(chapters)}个章节, {len(equations)}个公式, {len(figures)}个图表")
            return result
            
        except Exception as e:
            logger.error(f"❌ 解析失败: {e}")
            raise
    
    def _extract_document_info(self) -> Dict:
        """提取文档基本信息（标题、作者等）"""
        info = {}
        
        # 提取标题
        title_match = re.search(r'\\title\{([^}]+)\}', self.content)
        if title_match:
            info['title'] = title_match.group(1)
        
        # 提取作者
        author_match = re.search(r'\\author\{([^}]+)\}', self.content)
        if author_match:
            info['author'] = author_match.group(1)
        
        # 提取日期
        date_match = re.search(r'\\date\{([^}]+)\}', self.content)
        if date_match:
            info['date'] = date_match.group(1)
        
        return info
    
    def _extract_chapters(self) -> List[Dict]:
        """
        提取章节结构（支持chapter, section, subsection）
        
        Returns:
            章节列表，每个元素包含标题、层级、内容等
        """
        chapters = []
        
        # 匹配章节命令
        patterns = [
            (r'\\chapter\{([^}]+)\}', 'chapter', 1),
            (r'\\section\{([^}]+)\}', 'section', 2),
            (r'\\subsection\{([^}]+)\}', 'subsection', 3),
            (r'\\subsubsection\{([^}]+)\}', 'subsubsection', 4),
        ]
        
        for pattern, section_type, level in patterns:
            matches = re.finditer(pattern, self.content)
            for match in matches:
                title = match.group(1)
                start_pos = match.end()
                
                # 尝试提取该章节的内容（到下一个同级或更高级章节为止）
                content = self._extract_section_content(start_pos, level)
                
                chapters.append({
                    'title': title,
                    'type': section_type,
                    'level': level,
                    'content': content,
                    'position': match.start()
                })
        
        # 按位置排序
        chapters.sort(key=lambda x: x['position'])
        
        return chapters
    
    def _extract_section_content(self, start_pos: int, current_level: int) -> str:
        """提取章节内容（到下一个同级或更高级章节）"""
        # 查找下一个章节标记
        level_patterns = [
            r'\\chapter\{',
            r'\\section\{',
            r'\\subsection\{',
            r'\\subsubsection\{'
        ]
        
        # 只查找同级或更高级的章节
        relevant_patterns = level_patterns[:current_level]
        combined_pattern = '|'.join(relevant_patterns)
        
        next_section = re.search(combined_pattern, self.content[start_pos:])
        
        if next_section:
            end_pos = start_pos + next_section.start()
            content = self.content[start_pos:end_pos]
        else:
            content = self.content[start_pos:]
        
        # 清理内容（移除过多的空白）
        content = re.sub(r'\n\s*\n+', '\n\n', content)
        return content.strip()
    
    def _extract_equations(self) -> List[Dict]:
        """提取数学公式"""
        equations = []
        
        # 行内公式 $...$
        inline_matches = re.finditer(r'\$([^\$]+)\$', self.content)
        for match in inline_matches:
            equations.append({
                'type': 'inline',
                'latex': match.group(1),
                'position': match.start()
            })
        
        # 行间公式 \[...\] 或 $$...$$
        display_patterns = [
            (r'\\\[(.+?)\\\]', 'display'),
            (r'\$\$(.+?)\$\$', 'display'),
        ]
        
        for pattern, eq_type in display_patterns:
            matches = re.finditer(pattern, self.content, re.DOTALL)
            for match in matches:
                equations.append({
                    'type': eq_type,
                    'latex': match.group(1).strip(),
                    'position': match.start()
                })
        
        # equation环境
        equation_env = re.finditer(
            r'\\begin\{equation\}(.+?)\\end\{equation\}',
            self.content,
            re.DOTALL
        )
        for match in equation_env:
            equations.append({
                'type': 'equation',
                'latex': match.group(1).strip(),
                'position': match.start()
            })
        
        # align环境
        align_env = re.finditer(
            r'\\begin\{align\*?\}(.+?)\\end\{align\*?\}',
            self.content,
            re.DOTALL
        )
        for match in align_env:
            equations.append({
                'type': 'align',
                'latex': match.group(1).strip(),
                'position': match.start()
            })
        
        # 按位置排序
        equations.sort(key=lambda x: x['position'])
        
        return equations
    
    def _extract_figures(self) -> List[Dict]:
        """提取图表信息"""
        figures = []
        
        # figure环境
        figure_pattern = r'\\begin\{figure\}(.+?)\\end\{figure\}'
        matches = re.finditer(figure_pattern, self.content, re.DOTALL)
        
        for match in matches:
            figure_content = match.group(1)
            
            # 提取图片路径
            includegraphics = re.search(r'\\includegraphics(?:\[.*?\])?\{([^}]+)\}', figure_content)
            image_path = includegraphics.group(1) if includegraphics else None
            
            # 提取标题
            caption = re.search(r'\\caption\{([^}]+)\}', figure_content)
            caption_text = caption.group(1) if caption else None
            
            # 提取标签
            label = re.search(r'\\label\{([^}]+)\}', figure_content)
            label_text = label.group(1) if label else None
            
            figures.append({
                'type': 'figure',
                'image_path': image_path,
                'caption': caption_text,
                'label': label_text,
                'position': match.start()
            })
        
        # table环境
        table_pattern = r'\\begin\{table\}(.+?)\\end\{table\}'
        matches = re.finditer(table_pattern, self.content, re.DOTALL)
        
        for match in matches:
            table_content = match.group(1)
            
            # 提取标题
            caption = re.search(r'\\caption\{([^}]+)\}', table_content)
            caption_text = caption.group(1) if caption else None
            
            # 提取标签
            label = re.search(r'\\label\{([^}]+)\}', table_content)
            label_text = label.group(1) if label else None
            
            figures.append({
                'type': 'table',
                'caption': caption_text,
                'label': label_text,
                'position': match.start()
            })
        
        # 按位置排序
        figures.sort(key=lambda x: x['position'])
        
        return figures
    
    def clean_latex_text(self, text: str) -> str:
        """清理LaTeX文本，移除命令，保留纯文本"""
        # 移除注释
        text = re.sub(r'%.*$', '', text, flags=re.MULTILINE)
        
        # 移除常见命令
        text = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', text)
        text = re.sub(r'\\[a-zA-Z]+', '', text)
        
        # 移除特殊字符
        text = text.replace('~', ' ')
        text = text.replace('\\\\', '\n')
        
        # 清理多余空白
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text