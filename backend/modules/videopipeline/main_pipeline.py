# main_pipeline.py
# 主Pipeline编排器

import json
import os
from datetime import datetime
from typing import Optional
from pathlib import Path

from .models import SlideStructure, PipelineResult
from .stage0_parser import ScriptParser
from .stage1_slide_builder import SlideBuilder
from .stage1_5_page_director import PageDirectorAgent  # 新增
from .stage2_manim_renderer import ManimRenderer
from .stage3_pptx_generator import PPTXGenerator
from .stage4_bbox_extractor import BBoxExtractor
from .stage5_vlm_optimizer import VLMLayoutOptimizer
from .stage6_tts_generator import TTSGenerator
from .stage7_subtitle_generator import SubtitleGenerator
from .stage8_video_composer import VideoComposer


class VideoPipeline:
    """
    视频生成Pipeline主编排器
    
    协调所有Stage的执行，管理数据流
    """
    
    def __init__(
        self,
        json_path: str,
        template_path: Optional[str] = None,
        output_dir: Optional[str] = None
    ):
        """
        初始化Pipeline
        
        Args:
            json_path: 演讲稿JSON文件路径
            template_path: PPTX模板路径（可选）
            output_dir: 输出目录（可选）
        """
        self.json_path = Path(json_path)
        
        # 设置模板路径
        if template_path:
            self.template_path = Path(template_path)
        else:
            # 默认模板
            module_dir = Path(__file__).parent
            self.template_path = module_dir / "template" / "template.pptx"
        
        # 设置输出目录
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_dir = self.json_path.parent.parent / "pipeline_outputs" / timestamp
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化结果
        self.result = PipelineResult(success=False)
        self.slides = []
    
    def run(self) -> PipelineResult:
        """
        执行完整Pipeline
        
        Returns:
            Pipeline执行结果
        """
        print("=" * 60)
        print("🚀 开始视频生成Pipeline")
        print(f"   输入: {self.json_path}")
        print(f"   输出: {self.output_dir}")
        print("=" * 60)
        
        try:
            # Stage 0: 解析演讲稿
            print("\n📋 Stage 0: 解析演讲稿...")
            self.slides = self._run_stage0()
            print(f"   ✅ 解析完成，共 {len(self.slides)} 页")
            
            # Stage 1: 构建Slide结构
            print("\n🔧 Stage 1: 构建Slide结构...")
            self.slides = self._run_stage1()
            print(f"   ✅ 结构构建完成")
            
            # Stage 1.5: PageDirector Agent决策（新增）
            print("\n🎯 Stage 1.5: PageDirector Agent决策...")
            self.slides = self._run_stage1_5()
            total_blocks = sum(len(s.blocks) for s in self.slides)
            print(f"   ✅ 决策完成，共生成 {total_blocks} 个blocks")
            
            # Stage 2: 渲染Manim动画
            print("\n🎨 Stage 2: 渲染Manim动画...")
            self.slides = self._run_stage2()
            gif_count = sum(1 for s in self.slides if s.gif_path)
            print(f"   ✅ 渲染完成，共 {gif_count} 个GIF")
            
            # Stage 3: 生成PPTX
            print("\n📊 Stage 3: 生成PPTX...")
            pptx_path = self._run_stage3()
            print(f"   ✅ PPTX已生成")
            
            # Stage 4: 提取Bounding Box
            print("\n📐 Stage 4: 提取Bounding Box...")
            bboxes = self._run_stage4(pptx_path)
            print(f"   ✅ BBox提取完成")
            
            # Stage 5: VLM布局优化
            print("\n🔄 Stage 5: VLM布局优化...")
            optimized_pptx = self._run_stage5(pptx_path, bboxes)
            print(f"   ✅ 布局优化完成")
            
            # Stage 6: 生成TTS语音
            print("\n🎤 Stage 6: 生成TTS语音...")
            self.slides = self._run_stage6()
            total_duration = sum(s.duration or 0 for s in self.slides)
            print(f"   ✅ 语音生成完成，总时长 {total_duration:.1f}秒")
            
            # 合并音频
            tts_gen = TTSGenerator(str(self.output_dir))
            audio_path = tts_gen.merge_audio(self.slides)
            
            # Stage 7: 生成字幕
            print("\n📝 Stage 7: 生成字幕...")
            subtitle_path = self._run_stage7()
            print(f"   ✅ 字幕生成完成")
            
            # Stage 8: 合成视频
            print("\n🎬 Stage 8: 合成视频...")
            video_path = self._run_stage8(optimized_pptx, audio_path, subtitle_path)
            print(f"   ✅ 视频合成完成")
            
            # 保存slides数据
            self._save_slides_data()
            
            # 构建结果
            self.result = PipelineResult(
                success=True,
                video_path=video_path,
                pptx_path=optimized_pptx,
                audio_path=audio_path,
                subtitle_path=subtitle_path,
                total_duration=total_duration,
                slides=self.slides
            )
            
            print("\n" + "=" * 60)
            print("✅ Pipeline执行成功!")
            print(f"   视频: {video_path}")
            print(f"   PPTX: {optimized_pptx}")
            print(f"   时长: {total_duration:.1f}秒")
            print("=" * 60)
            
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            print(f"\n❌ Pipeline执行失败: {e}")
            
            self.result = PipelineResult(
                success=False,
                error_message=error_msg,
                slides=self.slides
            )
        
        # 保存执行报告
        self._save_report()
        
        return self.result
    
    def _run_stage0(self):
        """Stage 0: 解析演讲稿"""
        parser = ScriptParser(str(self.json_path))
        return parser.parse()
    
    def _run_stage1(self):
        """Stage 1: 构建Slide结构（使用LLM优化内容）"""
        builder = SlideBuilder(self.slides, use_llm=True)
        return builder.build()
    
    def _run_stage1_5(self):
        """Stage 1.5: PageDirector Agent决策（新增）"""
        agent = PageDirectorAgent()
        return agent.process_slides(self.slides)
    
    def _run_stage2(self):
        """Stage 2: 渲染Manim动画"""
        renderer = ManimRenderer(str(self.output_dir))
        return renderer.render_all(self.slides)
    
    def _run_stage3(self):
        """Stage 3: 生成PPTX"""
        # 从JSON获取标题
        with open(self.json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        title = data.get("outline", {}).get("title", "教学课件")
        
        generator = PPTXGenerator(str(self.template_path), str(self.output_dir))
        return generator.generate(self.slides, title)
    
    def _run_stage4(self, pptx_path):
        """Stage 4: 提取Bounding Box（块级别）"""
        # 传递slides_data以支持块级别的bbox提取
        extractor = BBoxExtractor(str(pptx_path), slides_data=self.slides)
        bboxes = extractor.extract()
        
        # 保存bbox数据
        extractor.save_to_json(str(self.output_dir / "bboxes.json"))
        
        return bboxes
    
    def _run_stage5(self, pptx_path, bboxes):
        """Stage 5: VLM布局优化"""
        optimizer = VLMLayoutOptimizer(str(pptx_path), str(self.output_dir))
        return optimizer.optimize(bboxes, slides_data=self.slides)
    
    def _run_stage6(self):
        """Stage 6: 生成TTS语音"""
        generator = TTSGenerator(str(self.output_dir))
        return generator.generate_all(self.slides)
    
    def _run_stage7(self):
        """Stage 7: 生成字幕"""
        generator = SubtitleGenerator(str(self.output_dir))
        return generator.generate(self.slides)
    
    def _run_stage8(self, pptx_path, audio_path, subtitle_path):
        """Stage 8: 合成视频"""
        composer = VideoComposer(str(self.output_dir))
        return composer.compose(pptx_path, audio_path, subtitle_path, self.slides)
    
    def _save_slides_data(self):
        """保存slides数据"""
        data = {
            "source_file": str(self.json_path),
            "generated_at": datetime.now().isoformat(),
            "slide_count": len(self.slides),
            "slides": [s.to_dict() for s in self.slides]
        }
        
        output_path = self.output_dir / "slides_data.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _save_report(self):
        """保存执行报告"""
        report = {
            "status": "success" if self.result.success else "failed",
            "generated_at": datetime.now().isoformat(),
            "input_file": str(self.json_path),
            "output_dir": str(self.output_dir),
            "result": self.result.to_dict()
        }
        
        output_path = self.output_dir / "pipeline_report.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)


def run_pipeline(
    json_path: str,
    template_path: Optional[str] = None,
    output_dir: Optional[str] = None
) -> PipelineResult:
    """
    便捷函数：运行Pipeline
    
    Args:
        json_path: 演讲稿JSON路径
        template_path: 模板路径
        output_dir: 输出目录
    
    Returns:
        Pipeline结果
    """
    pipeline = VideoPipeline(json_path, template_path, output_dir)
    return pipeline.run()


# 命令行入口
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python main_pipeline.py <json_path> [template_path] [output_dir]")
        sys.exit(1)
    
    json_path = sys.argv[1]
    template_path = sys.argv[2] if len(sys.argv) > 2 else None
    output_dir = sys.argv[3] if len(sys.argv) > 3 else None
    
    result = run_pipeline(json_path, template_path, output_dir)
    
    if result.success:
        print(f"\n✅ 视频生成成功: {result.video_path}")
        sys.exit(0)
    else:
        print(f"\n❌ 视频生成失败: {result.error_message}")
        sys.exit(1)


