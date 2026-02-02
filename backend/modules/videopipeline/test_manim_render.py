#!/usr/bin/env python3
# test_manim_render.py
# 单元测试：Manim动画渲染

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.videopipeline.stage2_manim_renderer import ManimRenderer
from modules.videopipeline.models import SlideStructure, SlideType


def test_function_plot():
    """测试函数图渲染"""
    print("=" * 80)
    print("🧪 测试1：函数图（双曲线对比）")
    print("=" * 80)
    
    # 创建测试slide
    slide = SlideStructure(
        slide_id=1,
        slide_type=SlideType.INTRO,
        title="测试函数图",
        text="测试文本"
    )
    
    # 设置manim配置
    slide.manim_relation_config = {
        'type': 'function_plot',
        'description': """双曲线对比图：X轴标记为'System Complexity'（系统复杂度），Y轴标记为'Verification Reliability'（验证可靠性）。
        曲线A（Human）在低复杂度时极高，随X轴延伸急剧跌落（指数级下降）；
        曲线B（Machine）在全区间保持稳定的高水平直线。"""
    }
    
    # 创建渲染器
    output_dir = Path(__file__).parent.parent.parent / "data" / "test_manim_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    renderer = ManimRenderer(str(output_dir))
    
    # 渲染
    print("\n🎨 开始渲染...")
    gif_path = renderer._render_relation(slide)
    
    if gif_path and gif_path.exists():
        print(f"\n✅ 渲染成功！")
        print(f"📄 GIF路径: {gif_path}")
        print(f"📏 文件大小: {gif_path.stat().st_size / 1024:.2f} KB")
    else:
        print(f"\n❌ 渲染失败！")
    
    return gif_path


def test_directed_graph():
    """测试有向图渲染"""
    print("\n" + "=" * 80)
    print("🧪 测试2：有向图（Parsing/Printing关系）")
    print("=" * 80)
    
    slide = SlideStructure(
        slide_id=2,
        slide_type=SlideType.INTRO,
        title="测试有向图",
        text="测试文本"
    )
    
    slide.manim_relation_config = {
        'type': 'directed_graph',
        'description': """左侧节点'Input: 35'，右侧节点'Internal: S (S ... O)'。
        中间有两个箭头：上方箭头从左向右标记为'Parse'，下方箭头从右向左标记为'Print'。"""
    }
    
    output_dir = Path(__file__).parent.parent.parent / "data" / "test_manim_output"
    renderer = ManimRenderer(str(output_dir))
    
    print("\n🎨 开始渲染...")
    gif_path = renderer._render_relation(slide)
    
    if gif_path and gif_path.exists():
        print(f"\n✅ 渲染成功！")
        print(f"📄 GIF路径: {gif_path}")
        print(f"📏 文件大小: {gif_path.stat().st_size / 1024:.2f} KB")
    else:
        print(f"\n❌ 渲染失败！")
    
    return gif_path


def test_flowchart():
    """测试流程图渲染"""
    print("\n" + "=" * 80)
    print("🧪 测试3：流程图（三层抽象阶梯）")
    print("=" * 80)
    
    slide = SlideStructure(
        slide_id=3,
        slide_type=SlideType.INTRO,
        title="测试流程图",
        text="测试文本"
    )
    
    slide.manim_relation_config = {
        'type': 'flowchart',
        'description': """三个节点的横向演化图：
        1. [现实世界/鸡兔] --(数学建模)--> 2. [数学符号/方程] --(形式化)--> 3. [机器语言/Coq代码]。
        重点强调第三步的转化。"""
    }
    
    output_dir = Path(__file__).parent.parent.parent / "data" / "test_manim_output"
    renderer = ManimRenderer(str(output_dir))
    
    print("\n🎨 开始渲染...")
    gif_path = renderer._render_relation(slide)
    
    if gif_path and gif_path.exists():
        print(f"\n✅ 渲染成功！")
        print(f"📄 GIF路径: {gif_path}")
        print(f"📏 文件大小: {gif_path.stat().st_size / 1024:.2f} KB")
    else:
        print(f"\n❌ 渲染失败！")
    
    return gif_path


def test_coq_code():
    """测试Coq代码动画（使用模板）"""
    print("\n" + "=" * 80)
    print("🧪 测试4：Coq代码动画（使用coq_scene.py模板）")
    print("=" * 80)
    
    slide = SlideStructure(
        slide_id=4,
        slide_type=SlideType.COQ,
        title="测试Coq代码",
        text="测试文本",
        coq_code="""Inductive nat : Type :=
  | O : nat
  | S : nat -> nat.

Check (S (S (S O))).
(* 输出: nat *)"""
    )
    
    output_dir = Path(__file__).parent.parent.parent / "data" / "test_manim_output"
    renderer = ManimRenderer(str(output_dir))
    
    print("\n🎨 开始渲染...")
    gif_path = renderer._render_coq(slide)
    
    if gif_path and gif_path.exists():
        print(f"\n✅ 渲染成功！")
        print(f"📄 GIF路径: {gif_path}")
        print(f"📏 文件大小: {gif_path.stat().st_size / 1024:.2f} KB")
    else:
        print(f"\n❌ 渲染失败！")
    
    return gif_path


if __name__ == "__main__":
    print("🎬 Manim渲染单元测试")
    print()
    
    results = []
    
    try:
        # 测试1: 函数图
        gif1 = test_function_plot()
        results.append(("函数图（双曲线对比）", gif1))
        
        # 测试2: 有向图
        gif2 = test_directed_graph()
        results.append(("有向图（Parse/Print）", gif2))
        
        # 测试3: 流程图
        gif3 = test_flowchart()
        results.append(("流程图（三层阶梯）", gif3))
        
        # 测试4: Coq代码
        gif4 = test_coq_code()
        results.append(("Coq代码动画", gif4))
        
    except Exception as e:
        print(f"\n❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
    
    # 打印总结
    print("\n" + "=" * 80)
    print("📊 测试总结")
    print("=" * 80)
    
    success_count = sum(1 for _, gif in results if gif and gif.exists())
    total_count = len(results)
    
    for name, gif in results:
        status = "✅" if gif and gif.exists() else "❌"
        print(f"{status} {name}")
        if gif and gif.exists():
            print(f"   路径: {gif}")
    
    print()
    print(f"成功: {success_count}/{total_count}")
    print()
    
    if success_count == total_count:
        print("🎉 所有测试通过！请手动查看生成的GIF文件。")
    else:
        print("⚠️ 部分测试失败，请查看详细日志。")



