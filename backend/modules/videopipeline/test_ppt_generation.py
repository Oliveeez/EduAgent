#!/usr/bin/env python3
# test_ppt_generation.py
# 测试PPT生成流程（Stage 0 → 1 → 1.5 → 2 → 3 → 4 → 5）

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.videopipeline.main_pipeline import VideoPipeline


def test_ppt_generation():
    """
    测试PPT生成流程
    
    测试范围：
    - Stage 0: 解析演讲稿
    - Stage 1: 构建Slide结构
    - Stage 1.5: PageDirector Agent决策
    - Stage 2: 渲染Manim动画
    - Stage 3: 生成PPTX
    - Stage 4: 提取BBox
    - Stage 5: VLM布局优化
    """
    
    print("=" * 80)
    print("🧪 测试PPT生成流程（Stage 0-5）")
    print("=" * 80)
    print()
    
    # 使用test.json
    json_path = Path(__file__).parent.parent.parent / "data" / "outlines" / "test.json"
    
    if not json_path.exists():
        print(f"❌ 测试文件不存在: {json_path}")
        return False
    
    print(f"📄 输入文件: {json_path}")
    print()
    
    # 创建输出目录
    output_dir = Path(__file__).parent.parent.parent / "data" / "pipeline_outputs" / "test_ppt_only"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 输出目录: {output_dir}")
    print()
    
    try:
        # 创建Pipeline
        pipeline = VideoPipeline(
            json_path=str(json_path),
            output_dir=str(output_dir)
        )
        
        # 只运行到Stage 5
        print("🚀 开始执行Pipeline...")
        print()
        
        # Stage 0: 解析
        print("📋 Stage 0: 解析演讲稿...")
        pipeline.slides = pipeline._run_stage0()
        print(f"   ✅ 解析完成，共 {len(pipeline.slides)} 页")
        print()
        
        # Stage 1: 构建
        print("🔧 Stage 1: 构建Slide结构...")
        pipeline.slides = pipeline._run_stage1()
        print(f"   ✅ 结构构建完成")
        print()
        
        # Stage 1.5: Agent决策
        print("🎯 Stage 1.5: PageDirector Agent决策...")
        pipeline.slides = pipeline._run_stage1_5()
        total_blocks = sum(len(s.blocks) for s in pipeline.slides)
        print(f"   ✅ 决策完成，共生成 {total_blocks} 个blocks")
        print()
        
        # 打印决策结果摘要
        print("📊 决策结果摘要:")
        for slide in pipeline.slides[:3]:  # 只显示前3页
            print(f"   Slide {slide.slide_id}: {slide.title}")
            print(f"     Intent: {slide.page_intent}")
            print(f"     Atoms: {', '.join(str(a) for a in slide.page_atoms)}")
            print(f"     Blocks: {len(slide.blocks)}个")
            for block in slide.blocks[:2]:  # 每页只显示前2个block
                # 安全处理content，可能是字符串或字典
                content_preview = str(block.content)[:50] if block.content else ""
                print(f"       - {block.block_type} ({block.semantic_role}): {content_preview}...")
        if len(pipeline.slides) > 3:
            print(f"   ... 还有 {len(pipeline.slides) - 3} 页")
        print()
        
        # Stage 2: 渲染Manim
        print("🎨 Stage 2: 渲染Manim动画...")
        pipeline.slides = pipeline._run_stage2()
        gif_count = sum(1 for s in pipeline.slides if s.gif_path)
        print(f"   ✅ 渲染完成，共 {gif_count} 个GIF")
        print()
        
        # Stage 3: 生成PPTX
        print("📊 Stage 3: 生成PPTX...")
        pptx_path = pipeline._run_stage3()
        print(f"   ✅ PPTX已生成: {pptx_path}")
        print()
        
        # Stage 4: 提取BBox
        print("📐 Stage 4: 提取Bounding Box...")
        bboxes = pipeline._run_stage4(pptx_path)
        print(f"   ✅ BBox提取完成")
        print()
        
        # Stage 5: VLM优化
        print("🔄 Stage 5: VLM布局优化...")
        optimized_pptx = pipeline._run_stage5(pptx_path, bboxes)
        print(f"   ✅ 布局优化完成: {optimized_pptx}")
        print()
        
        # 保存slides数据
        pipeline._save_slides_data()
        
        print("=" * 80)
        print("✅ PPT生成流程测试成功！")
        print("=" * 80)
        print()
        print(f"📄 最终PPT: {optimized_pptx}")
        print(f"📊 Slides数据: {output_dir / 'slides_data.json'}")
        print(f"📐 BBox数据: {output_dir / 'bboxes.json'}")
        print()
        
        return True
        
    except Exception as e:
        import traceback
        print()
        print("=" * 80)
        print("❌ 测试失败！")
        print("=" * 80)
        print()
        print(f"错误: {e}")
        print()
        print("详细错误信息:")
        print(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = test_ppt_generation()
    sys.exit(0 if success else 1)

