#!/usr/bin/env python3
"""
完整视频生成Pipeline测试脚本

使用方法:
    cd /wuhu_uni_ai/edu/shenao/EduAgent/backend
    python modules/videopipeline/test_pipeline.py

可选参数:
    --input   : 输入JSON文件路径 (默认: data/outlines/test.json)
    --output  : 输出目录 (默认: data/pipeline_outputs/test_run)
    --no-llm  : 不使用LLM优化内容
    --stage   : 只运行指定阶段 (0-8, 或 all)
    --fast    : 快速模式（跳过VLM优化，减少迭代）
"""

import sys
import os
import argparse
import asyncio
import shutil
import json
import time
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

# 添加项目根目录到路径
BACKEND_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from modules.videopipeline.models import SlideStructure, PipelineResult
from modules.videopipeline.stage0_parser import ScriptParser
from modules.videopipeline.stage1_slide_builder import SlideBuilder
from modules.videopipeline.stage2_manim_renderer import ManimRenderer
from modules.videopipeline.stage3_pptx_generator import PPTXGenerator
from modules.videopipeline.stage4_bbox_extractor import BBoxExtractor
from modules.videopipeline.stage5_vlm_optimizer import VLMLayoutOptimizer
from modules.videopipeline.stage6_tts_generator import TTSGenerator
from modules.videopipeline.stage7_subtitle_generator import SubtitleGenerator
from modules.videopipeline.stage8_video_composer import VideoComposer


def run_full_pipeline(
    input_json: str,
    output_dir: str,
    template_path: str,
    use_llm: bool = True
) -> PipelineResult:
    """
    运行完整的视频生成Pipeline
    
    Args:
        input_json: 输入JSON文件路径
        output_dir: 输出目录
        template_path: PPTX模板路径
        use_llm: 是否使用LLM优化内容
    
    Returns:
        PipelineResult: 执行结果
    """
    output_path = Path(output_dir)
    
    # 清理输出目录
    if output_path.exists():
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True)
    
    print("=" * 70)
    print("🎬 完整视频生成Pipeline")
    print(f"   输入: {input_json}")
    print(f"   输出: {output_dir}")
    print(f"   LLM: {'启用' if use_llm else '禁用'}")
    print("=" * 70)
    
    slides = []
    stage_times = {}  # 记录每个阶段的耗时
    
    try:
        # ========== Stage 0: 解析演讲稿 ==========
        print("\n📋 Stage 0: 解析演讲稿...")
        t0 = time.time()
        parser = ScriptParser(input_json)
        slides = parser.parse()
        stage_times['Stage 0 (解析)'] = time.time() - t0
        print(f"   ✅ 解析完成，共 {len(slides)} 页 ({stage_times['Stage 0 (解析)']:.1f}秒)")
        for s in slides:
            print(f"      Slide {s.slide_id}: [{s.slide_type.value}] {s.section_title[:30] if s.section_title else ''}")
        
        # ========== Stage 1: 构建Slide结构 ==========
        print("\n🔧 Stage 1: 构建Slide结构...")
        t0 = time.time()
        builder = SlideBuilder(slides, use_llm=use_llm)
        slides = builder.build()
        stage_times['Stage 1 (结构)'] = time.time() - t0
        print(f"   ✅ 结构构建完成 ({stage_times['Stage 1 (结构)']:.1f}秒)")
        
        # ========== Stage 2: Manim动画渲染 ==========
        print("\n🎨 Stage 2: Manim动画渲染...")
        t0 = time.time()
        renderer = ManimRenderer(output_dir, quality='medium')
        slides = renderer.render_all(slides, parallel=True)  # 启用并行
        stage_times['Stage 2 (Manim)'] = time.time() - t0
        gif_count = sum(1 for s in slides if s.gif_path and s.gif_path.exists())
        print(f"   ✅ 渲染完成，共 {gif_count} 个GIF ({stage_times['Stage 2 (Manim)']:.1f}秒)")
        
        # ========== Stage 3: 生成PPTX ==========
        print("\n📊 Stage 3: 生成PPTX...")
        t0 = time.time()
        # 从JSON获取标题
        with open(input_json, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        title = json_data.get("outline", {}).get("title", "教学课件")
        
        pptx_gen = PPTXGenerator(template_path, output_dir)
        pptx_path = pptx_gen.generate(slides, title)
        stage_times['Stage 3 (PPTX)'] = time.time() - t0
        print(f"   ✅ PPTX生成: {pptx_path} ({stage_times['Stage 3 (PPTX)']:.1f}秒)")
        
        # ========== Stage 4: Bounding Box提取 ==========
        print("\n📐 Stage 4: 提取Bounding Box...")
        t0 = time.time()
        bbox_extractor = BBoxExtractor(str(pptx_path))
        bboxes = bbox_extractor.extract()
        bbox_extractor.save_to_json(str(output_path / 'bboxes.json'))
        stage_times['Stage 4 (BBox)'] = time.time() - t0
        print(f"   ✅ 提取完成，共 {len(bboxes)} 页 ({stage_times['Stage 4 (BBox)']:.1f}秒)")
        
        # ========== Stage 5: VLM布局优化 ==========
        print("\n🔄 Stage 5: VLM布局优化...")
        t0 = time.time()
        try:
            vlm_optimizer = VLMLayoutOptimizer(str(pptx_path), output_dir)
            pptx_path = vlm_optimizer.optimize(bboxes, max_iterations=2)  # 减少迭代
            stage_times['Stage 5 (VLM)'] = time.time() - t0
            print(f"   ✅ 布局优化完成 ({stage_times['Stage 5 (VLM)']:.1f}秒)")
        except Exception as e:
            stage_times['Stage 5 (VLM)'] = time.time() - t0
            print(f"   ⚠️ VLM优化跳过: {e} ({stage_times['Stage 5 (VLM)']:.1f}秒)")
        
        # ========== Stage 6: TTS语音生成 ==========
        print("\n🎤 Stage 6: TTS语音生成...")
        t0 = time.time()
        tts_gen = TTSGenerator(output_dir)
        
        # 使用异步并行生成
        async def gen_tts():
            return await tts_gen.generate_all_async(slides, parallel=True)
        
        slides = asyncio.run(gen_tts())
        audio_count = sum(1 for s in slides if s.audio_path and s.audio_path.exists())
        stage_times['Stage 6 (TTS)'] = time.time() - t0
        print(f"   ✅ 语音生成完成，共 {audio_count} 个音频 ({stage_times['Stage 6 (TTS)']:.1f}秒)")
        
        # 合并音频（不添加静音，视频开头已截掉）
        full_audio = tts_gen.merge_audio(slides, cover_duration=0.0)
        if full_audio:
            print(f"   ✅ 音频合并: {full_audio}")
        
        # ========== Stage 7: 字幕生成 ==========
        print("\n📝 Stage 7: 字幕生成...")
        t0 = time.time()
        subtitle_gen = SubtitleGenerator(output_dir)
        # 字幕从0秒开始（视频开头已截掉）
        srt_path = subtitle_gen.generate(slides, cover_duration=0.0)
        stage_times['Stage 7 (字幕)'] = time.time() - t0
        print(f"   ✅ 字幕生成: {srt_path} ({stage_times['Stage 7 (字幕)']:.1f}秒)")
        
        # ========== Stage 8: 视频合成 ==========
        print("\n🎬 Stage 8: 视频合成...")
        t0 = time.time()
        composer = VideoComposer(output_dir)
        final_video = composer.compose(pptx_path, full_audio, srt_path, slides)
        stage_times['Stage 8 (视频)'] = time.time() - t0
        print(f"   ✅ 视频合成完成 ({stage_times['Stage 8 (视频)']:.1f}秒)")
        
        # ========== 保存结果 ==========
        # 保存slides数据
        slides_data = {
            'generated_at': datetime.now().isoformat(),
            'source_file': input_json,
            'slide_count': len(slides),
            'slides': [s.to_dict() for s in slides]
        }
        with open(output_path / 'slides_data.json', 'w', encoding='utf-8') as f:
            json.dump(slides_data, f, ensure_ascii=False, indent=2)
        
        # 计算总时长
        total_duration = sum(s.duration or 0 for s in slides)
        
        # 构建结果
        result = PipelineResult(
            success=True,
            video_path=final_video,
            pptx_path=pptx_path,
            audio_path=full_audio,
            subtitle_path=srt_path,
            total_duration=total_duration,
            slides=slides
        )
        
        # 计算总耗时
        total_time = sum(stage_times.values())
        
        print("\n" + "=" * 70)
        print("🎉 Pipeline执行成功！")
        print("=" * 70)
        print(f"\n📁 输出目录: {output_dir}")
        print(f"\n📄 生成文件:")
        print(f"   • PPTX:   {pptx_path}")
        print(f"   • 视频:   {final_video}")
        print(f"   • 音频:   {full_audio}")
        print(f"   • 字幕:   {srt_path}")
        print(f"   • 数据:   {output_path / 'slides_data.json'}")
        print(f"\n⏱️ 音频总时长: {total_duration:.1f} 秒 ({total_duration/60:.1f} 分钟)")
        print(f"📊 共 {len(slides)} 页")
        
        # 输出各阶段耗时统计
        print(f"\n⏱️ 各阶段耗时统计:")
        print("-" * 50)
        for stage, t in stage_times.items():
            bar_len = int(t / total_time * 30) if total_time > 0 else 0
            bar = "█" * bar_len + "░" * (30 - bar_len)
            pct = t / total_time * 100 if total_time > 0 else 0
            print(f"   {stage:20s} {bar} {t:6.1f}s ({pct:4.1f}%)")
        print("-" * 50)
        print(f"   {'总耗时':20s} {'':30s} {total_time:6.1f}s")
        
        return result
        
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"\n❌ Pipeline执行失败: {e}")
        traceback.print_exc()
        
        return PipelineResult(
            success=False,
            error_message=error_msg,
            slides=slides
        )


