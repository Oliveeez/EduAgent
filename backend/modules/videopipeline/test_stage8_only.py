#!/usr/bin/env python3
"""
只运行Stage 8的测试脚本 - 使用已有的test_run数据重新录制视频
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到路径
BACKEND_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from modules.videopipeline.models import SlideStructure, SlideType
from modules.videopipeline.stage8_video_composer import VideoComposer


def load_slides_from_json(json_path: Path) -> list:
    """从slides_data.json加载slide数据"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    slides = []
    for s in data['slides']:
        slide = SlideStructure(
            slide_id=s['slide_id'],
            slide_type=SlideType(s['slide_type']),
            title=s['title'],
            text=s['text'],
            original_text=s.get('original_text', ''),
            coq_code=s.get('coq_code'),
            formula=s.get('formula'),
            gif_path=Path(s['gif_path']) if s.get('gif_path') else None,
            audio_path=Path(s['audio_path']) if s.get('audio_path') else None,
            duration=s.get('duration'),
            section_title=s.get('section_title', ''),
            estimated_duration=s.get('estimated_duration', 0)
        )
        slides.append(slide)
    
    return slides


def main():
    output_dir = BACKEND_DIR / "data" / "pipeline_outputs" / "test_run"
    
    # 检查必要文件
    slides_json = output_dir / "slides_data.json"
    pptx_path = output_dir / "pptx" / "presentation_optimized.pptx"
    audio_path = output_dir / "audio" / "full_audio.mp3"
    subtitle_path = output_dir / "subtitles" / "subtitles.srt"
    
    if not slides_json.exists():
        print(f"❌ 找不到slides_data.json: {slides_json}")
        return
    
    if not pptx_path.exists():
        print(f"❌ 找不到PPTX: {pptx_path}")
        return
    
    print("=" * 60)
    print("🎬 Stage 8 Only: 重新录制视频")
    print(f"   输出目录: {output_dir}")
    print("=" * 60)
    
    # 加载slides数据
    print("\n📋 加载slides数据...")
    slides = load_slides_from_json(slides_json)
    print(f"   共 {len(slides)} 页")
    for s in slides:
        print(f"   Slide {s.slide_id}: {s.duration:.1f}秒")
    
    # 计算总时长
    total_duration = 3.0 + sum(s.duration or 5.0 for s in slides)
    print(f"\n   总时长: {total_duration:.1f}秒 (封面3秒 + 内容{total_duration-3:.1f}秒)")
    
    # 运行Stage 8
    print("\n🎬 开始视频合成...")
    composer = VideoComposer(str(output_dir))
    final_video = composer.compose(pptx_path, audio_path, subtitle_path, slides)
    
    if final_video and final_video.exists():
        print(f"\n✅ 视频生成成功: {final_video}")
        print(f"   文件大小: {final_video.stat().st_size / 1024 / 1024:.1f} MB")
    else:
        print("\n❌ 视频生成失败")


if __name__ == "__main__":
    main()

