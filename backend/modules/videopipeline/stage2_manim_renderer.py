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
        渲染所有需要动画的slides（增强版：支持关系图）
        
        Args:
            slides: slide列表
            parallel: 是否并行渲染（默认True）
        
        Returns:
            更新了gif_path的slides列表
        """
        # 筛选需要渲染的slides
        coq_slides = [(i, s) for i, s in enumerate(slides) 
                      if s.slide_type == SlideType.COQ and s.coq_code]
        
        # 筛选需要渲染关系图的slides（新增）
        relation_slides = [(i, s) for i, s in enumerate(slides)
                          if s.manim_relation_config]
        
        if not coq_slides and not relation_slides:
            return slides
        
        # 渲染Coq代码动画
        if coq_slides:
            if parallel and len(coq_slides) > 1:
                # 并行渲染
                from concurrent.futures import ThreadPoolExecutor, as_completed
                
                print(f"  ⚡ 并行渲染 {len(coq_slides)} 个代码动画...")
                
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
        
        # 渲染关系图动画（新增）
        if relation_slides:
            print(f"  📊 渲染 {len(relation_slides)} 个关系图...")
            for idx, slide in relation_slides:
                try:
                    gif_path = self._render_relation(slide)
                    if gif_path:
                        # 更新对应block的内容
                        for block in slide.blocks:
                            if hasattr(block, 'block_type') and block.block_type == 'manim_relation':
                                # 将GIF路径存储到block中
                                if isinstance(block.content, dict):
                                    block.content['gif_path'] = str(gif_path)
                        print(f"     ✓ Slide {idx+1}: 关系图渲染完成")
                except Exception as e:
                    print(f"     ⚠️ Slide {idx+1} 关系图渲染失败: {e}")
        
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
    
    def _render_relation(self, slide: SlideStructure) -> Optional[Path]:
        """
        渲染关系图/函数图（新增）
        
        Args:
            slide: 包含manim_relation_config的slide
        
        Returns:
            GIF文件路径
        """
        config = slide.manim_relation_config
        if not config:
            return None
        
        relation_type = config.get('type', 'function_plot')
        description = config.get('description', '关系图')
        
        print(f"    渲染关系图: {description} (类型: {relation_type})")
        
        # 根据类型生成不同的Manim场景
        if relation_type == 'function_plot':
            return self._render_function_plot(slide, config)
        elif relation_type == 'directed_graph':
            return self._render_directed_graph(slide, config)
        elif relation_type == 'flowchart':
            return self._render_flowchart(slide, config)
        else:
            print(f"      ⚠️ 未知的关系图类型: {relation_type}")
            return None
    
    def _render_function_plot(self, slide: SlideStructure, config: dict) -> Optional[Path]:
        """渲染函数图（增强版：使用LLM生成真实代码，带重试）"""
        description = config.get('description', '函数图')
        
        # 使用LLM生成Manim代码（带重试）
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from utils.llm import CustomLLM
        import time
        import re
        
        llm = CustomLLM()
        
        prompt = f"""你是一个Manim代码生成专家。请根据以下描述生成完整的Manim场景代码。

描述：{description}

⚠️ 重要：只能使用以下Manim类和方法：
- 坐标轴：Axes (不要用 NumberPlane, CoordinateSystem)
- 文本：Text, MathTex
- 颜色：BLUE, RED, GREEN, YELLOW, WHITE 等
- 箭头：Arrow (不要用 ArrowTriangleFilled 等不存在的类)
- 形状：Circle, Rectangle, Line
- 动画：Create, Write, FadeIn, FadeOut
- 函数绘制：axes.plot(lambda x: ..., color=BLUE)

要求：
1. 类名必须是：RelationGraph{slide.slide_id}
2. 绘制坐标轴：axes = Axes(x_range=[...], y_range=[...])
3. 轴标签：x_label = Text("X轴", font_size=24).next_to(axes.x_axis, DOWN)
4. 绘制曲线：graph = axes.plot(lambda x: 函数表达式, color=BLUE)
5. 多条曲线用不同颜色：BLUE, RED, GREEN
6. 动画时长3-4秒
7. 只输出Python代码，不要任何解释