def main():
    """主入口"""
    parser = argparse.ArgumentParser(description="视频生成Pipeline测试")
    parser.add_argument(
        "--input", "-i",
        default=str(BACKEND_DIR / "data" / "outlines" / "test.json"),
        help="输入JSON文件路径"
    )
    parser.add_argument(
        "--output", "-o",
        default=str(BACKEND_DIR / "data" / "pipeline_outputs" / "test_run"),
        help="输出目录"
    )
    parser.add_argument(
        "--template", "-t",
        default=str(BACKEND_DIR / "modules" / "videopipeline" / "template" / "template.pptx"),
        help="PPTX模板路径"
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="不使用LLM优化内容"
    )
    
    args = parser.parse_args()
    
    # 检查输入文件
    if not Path(args.input).exists():
        print(f"❌ 输入文件不存在: {args.input}")
        sys.exit(1)
    
    # 检查模板文件
    if not Path(args.template).exists():
        print(f"⚠️ 模板文件不存在: {args.template}")
    
    # 运行Pipeline
    result = run_full_pipeline(
        input_json=args.input,
        output_dir=args.output,
        template_path=args.template,
        use_llm=not args.no_llm
    )
    
    # 保存报告
    report = {
        "status": "success" if result.success else "failed",
        "generated_at": datetime.now().isoformat(),
        "input_file": args.input,
        "output_dir": args.output,
        "result": result.to_dict()
    }
    
    report_path = Path(args.output) / "pipeline_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
