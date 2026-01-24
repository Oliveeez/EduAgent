# stage4_bbox_extractor.py
# Stage 4: Bounding Box提取

import json
from typing import List, Dict, Any
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches

from .models import BoundingBox, SlideBBoxes


class BBoxExtractor:
    """
    Bounding Box提取器
    
    功能：
    1. 从PPTX中提取所有元素的位置和大小
    2. 生成布局分析JSON
    3. 检测重叠问题
    """
    
    def __init__(self, pptx_path: str):
        """
        初始化提取器
        
        Args:
            pptx_path: PPTX文件路径
        """
        self.pptx_path = Path(pptx_path)
        self.prs = Presentation(str(self.pptx_path))
        self.all_bboxes: List[SlideBBoxes] = []
    
    def extract(self) -> List[SlideBBoxes]:
        """
        提取所有slides的bounding boxes
        
        Returns:
            每页的bounding boxes列表
        """
        self.all_bboxes = []
        
        for slide_idx, slide in enumerate(self.prs.slides):
            slide_bboxes = self._extract_slide_bboxes(slide, slide_idx)
            self.all_bboxes.append(slide_bboxes)
        
        return self.all_bboxes
    
    def _extract_slide_bboxes(self, slide, slide_idx: int) -> SlideBBoxes:
        """
        提取单页的bounding boxes（过滤空元素）
        
        Args:
            slide: pptx slide对象
            slide_idx: slide索引
        
        Returns:
            该页的SlideBBoxes（只包含有内容的元素）
        """
        slide_bboxes = SlideBBoxes(slide_id=slide_idx, elements=[])
        
        for shape in slide.shapes:
            bbox = self._extract_shape_bbox(shape)
            if bbox:  # 只添加非空元素
                slide_bboxes.elements.append(bbox)
        
        return slide_bboxes
    
    def _extract_shape_bbox(self, shape) -> BoundingBox:
        """
        提取单个形状的bounding box
        
        Args:
            shape: pptx shape对象
        
        Returns:
            BoundingBox对象，如果是空元素则返回None
        """
        # 确定元素类型和内容
        element_type = None
        content = ""
        
        if hasattr(shape, 'text_frame'):
            element_type = "text"
            content = shape.text_frame.text.strip() if shape.text_frame.text else ""
            # 过滤空文本框（无内容或只有空白）
            if not content:
                return None
        elif hasattr(shape, 'image'):
            element_type = "image"
            content = "GIF/图片"
        else:
            # 其他形状类型，如果没有内容则跳过
            return None
        
        # 提取位置和大小
        try:
            bbox = BoundingBox(
                element_type=element_type,
                left=shape.left.inches if hasattr(shape.left, 'inches') else shape.left / 914400,
                top=shape.top.inches if hasattr(shape.top, 'inches') else shape.top / 914400,
                width=shape.width.inches if hasattr(shape.width, 'inches') else shape.width / 914400,
                height=shape.height.inches if hasattr(shape.height, 'inches') else shape.height / 914400,
                content=content[:100]  # 限制长度
            )
            return bbox
        except Exception as e:
            print(f"  ⚠️ 提取bbox失败: {e}")
            return None
    
    def find_overlaps(self) -> List[Dict[str, Any]]:
        """
        查找所有重叠问题
        
        Returns:
            重叠问题列表
        """
        overlaps = []
        
        for slide_bboxes in self.all_bboxes:
            if slide_bboxes.has_overlaps():
                # 找出具体哪些元素重叠
                elements = slide_bboxes.elements
                for i, elem1 in enumerate(elements):
                    for j, elem2 in enumerate(elements[i+1:], i+1):
                        if elem1.overlaps_with(elem2):
                            overlaps.append({
                                "slide_id": slide_bboxes.slide_id,
                                "element1_index": i,
                                "element1_type": elem1.element_type,
                                "element2_index": j,
                                "element2_type": elem2.element_type
                            })
        
        return overlaps
    
    def check_boundaries(self, page_width: float = 13.33, page_height: float = 7.5) -> List[Dict[str, Any]]:
        """
        检查是否有元素超出页面边界
        
        Args:
            page_width: 页面宽度（英寸）
            page_height: 页面高度（英寸）
        
        Returns:
            超出边界的元素列表
        """
        out_of_bounds = []
        
        for slide_bboxes in self.all_bboxes:
            for i, elem in enumerate(slide_bboxes.elements):
                issues = []
                
                if elem.left < 0:
                    issues.append("left < 0")
                if elem.top < 0:
                    issues.append("top < 0")
                if elem.left + elem.width > page_width:
                    issues.append(f"right > {page_width}")
                if elem.top + elem.height > page_height:
                    issues.append(f"bottom > {page_height}")
                
                if issues:
                    out_of_bounds.append({
                        "slide_id": slide_bboxes.slide_id,
                        "element_index": i,
                        "element_type": elem.element_type,
                        "issues": issues,
                        "bbox": elem.to_dict()
                    })
        
        return out_of_bounds
    
    def save_to_json(self, output_path: str):
        """
        保存bounding boxes到JSON文件
        
        Args:
            output_path: 输出文件路径
        """
        data = {
            "pptx_file": str(self.pptx_path),
            "slide_count": len(self.all_bboxes),
            "slides": [s.to_dict() for s in self.all_bboxes],
            "analysis": {
                "overlaps": self.find_overlaps(),
                "out_of_bounds": self.check_boundaries()
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"  ✅ BBox JSON已保存: {output_path}")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            包含所有信息的字典
        """
        return {
            "slides": [s.to_dict() for s in self.all_bboxes],
            "overlaps": self.find_overlaps(),
            "out_of_bounds": self.check_boundaries()
        }


def extract_bboxes(pptx_path: str) -> List[SlideBBoxes]:
    """
    便捷函数：提取PPTX的bounding boxes
    
    Args:
        pptx_path: PPTX文件路径
    
    Returns:
        每页的bounding boxes列表
    """
    extractor = BBoxExtractor(pptx_path)
    return extractor.extract()


