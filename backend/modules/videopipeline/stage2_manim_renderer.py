# stage2_manim_renderer.py
# Stage 2: Manim GIF渲染器

import os
import subprocess
import tempfile
from typing import List, Optional
from pathlib import Path

from .models import SlideStructure, SlideType
from .manim_scenes.coq_scene import create_coq_scene_file
from .manim_scenes.formula_scene import create_formula_scene_file


class ManimRenderer:
    """
    Manim GIF渲染器
    
    功能：
    1. 为每个code/formula slide生成Manim场景文件
    2. 调用manim命令渲染GIF
    3. 控制GIF只播放一次
    """
    
    def __init__(self, output_dir: str, quality: str = "medium"):
        """
        初始化渲染器
        
        Args:
            output_dir: 输出目录
            quality: 渲染质量 ("low", "medium", "high")
        """
        self.output_dir = Path(output_dir)
        self.gifs_dir = self.output_dir / "gifs"
        self.gifs_dir.mkdir(parents=True, exist_ok=True)
        
        self.temp_dir = self.output_dir / "temp_scenes"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 质量映射
        self.quality_flags = {
            "low": "-ql",
            "medium": "-qm", 
            "high": "-qh"
        }
        self.quality = quality
    
    def render_all(self, slides: List[SlideStructure], parallel: bool = True) -> List[SlideStructure]:
        """
        渲染所有需要动画的slides
        
        Args:
            slides: slide列表
            parallel: 是否并行渲染（默认True）
        
        Returns:
            更新了gif_path的slides列表
        """
        # 筛选需要渲染的slides
        coq_slides = [(i, s) for i, s in enumerate(slides) 
                      if s.slide_type == SlideType.COQ and s.coq_code]
        
        if not coq_slides:
            return slides
        
        if parallel and len(coq_slides) > 1:
            # 并行渲染
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            print(f"  ⚡ 并行渲染 {len(coq_slides)} 个动画...")
            
            with ThreadPoolExecutor(max_workers=min(4, len(coq_slides))) as executor:
                futures = {
                    executor.submit(self._render_coq, slide): idx 
                    for idx, slide in coq_slides
                }
                
                for future in as_completed(futures):
                    idx = futures[future]
                    try:
                        gif_path = future.result()
                        slides[idx].gif_path = gif_path
                    except Exception as e:
                        print(f"     ⚠️ Slide {idx+1} 渲染失败: {e}")
        else:
            # 串行渲染
            for idx, slide in coq_slides:
                gif_path = self._render_coq(slide)
                slides[idx].gif_path = gif_path
        
        return slides
    
    def _render_coq(self, slide: SlideStructure) -> Optional[Path]:
        """
        渲染Coq代码动画
        
        Args:
            slide: 包含coq_code的slide
        
        Returns:
            生成的GIF路径
        """
        scene_name = f"CoqScene_{slide.slide_id}"
        
        # 创建场景文件
        scene_file = create_coq_scene_file(
            coq_code=slide.coq_code,
            output_dir=str(self.temp_dir),
            scene_name=scene_name
        )
        
        # 渲染GIF
        output_name = f"slide_{slide.slide_id:03d}_coq"
        gif_path = self._run_manim(scene_file, scene_name, output_name)
        
        return gif_path
    
    def _render_formula(self, slide: SlideStructure) -> Optional[Path]:
        """
        渲染公式动画
        
        Args:
            slide: 包含formula的slide
        
        Returns:
            生成的GIF路径
        """
        scene_name = f"FormulaScene_{slide.slide_id}"
        
        # 创建场景文件（透明/白色背景，黑色字体）
        scene_file = create_formula_scene_file(
            latex_formula=slide.formula,
            output_dir=str(self.temp_dir),
            scene_name=scene_name,
            background="transparent"  # 透明背景适合PPT嵌入
        )
        
        # 渲染GIF
        output_name = f"slide_{slide.slide_id:03d}_formula"
        gif_path = self._run_manim(scene_file, scene_name, output_name)
        
        return gif_path
    
    def _run_manim(
        self,
        scene_file: str,
        scene_name: str,
        output_name: str
    ) -> Optional[Path]:
        """
        执行manim命令渲染GIF
        
        Args:
            scene_file: 场景文件路径
            scene_name: 场景类名
            output_name: 输出文件名（不含扩展名）
        
        Returns:
            生成的GIF路径，失败返回None
        """
        import shutil
        
        output_file = self.gifs_dir / f"{output_name}.gif"
        
        # 构建manim命令 - 使用 --media_dir 指定输出目录
        quality_flag = self.quality_flags.get(self.quality, "-qm")
        media_dir = self.output_dir / "manim_media"
        media_dir.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            "manim",
            quality_flag,
            "--format=gif",
            "--disable_caching",
            f"--media_dir={media_dir}",
            scene_file,
            scene_name
        ]
        
        print(f"  🎬 渲染: {output_name}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,  # 2分钟超时
                cwd=str(self.output_dir)  # 在输出目录运行
            )
            
            # 不管returncode，先查找生成的GIF
            # Manim输出在 media_dir/videos/{scene_file_stem}/{quality}/xxx.gif
            scene_file_stem = Path(scene_file).stem
            
            # 搜索所有可能的GIF位置
            search_paths = [
                media_dir / "videos" / scene_file_stem,
                media_dir / "images" / scene_file_stem,
                media_dir,
                Path("media"),
            ]
            
            found_gif = None
            for search_path in search_paths:
                if search_path.exists():
                    for gif in search_path.rglob("*.gif"):
                        if scene_name in gif.name or output_name in gif.name:
                            found_gif = gif
                            break
                if found_gif:
                    break
            
            if found_gif:
                # 移动到目标位置
                shutil.move(str(found_gif), str(output_file))
                print(f"     ✅ 成功: {output_file}")
                return output_file
            
            # 如果没找到，检查返回码
            if result.returncode != 0:
                print(f"     ❌ 渲染失败 (exit={result.returncode})")
                if result.stderr:
                    # 只打印最后几行错误
                    stderr_lines = result.stderr.strip().split('\n')
                    for line in stderr_lines[-5:]:
                        print(f"        {line}")
            else:
                print(f"     ⚠️ 命令成功但未找到输出文件")
            
            return None
                
        except subprocess.TimeoutExpired:
            print(f"     ❌ 渲染超时")
            return None
        except Exception as e:
            print(f"     ❌ 渲染异常: {e}")
            return None
    
    def cleanup_temp(self):
        """清理临时文件"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)


def render_slides(slides: List[SlideStructure], output_dir: str) -> List[SlideStructure]:
    """
    便捷函数：渲染所有slides的动画
    
    Args:
        slides: slide列表
        output_dir: 输出目录
    
    Returns:
        更新了gif_path的slides列表
    """
    renderer = ManimRenderer(output_dir)
    return renderer.render_all(slides)