示例代码：
```python
from manim import *

class RelationGraph{slide.slide_id}(Scene):
    def construct(self):
        axes = Axes(
            x_range=[0, 10, 1],
            y_range=[0, 10, 1],
            x_length=7,
            y_length=5
        )
        x_label = Text("X轴", font_size=24).next_to(axes.x_axis, DOWN)
        y_label = Text("Y轴", font_size=24).next_to(axes.y_axis, LEFT)
        graph = axes.plot(lambda x: x**2, color=BLUE)
        
        self.play(Create(axes), Write(x_label), Write(y_label))
        self.play(Create(graph))
        self.wait(1)
```"""

        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = llm(prompt)
                
                # 检查是否是错误信息
                if not response or '超时' in response or '错误' in response or len(response) < 50:
                    if attempt < max_retries - 1:
                        print(f"      ⚠️ LLM返回无效响应，重试 {attempt + 1}/{max_retries}")
                        time.sleep(2)
                        continue
                    else:
                        raise ValueError("LLM响应无效，已达最大重试次数")
                
                # 清理HTML标签
                response = re.sub(r'<br\s*/?>', '\n', response)  # 替换<br>为换行
                response = re.sub(r'<[^>]+>', '', response)  # 移除其他HTML标签
                
                # 提取代码块
                code_match = re.search(r'```(?:python)?\s*(.*?)\s*```', response, re.DOTALL)
                if code_match:
                    scene_code = code_match.group(1)
                else:
                    # 如果没有代码块标记，检查是否直接是代码
                    if 'class RelationGraph' in response and 'def construct' in response:
                        scene_code = response
                    else:
                        if attempt < max_retries - 1:
                            print(f"      ⚠️ 未找到有效的Manim代码，重试 {attempt + 1}/{max_retries}")
                            time.sleep(2)
                            continue
                        else:
                            raise ValueError("未找到有效的Manim代码")
                
                # 确保包含必要的import
                if 'from manim import' not in scene_code:
                    scene_code = 'from manim import *\n\n' + scene_code
                
                # 写入场景文件
                scene_file = self.temp_dir / f"relation_graph_{slide.slide_id}.py"
                scene_file.write_text(scene_code)
                
                # 调用Manim渲染
                scene_name = f"RelationGraph{slide.slide_id}"
                gif_path = self._run_manim(scene_file, scene_name, f"slide_{slide.slide_id:03d}_relation")
                
                if gif_path and gif_path.exists():
                    return gif_path
                else:
                    if attempt < max_retries - 1:
                        print(f"      ⚠️ 渲染失败，重试 {attempt + 1}/{max_retries}")
                        time.sleep(2)
                        continue
                    else:
                        raise ValueError("Manim渲染失败")
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"      ⚠️ 尝试 {attempt + 1} 失败: {e}，重试...")
                    time.sleep(2)
                else:
                    print(f"      ❌ 所有重试都失败了: {e}")
                    raise
    
    def _render_directed_graph(self, slide: SlideStructure, config: dict) -> Optional[Path]:
        """渲染有向图（增强版：使用LLM生成真实代码）"""
        description = config.get('description', '有向图')
        
        # 使用LLM生成Manim代码
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from utils.llm import CustomLLM
        llm = CustomLLM()
        
        prompt = f"""你是一个Manim代码生成专家。请根据以下描述生成完整的Manim场景代码。

描述：{description}

⚠️ 重要：只能使用以下Manim类：
- 节点：Circle, Rectangle, RoundedRectangle
- 箭头：Arrow (用法: Arrow(start_point, end_point, buff=0.1))
- 文本：Text (中文可用，font_size=24)
- 颜色：BLUE, RED, GREEN, YELLOW, WHITE
- 动画：Create, Write, FadeIn
- 位置：LEFT, RIGHT, UP, DOWN, shift(), next_to(), move_to()

要求：
1. 类名必须是：RelationGraph{slide.slide_id}
2. 节点示例：circle = Circle(radius=0.5, color=BLUE).shift(LEFT*2)
3. 标签示例：label = Text("节点A", font_size=20).move_to(circle)
4. 箭头示例：arrow = Arrow(circle.get_right(), circle2.get_left(), buff=0.1)
5. 箭头标签：arrow_label = Text("关系", font_size=16).next_to(arrow, UP)
6. 动画时长3-4秒
7. 只输出Python代码，不要解释

示例代码：
```python
from manim import *

class RelationGraph{slide.slide_id}(Scene):
    def construct(self):
        node1 = Circle(radius=0.5, color=BLUE).shift(LEFT*2)
        label1 = Text("A", font_size=24).move_to(node1)
        node2 = Circle(radius=0.5, color=RED).shift(RIGHT*2)
        label2 = Text("B", font_size=24).move_to(node2)
        arrow = Arrow(node1.get_right(), node2.get_left(), buff=0.1)
        
        self.play(Create(node1), Write(label1))
        self.play(Create(arrow))
        self.play(Create(node2), Write(label2))
        self.wait(1)
```"""

        try:
            response = llm(prompt)
            
            # 检查是否是错误信息
            if not response or '超时' in response or '错误' in response or len(response) < 50:
                print(f"      ⚠️ LLM返回无效响应，使用回退方案")
                raise ValueError("Invalid LLM response")
            
            # 清理HTML标签
            import re
            response = re.sub(r'<br\s*/?>', '\n', response)  # 替换<br>为换行
            response = re.sub(r'<[^>]+>', '', response)  # 移除其他HTML标签
            
            # 提取代码块
            code_match = re.search(r'```(?:python)?\s*(.*?)\s*```', response, re.DOTALL)
            if code_match:
                scene_code = code_match.group(1)
            else:
                # 如果没有代码块标记，检查是否直接是代码
                if 'class RelationGraph' in response and 'def construct' in response:
                    scene_code = response
                else:
                    print(f"      ⚠️ 未找到有效的Manim代码，使用回退方案")
                    raise ValueError("No valid Manim code found")
            
            # 确保包含必要的import
            if 'from manim import' not in scene_code:
                scene_code = 'from manim import *\n\n' + scene_code
            
            # 写入场景文件
            scene_file = self.temp_dir / f"relation_graph_{slide.slide_id}.py"
            scene_file.write_text(scene_code)
            
            # 调用Manim渲染
            scene_name = f"RelationGraph{slide.slide_id}"
            gif_path = self._run_manim(scene_file, scene_name, f"slide_{slide.slide_id:03d}_relation")
            
            return gif_path
            
        except Exception as e:
            print(f"      ⚠️ LLM生成Manim代码失败: {e}")
            # 回退到简单模板
            raise
    
    def _render_flowchart(self, slide: SlideStructure, config: dict) -> Optional[Path]:
        """渲染流程图（增强版：使用LLM生成真实代码）"""
        description = config.get('description', '流程图')
        
        # 使用LLM生成Manim代码
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from utils.llm import CustomLLM
        llm = CustomLLM()
        
        prompt = f"""你是一个Manim代码生成专家。请根据以下描述生成完整的Manim场景代码。

