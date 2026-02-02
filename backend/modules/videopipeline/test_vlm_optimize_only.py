#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：只运行VLM优化阶段（Stage 5）
基于现有的PPT和bboxes.json进行优化
"""

import sys
import os
import json
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from modules.videopipeline.stage5_vlm_optimizer import VLMLayoutOptimizer
from modules.videopipeline.stage4_bbox_extractor import BBoxExtractor
from modules.videopipeline.models import SlideStructure
from pptx import Presentation


def load_slides_data(json_path: str):
    """加载slides_data.json"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    slides = []
    for slide_dict in data.get('slides', []):
        slide = SlideStructure.from_dict(slide_dict)
        slides.append(slide)
    
    return slides


def test_vlm_optimization():
    """测试VLM优化流程"""
    print("=" * 80)
    print("🧪 测试VLM优化（仅Stage 5）")
    print("=" * 80)
    print()
    
    # 定义路径
    base_dir = Path(project_root) / "data" / "pipeline_outputs" / "test_ppt_only"
    slides_data_path = base_dir / "slides_data.json"
    bboxes_path = base_dir / "bboxes_fixed.json"
    pptx_input = base_dir / "pptx" / "presentation.pptx"
    pptx_output = base_dir / "pptx" / "presentation_optimized_new.pptx"
    adjustments_output = base_dir / "layout_adjustments_new.json"
    
    print(f"📄 输入文件:")
    print(f"  - slides_data: {slides_data_path}")
    print(f"  - bboxes: {bboxes_path}")
    print(f"  - pptx输入: {pptx_input}")
    print()
    print(f"📁 输出文件:")
    print(f"  - pptx输出: {pptx_output}")
    print(f"  - 调整记录: {adjustments_output}")
    print()
    
    # 验证输入文件存在
    if not slides_data_path.exists():
        print(f"❌ 错误: slides_data.json 不存在")
        return False
    
    if not bboxes_path.exists():
        print(f"❌ 错误: bboxes.json 不存在")
        return False
    
    if not pptx_input.exists():
        print(f"❌ 错误: presentation.pptx 不存在")
        return False
    
    try:
        # 1. 加载slides_data
        print("📋 加载slides_data...")
        slides = load_slides_data(str(slides_data_path))
        print(f"   ✅ 加载完成，共 {len(slides)} 页")
        print()
        
        # 2. 加载bboxes
        print("📦 加载bboxes...")
        with open(bboxes_path, 'r', encoding='utf-8') as f:
            bboxes_data = json.load(f)
        print(f"   ✅ 加载完成")
        
        # 分析问题
        analysis = bboxes_data.get('analysis', {})
        overlaps = analysis.get('overlaps', [])
        out_of_bounds = analysis.get('out_of_bounds', [])
        
        print(f"   📊 当前布局问题:")
        print(f"      - 重叠元素: {len(overlaps)} 个")
        print(f"      - 超出边界: {len(out_of_bounds)} 个")
        print()
        
        # 3. 运行VLM优化
        print("🎨 Stage 5: VLM布局优化...")
        optimizer = VLMLayoutOptimizer(
            pptx_path=str(pptx_input),
            output_dir=str(base_dir)
        )
        
        # 将bboxes_data转换为SlideBBoxes列表
        from modules.videopipeline.models import SlideBBoxes, BoundingBox
        
        bboxes_list = []
        for slide_bbox_dict in bboxes_data.get('slides', []):
            slide_id = slide_bbox_dict.get('slide_id')
            elements = []
            for elem in slide_bbox_dict.get('elements', []):
                bbox = BoundingBox(
                    element_type=elem.get('type'),  # 正确的字段名
                    left=elem.get('left'),
                    top=elem.get('top'),
                    width=elem.get('width'),
                    height=elem.get('height'),
                    content=elem.get('content', ''),
                    block_id=elem.get('block_id'),
                    block_type=elem.get('block_type'),
                    semantic_role=elem.get('semantic_role')
                )
                elements.append(bbox)
            
            slide_bboxes = SlideBBoxes(
                slide_id=slide_id,
                elements=elements
            )
            bboxes_list.append(slide_bboxes)
        
        optimized_pptx_path = optimizer.optimize(
            bboxes=bboxes_list,
            max_iterations=1,
            slides_data=slides
        )
        
        print(f"   ✅ 优化完成")
        print(f"   📂 优化后的PPT: {optimized_pptx_path}")
        print()
        
        # 4. 复制优化后的PPT到新位置
        import shutil
        if optimized_pptx_path != pptx_output:
            print("📋 复制优化后的PPT...")
            shutil.copy(str(optimized_pptx_path), str(pptx_output))
            print(f"   ✅ 已复制到: {pptx_output}")
            print()
        
        # 5. 保存调整日志
        print("💾 保存调整日志...")
        adjustment_summary = {
            "input_pptx": str(pptx_input),
            "output_pptx": str(optimized_pptx_path),
            "adjustments": optimizer.adjustment_log
        }
        with open(adjustments_output, 'w', encoding='utf-8') as f:
            json.dump(adjustment_summary, f, ensure_ascii=False, indent=2)
        print(f"   ✅ 已保存到: {adjustments_output}")
        print()
        
        # 6. 显示优化摘要
        print("=" * 80)
        print("✅ 测试成功！")
        print("=" * 80)
        print()
        print("📊 优化摘要:")
        print(f"  - 优化的slide数量: {len(optimizer.adjustment_log)}")
        print(f"  - 调整记录条目: {len(optimizer.adjustment_log)}")
        print()
        print(f"📂 输出文件位置:")
        print(f"  - {pptx_output}")
        print(f"  - {adjustments_output}")
        print()
        
        return True
        
    except Exception as e:
        print("=" * 80)
        print("❌ 测试失败！")
        print("=" * 80)
        print()
        print(f"错误: {e}")
        print()
        
        import traceback
        print("详细错误信息:")
        traceback.print_exc()
        print()
        
        return False


if __name__ == "__main__":
    success = test_vlm_optimization()
    sys.exit(0 if success else 1)

