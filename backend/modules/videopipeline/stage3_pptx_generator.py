# stage3_pptx_generator.py
# Stage 3: PPTX生成器

import os
import re
from typing import List, Optional
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
import copy

from .models import SlideStructure, SlideType


class PPTXGenerator:
    """
    PPTX生成器
    
    功能：
    1. 使用模板创建PPTX（不修改模板结构）
    2. 第一页是封面页（只修改标题，删除二级标题和日期）
    3. 后续内容页使用第二页（空白页）作为模板
    
    字体格式参考 lecture_generator.py
    """
    
    # PPT尺寸（16:9）
    SLIDE_WIDTH = 13.33  # 英寸
    SLIDE_HEIGHT = 7.5   # 英寸
    
    # 布局常量
    TITLE_TOP = 0.3
    TITLE_HEIGHT = 0.8
    CONTENT_TOP = 1.3
    CONTENT_LEFT = 0.5
    TEXT_WIDTH = 6.0
    TEXT_HEIGHT = 5.5
    GIF_LEFT = 7.0
    GIF_TOP = 1.5
    GIF_WIDTH = 5.5
    GIF_HEIGHT = 5.0
    
    def __init__(self, template_path: str, output_dir: str):
        """
        初始化生成器
        
        Args:
            template_path: PPTX模板路径
            output_dir: 输出目录
        """
        self.template_path = Path(template_path)
        self.output_dir = Path(output_dir)
        self.pptx_dir = self.output_dir / "pptx"
        self.pptx_dir.mkdir(parents=True, exist_ok=True)
        
        self.prs: Optional[Presentation] = None
        self.blank_layout = None  # 第二页的空白布局
    
    def generate(self, slides: List[SlideStructure], title: str = "教学课件") -> Path:
        """
        生成PPTX文件
        
        Args:
            slides: slide结构列表
            title: 课件标题（用于修改第一页）
        
        Returns:
            生成的PPTX文件路径
        """
        # 加载模板
        if not self.template_path.exists():
            raise FileNotFoundError(f"模板文件不存在: {self.template_path}")
        
        self.prs = Presentation(str(self.template_path))
        print(f"  📄 加载模板: {self.template_path}")
        print(f"     模板共 {len(self.prs.slides)} 页")
        
        # 修改第一页（封面页）：只改标题，删除二级标题和日期
        self._modify_cover_slide(title)
        
        # 删除第二页（模板空白页），保存其布局以供后续使用
        # 注意：第二页是索引1
        if len(self.prs.slides) >= 2:
            # 记录第二页的布局（用于添加新页）
            self.blank_layout = self.prs.slides[1].slide_layout
            # 删除第二页
            rId = self.prs.slides._sldIdLst[1].rId
            self.prs.part.drop_rel(rId)
            del self.prs.slides._sldIdLst[1]
        else:
            # 如果模板只有一页，使用空白布局
            self.blank_layout = self.prs.slide_layouts[6] if len(self.prs.slide_layouts) > 6 else self.prs.slide_layouts[0]
        
        # 添加内容页
        for slide in slides:
            self._add_content_slide(slide)
        
        # 保存文件
        output_path = self.pptx_dir / "presentation.pptx"
        self.prs.save(str(output_path))
        print(f"  ✅ PPTX已保存: {output_path}")
        
        return output_path
    
    def _modify_cover_slide(self, title: str):
        """
        修改封面页：只修改主标题，删除二级标题和日期
        
        Args:
            title: 新的主标题
        """
        if len(self.prs.slides) == 0:
            return
        
        cover_slide = self.prs.slides[0]
        shapes_to_delete = []
        title_shape = None
        
        # 找到所有文本框并按面积排序，最大的是主标题
        text_shapes = []
        for shape in cover_slide.shapes:
            if hasattr(shape, 'text_frame') and shape.text_frame.text.strip():
                area = shape.width * shape.height
                text_shapes.append((area, shape))
        
        # 按面积排序
        text_shapes.sort(key=lambda x: x[0], reverse=True)
        
        if text_shapes:
            # 最大的文本框是主标题
            title_shape = text_shapes[0][1]
            
            # 其他所有文本框都删除（二级标题、日期等）
            for _, shape in text_shapes[1:]:
                shapes_to_delete.append(shape)
        
        # 修改主标题
        if title_shape:
            # 清除所有段落文本
            for para in title_shape.text_frame.paragraphs:
                para.clear()
            # 设置新标题
            title_shape.text_frame.paragraphs[0].text = title
            for run in title_shape.text_frame.paragraphs[0].runs:
                run.font.name = '微软雅黑'
                run.font.bold = True
                run.font.size = Pt(44)
                run.font.color.rgb = RGBColor(192, 0, 0)
        
        # 删除二级标题和日期
        for shape in shapes_to_delete:
            try:
                sp = shape.element
                sp.getparent().remove(sp)
            except Exception as e:
                print(f"      ⚠️ 无法删除元素: {e}")
    
    def _add_content_slide(self, slide_data: SlideStructure):
        """
        添加内容页
        
        使用第二页（空白页）的布局，不修改模板结构
        标题使用section_title（从test.json的script.sections[].title获取）
        
        布局逻辑：
        - 代码类型（COQ）：如果有GIF，左文字右GIF；否则左文字右代码文本
        - 公式类型（FORMULA）：左文字右公式文本（不使用Manim GIF）
        - 介绍类型（INTRO）：全幅文字
        
        Args:
            slide_data: slide结构体
        """
        # 使用保存的空白布局（来自模板第二页）
        slide = self.prs.slides.add_slide(self.blank_layout)
        
        # 标题优先使用section_title（来自test.json）
        display_title = slide_data.section_title if slide_data.section_title else slide_data.title
        self._add_title(slide, display_title)
        
        # 根据类型决定布局
        if slide_data.slide_type == SlideType.FORMULA and slide_data.formula:
            # 公式类型：左文字右公式（不使用GIF，直接用文本公式）
            self._add_text_with_formula(slide, slide_data)
        elif slide_data.gif_path and slide_data.gif_path.exists():
            # 代码类型有GIF：左文字右图
            self._add_text_with_gif(slide, slide_data)
        elif slide_data.slide_type == SlideType.COQ and slide_data.coq_code:
            # 代码类型无GIF：左文字右代码文本
            self._add_text_with_code(slide, slide_data)
        else:
            # 介绍类型：全幅文字
            self._add_text_full_width(slide, slide_data)
    
    def _add_title(self, slide, title: str):
        """添加标题"""
        title_box = slide.shapes.add_textbox(
            Inches(self.CONTENT_LEFT),
            Inches(self.TITLE_TOP),
            Inches(self.SLIDE_WIDTH - 1),
            Inches(self.TITLE_HEIGHT)
        )
        title_frame = title_box.text_frame
        title_frame.text = title
        
        for para in title_frame.paragraphs:
            para.alignment = PP_ALIGN.LEFT
            for run in para.runs:
                run.font.name = '微软雅黑'
                run.font.size = Pt(28)
                run.font.bold = True
                run.font.color.rgb = RGBColor(192, 0, 0)  # 深红色
    
    def _add_text_with_gif(self, slide, slide_data: SlideStructure):
        """添加带GIF的布局：左文字右GIF"""
        # 左侧文本框
        text_box = slide.shapes.add_textbox(
            Inches(self.CONTENT_LEFT),
            Inches(self.CONTENT_TOP),
            Inches(self.TEXT_WIDTH),
            Inches(self.TEXT_HEIGHT)
        )
        self._format_text_box(text_box, slide_data.text)
        
        # 右侧GIF
        slide.shapes.add_picture(
            str(slide_data.gif_path),
            Inches(self.GIF_LEFT),
            Inches(self.GIF_TOP),
            Inches(self.GIF_WIDTH),
            Inches(self.GIF_HEIGHT)
        )
    
    def _add_text_with_formula(self, slide, slide_data: SlideStructure):
        """添加带公式的布局：左文字右公式文本"""
        # 左侧文本框
        text_box = slide.shapes.add_textbox(
            Inches(self.CONTENT_LEFT),
            Inches(self.CONTENT_TOP),
            Inches(self.TEXT_WIDTH),
            Inches(self.TEXT_HEIGHT)
        )
        self._format_text_box(text_box, slide_data.text)
        
        # 右侧公式文本框（使用Cambria Math字体）
        self._add_formula_text_box(slide, slide_data.formula)
    
    def _add_text_with_code(self, slide, slide_data: SlideStructure):
        """添加带代码的布局：左文字右代码文本"""
        # 左侧文本框
        text_box = slide.shapes.add_textbox(
            Inches(self.CONTENT_LEFT),
            Inches(self.CONTENT_TOP),
            Inches(self.TEXT_WIDTH),
            Inches(self.TEXT_HEIGHT)
        )
        self._format_text_box(text_box, slide_data.text)
        
        # 右侧代码文本框
        self._add_code_text_box(slide, slide_data.coq_code)
    
    def _add_text_full_width(self, slide, slide_data: SlideStructure):
        """添加全幅文字布局"""
        text_box = slide.shapes.add_textbox(
            Inches(self.CONTENT_LEFT),
            Inches(self.CONTENT_TOP),
            Inches(self.SLIDE_WIDTH - 1),
            Inches(self.TEXT_HEIGHT)
        )
        self._format_text_box(text_box, slide_data.text)
        
        # 如果有代码但没有GIF，显示代码文本
        if slide_data.coq_code:
            self._add_code_text_box(slide, slide_data.coq_code)
        
        # 如果有公式但没有GIF，显示公式文本
        if slide_data.formula:
            self._add_formula_text_box(slide, slide_data.formula)
    
    def _format_text_box(self, text_box, text: str):
        """
        格式化文本框，使用普通bullet point格式
        
        不使用模板的logo，使用简单的文字要点格式
        """
        text_frame = text_box.text_frame
        text_frame.word_wrap = True
        
        # 分段处理 - 每行作为一个要点
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        
        for i, para_text in enumerate(paragraphs):
            if i == 0:
                para = text_frame.paragraphs[0]
            else:
                para = text_frame.add_paragraph()
            
            # 去除可能的bullet符号
            para_text = re.sub(r'^[•\-\*\d\.]+\s*', '', para_text)
            
            # 如果有多个要点，添加简单的bullet符号
            if len(paragraphs) > 1:
                para.text = "• " + para_text
            else:
                para.text = para_text
            
            para.alignment = PP_ALIGN.LEFT
            para.space_after = Pt(12)
            para.level = 0  # 不使用缩进级别（避免触发模板的bullet样式）
            
            for run in para.runs:
                run.font.name = '微软雅黑'
                run.font.size = Pt(18)
                run.font.color.rgb = RGBColor(0, 0, 0)
    
    def _add_code_text_box(self, slide, code: str):
        """添加代码文本框（当没有GIF时使用）"""
        code_box = slide.shapes.add_textbox(
            Inches(self.GIF_LEFT),
            Inches(self.GIF_TOP),
            Inches(self.GIF_WIDTH),
            Inches(self.GIF_HEIGHT)
        )
        
        text_frame = code_box.text_frame
        text_frame.word_wrap = True
        text_frame.text = code
        
        # 设置代码字体
        for para in text_frame.paragraphs:
            for run in para.runs:
                run.font.name = 'Consolas'
                run.font.size = Pt(14)
                run.font.color.rgb = RGBColor(0, 100, 0)  # 深绿色
        
        # 添加背景色（通过形状）
        # 注意：python-pptx不直接支持文本框背景色
        # 可以在文本框下方添加一个填充矩形作为背景
    
    def _add_formula_text_box(self, slide, formula: str):
        """添加公式文本框（当没有GIF时使用）"""
        formula_box = slide.shapes.add_textbox(
            Inches(self.GIF_LEFT),
            Inches(self.GIF_TOP),
            Inches(self.GIF_WIDTH),
            Inches(2.0)
        )
        
        text_frame = formula_box.text_frame
        text_frame.text = formula
        
        for para in text_frame.paragraphs:
            para.alignment = PP_ALIGN.CENTER
            for run in para.runs:
                run.font.name = 'Cambria Math'
                run.font.size = Pt(24)
                run.font.color.rgb = RGBColor(0, 0, 128)  # 深蓝色


def generate_pptx(
    slides: List[SlideStructure],
    template_path: str,
    output_dir: str,
    title: str = "教学课件"
) -> Path:
    """
    便捷函数：生成PPTX
    
    Args:
        slides: slide列表
        template_path: 模板路径
        output_dir: 输出目录
        title: 课件标题
    
    Returns:
        生成的PPTX文件路径
    """
    generator = PPTXGenerator(template_path, output_dir)
    return generator.generate(slides, title)