描述：{description}

⚠️ 重要：只能使用以下Manim类：
- 流程框：Rectangle, RoundedRectangle
- 箭头：Arrow (用法: Arrow(start, end, buff=0.1))
- 文本：Text (中文可用，font_size=20)
- 颜色：BLUE, RED, GREEN, YELLOW, WHITE
- 动画：Create, Write, FadeIn
- 位置：shift(UP*2), shift(LEFT*3), next_to()

要求：
1. 类名必须是：RelationGraph{slide.slide_id}
2. 流程框示例：box1 = Rectangle(width=2, height=1, color=BLUE).shift(UP*2)
3. 文本示例：text1 = Text("步骤1", font_size=20).move_to(box1)
4. 箭头示例：arrow = Arrow(box1.get_bottom(), box2.get_top(), buff=0.1)
5. 水平布局：shift(LEFT*3), shift(RIGHT*3)
6. 垂直布局：shift(UP*2), shift(DOWN*2)
7. 动画时长3-4秒
8. 只输出Python代码，不要解释

示例代码（三步流程）：
```python
from manim import *

class RelationGraph{slide.slide_id}(Scene):
    def construct(self):
        box1 = Rectangle(width=2, height=1, color=BLUE).shift(UP*2)
        text1 = Text("步骤1", font_size=18).move_to(box1)
        box2 = Rectangle(width=2, height=1, color=GREEN)
        text2 = Text("步骤2", font_size=18).move_to(box2)
        box3 = Rectangle(width=2, height=1, color=RED).shift(DOWN*2)
        text3 = Text("步骤3", font_size=18).move_to(box3)
        
        arrow1 = Arrow(box1.get_bottom(), box2.get_top(), buff=0.1)
        arrow2 = Arrow(box2.get_bottom(), box3.get_top(), buff=0.1)
        
        self.play(Create(box1), Write(text1))
        self.play(Create(arrow1))
        self.play(Create(box2), Write(text2))
        self.play(Create(arrow2))
        self.play(Create(box3), Write(text3))
        self.wait(1)
```"""

        try:
            response = llm(prompt)
            
            # 检查是否是错误信息
            if not response or '超时' in response or '错误' in response or len(response) < 50:
                print(f"      ⚠️ LLM返回无效响应，使用回退方案")
                raise ValueError("Invalid LLM response")
            
            # 清理HTML标签
            import re
            response = re.sub(r'<br\s*/?>', '\n', response)  # 替换<br>为换行
            response = re.sub(r'<[^>]+>', '', response)  # 移除其他HTML标签
            
            # 提取代码块
            code_match = re.search(r'```(?:python)?\s*(.*?)\s*```', response, re.DOTALL)
            if code_match:
                scene_code = code_match.group(1)
            else:
                # 如果没有代码块标记，检查是否直接是代码
                if 'class RelationGraph' in response and 'def construct' in response:
                    scene_code = response
                else:
                    print(f"      ⚠️ 未找到有效的Manim代码，使用回退方案")
                    raise ValueError("No valid Manim code found")
            
            # 确保包含必要的import
            if 'from manim import' not in scene_code:
                scene_code = 'from manim import *\n\n' + scene_code
            
            # 写入场景文件
            scene_file = self.temp_dir / f"relation_graph_{slide.slide_id}.py"
            scene_file.write_text(scene_code)
            
            # 调用Manim渲染
            scene_name = f"RelationGraph{slide.slide_id}"
            gif_path = self._run_manim(scene_file, scene_name, f"slide_{slide.slide_id:03d}_relation")
            
            return gif_path
            
        except Exception as e:
            print(f"      ⚠️ LLM生成Manim代码失败: {e}")
            # 回退到简单模板
            raise
    
    # === 简单回退模板 ===
    


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


