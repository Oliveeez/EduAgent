# stage5_vlm_optimizer.py
# Stage 5: VLM布局优化

import json
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from utils.llm import CustomLLM
from .models import SlideBBoxes, BoundingBox


class VLMLayoutOptimizer:
    """
    VLM布局优化器
    
    功能：
    1. 将bounding box信息发送给LLM
    2. 获取布局调整建议
    3. 自动应用调整
    
    使用CustomLLM进行布局分析
    """
    
    # 页面尺寸
    PAGE_WIDTH = 13.33
    PAGE_HEIGHT = 7.5
    
    def __init__(self, pptx_path: str, output_dir: str):
        """
        初始化优化器
        
        Args:
            pptx_path: PPTX文件路径
            output_dir: 输出目录
        """
        self.pptx_path = Path(pptx_path)
        self.output_dir = Path(output_dir)
        self.prs = Presentation(str(self.pptx_path))
        self.llm = CustomLLM()
        
        self.adjustment_log: List[Dict] = []
    
    def optimize(self, bboxes: List[SlideBBoxes], max_iterations: int = 2) -> Path:
        """
        优化PPTX布局（优化版）
        
        优化策略：
        1. 智能跳过：简单页面（只有标题+文本）跳过VLM
        2. 提前终止：第1次迭代无问题则跳过第2次
        3. 简化检测：只检测有内容的元素重叠
        4. 并行调用：多页同时调用LLM
        
        Args:
            bboxes: 每页的bounding boxes（已过滤空元素）
            max_iterations: 最大迭代次数（默认2）
        
        Returns:
            优化后的PPTX路径
        """
        print("  🔄 开始VLM布局优化...")
        
        # 筛选需要优化的页面（智能跳过）
        pages_to_optimize = []
        for slide_idx, slide_bboxes in enumerate(bboxes):
            if self._should_skip_page(slide_bboxes):
                print(f"    ⏭️ 跳过页面 {slide_idx+1}（简单布局，无需优化）")
                continue
            pages_to_optimize.append((slide_idx, slide_bboxes))
        
        if not pages_to_optimize:
            print("    ✅ 所有页面都是简单布局，无需优化")
            output_path = self.output_dir / "pptx" / "presentation_optimized.pptx"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            self.prs.save(str(output_path))
            return output_path
        
        print(f"    📊 需要优化 {len(pages_to_optimize)} 页")
        
        # 迭代优化
        for iteration in range(max_iterations):
            print(f"    迭代 {iteration + 1}/{max_iterations}")
            
            # 并行处理多页
            needs_adjustment = self._optimize_pages_parallel(pages_to_optimize)
            
            # 提前终止：如果第1次迭代没发现问题，不进行第2次
            if not needs_adjustment:
                print("    ✅ 布局检查通过，提前终止")
                break
        
        # 保存优化后的PPTX
        output_path = self.output_dir / "pptx" / "presentation_optimized.pptx"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.prs.save(str(output_path))
        
        # 保存调整日志
        self._save_adjustment_log()
        
        print(f"  ✅ 优化完成: {output_path}")
        return output_path
    
    def _should_skip_page(self, slide_bboxes: SlideBBoxes) -> bool:
        """
        判断页面是否应该跳过VLM优化
        
        简单页面（只有标题+文本，无GIF/公式）可以跳过
        
        Args:
            slide_bboxes: 单页的bounding boxes
        
        Returns:
            True表示应该跳过
        """
        has_image = False
        text_count = 0
        
        for elem in slide_bboxes.elements:
            if elem.element_type == "image":
                has_image = True
            elif elem.element_type == "text":
                text_count += 1
        
        # 如果有图片（GIF/公式），需要优化
        if has_image:
            return False
        
        # 如果只有1-2个文本框（标题+内容），可以跳过
        if text_count <= 2:
            return True
        
        # 如果有重叠，不能跳过
        if slide_bboxes.has_overlaps():
            return False
        
        return True
    
    def _optimize_pages_parallel(self, pages_to_optimize: List[tuple]) -> bool:
        """
        并行优化多页
        
        Args:
            pages_to_optimize: [(slide_idx, slide_bboxes), ...]
        
        Returns:
            是否有调整
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        needs_adjustment = False
        
        # 使用线程池并行处理（限制并发数避免API限流）
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self._optimize_single_page, slide_idx, slide_bboxes): slide_idx
                for slide_idx, slide_bboxes in pages_to_optimize
            }
            
            for future in as_completed(futures):
                slide_idx = futures[future]
                try:
                    had_adjustment = future.result()
                    if had_adjustment:
                        needs_adjustment = True
                except Exception as e:
                    print(f"      ⚠️ 页面 {slide_idx+1} 优化失败: {e}")
        
        return needs_adjustment
    
    def _optimize_single_page(self, slide_idx: int, slide_bboxes: SlideBBoxes) -> bool:
        """
        优化单页
        
        Args:
            slide_idx: 页面索引
            slide_bboxes: 该页的bounding boxes
        
        Returns:
            是否有调整
        """
        # 简化检测：只检查有内容的元素重叠
        if not slide_bboxes.has_overlaps() and not self._check_visual_issues(slide_bboxes):
            return False
        
        # 获取LLM建议
        adjustments = self._get_llm_suggestions(slide_bboxes)
        
        if adjustments:
            # 应用调整
            self._apply_adjustments(slide_idx, adjustments)
            return True
        
        return False
    
    def _check_visual_issues(self, slide_bboxes: SlideBBoxes) -> bool:
        """
        检查视觉问题
        
        Args:
            slide_bboxes: 单页的bounding boxes
        
        Returns:
            是否有问题
        """
        for elem in slide_bboxes.elements:
            # 检查是否超出边界
            if elem.left < 0 or elem.top < 0:
                return True
            if elem.left + elem.width > self.PAGE_WIDTH:
                return True
            if elem.top + elem.height > self.PAGE_HEIGHT:
                return True
        
        return False
    
    def _get_llm_suggestions(self, slide_bboxes: SlideBBoxes) -> List[Dict[str, Any]]:
        """
        获取LLM的布局调整建议
        
        Args:
            slide_bboxes: 单页的bounding boxes
        
        Returns:
            调整建议列表
        """
        # 构建prompt
        prompt = f"""你是一个PPT布局检查专家。请分析以下页面布局是否存在问题。

页面尺寸：{self.PAGE_WIDTH} x {self.PAGE_HEIGHT} 英寸

页面元素：
{json.dumps([e.to_dict() for e in slide_bboxes.elements], ensure_ascii=False, indent=2)}

检查项：
1. 元素是否重叠（文本框和图像不应该重叠）
2. 元素是否超出页面边界
3. 布局是否平衡（左右不应过于不均衡）
4. 文本框和图像之间是否有足够间距（至少0.2英寸）

⚠️ 重要限制：
- 只能调整元素的 left, top, width, height
- 不能修改任何文字内容
- 不能删除或添加元素
- 调整后所有元素必须在页面边界内

请以JSON格式返回分析结果：
{{
  "has_issues": true/false,
  "issues_description": ["问题1", "问题2"],
  "adjustments": [
    {{
      "element_index": 0,
      "action": "move",
      "new_left": 1.0,
      "new_top": 2.0
    }},
    {{
      "element_index": 1,
      "action": "resize",
      "new_width": 5.0,
      "new_height": 4.0
    }}
  ]
}}

如果没有问题，adjustments应为空数组。
只返回JSON，不要添加其他文字。"""

        try:
            response = self.llm(prompt)
            
            # 清理响应
            response = response.replace("<br>", "\n")
            
            # 移除markdown代码块标记
            response = re.sub(r'```json\s*', '', response, flags=re.IGNORECASE)
            response = re.sub(r'```\s*', '', response)
            response = response.strip()
            
            # 解析JSON
            result = json.loads(response)
            
            if result.get("has_issues", False):
                print(f"      发现问题: {result.get('issues_description', [])}")
                return result.get("adjustments", [])
            else:
                return []
                
        except json.JSONDecodeError as e:
            print(f"      ⚠️ LLM响应解析失败: {e}")
            return []
        except Exception as e:
            print(f"      ⚠️ LLM调用失败: {e}")
            return []
    
    def _apply_adjustments(self, slide_idx: int, adjustments: List[Dict[str, Any]]):
        """
        应用布局调整
        
        Args:
            slide_idx: slide索引
            adjustments: 调整列表
        """
        slide = self.prs.slides[slide_idx]
        shapes = list(slide.shapes)
        
        for adj in adjustments:
            try:
                elem_idx = adj.get("element_index")
                action = adj.get("action")
                
                if elem_idx is None or elem_idx >= len(shapes):
                    continue
                
                shape = shapes[elem_idx]
                
                if action == "move":
                    new_left = adj.get("new_left")
                    new_top = adj.get("new_top")
                    
                    if new_left is not None:
                        shape.left = Inches(new_left)
                    if new_top is not None:
                        shape.top = Inches(new_top)
                    
                    self.adjustment_log.append({
                        "slide_idx": slide_idx,
                        "element_idx": elem_idx,
                        "action": "move",
                        "new_left": new_left,
                        "new_top": new_top
                    })
                    
                elif action == "resize":
                    new_width = adj.get("new_width")
                    new_height = adj.get("new_height")
                    
                    if new_width is not None:
                        shape.width = Inches(new_width)
                    if new_height is not None:
                        shape.height = Inches(new_height)
                    
                    self.adjustment_log.append({
                        "slide_idx": slide_idx,
                        "element_idx": elem_idx,
                        "action": "resize",
                        "new_width": new_width,
                        "new_height": new_height
                    })
                
                print(f"      应用调整: slide {slide_idx}, element {elem_idx}, {action}")
                
            except Exception as e:
                print(f"      ⚠️ 应用调整失败: {e}")
    
    def _save_adjustment_log(self):
        """保存调整日志"""
        log_path = self.output_dir / "layout_adjustments.json"
        
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump({
                "pptx_file": str(self.pptx_path),
                "adjustments": self.adjustment_log
            }, f, ensure_ascii=False, indent=2)
        
        print(f"  📝 调整日志已保存: {log_path}")


def optimize_layout(pptx_path: str, bboxes: List[SlideBBoxes], output_dir: str) -> Path:
    """
    便捷函数：优化PPTX布局
    
    Args:
        pptx_path: PPTX文件路径
        bboxes: bounding boxes列表
        output_dir: 输出目录
    
    Returns:
        优化后的PPTX路径
    """
    optimizer = VLMLayoutOptimizer(pptx_path, output_dir)
    return optimizer.optimize(bboxes)


