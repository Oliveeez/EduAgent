# stage8_video_composer.py
# Stage 8: 视频合成
# 
# 支持两种模式：
# 1. Xvfb + LibreOffice Impress 放映录制（推荐，支持动画）
# 2. 静态图片合成（备用方案）

import subprocess
import os
import time
import signal
from typing import List, Optional, Tuple
from pathlib import Path

from .models import SlideStructure


class VideoComposer:
    """
    视频合成器
    
    功能：
    1. 优先使用Xvfb + LibreOffice Impress放映录制（支持GIF动画）
    2. 备用：将PPTX转换为图片序列后合成
    3. 合并音频和字幕
    """
    
    # 视频参数
    FPS = 30
    WIDTH = 1920
    HEIGHT = 1080
    
    def __init__(self, output_dir: str):
        """
        初始化视频合成器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.videos_dir = self.output_dir / "videos"
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        
        self.frames_dir = self.output_dir / "frames"
        self.frames_dir.mkdir(parents=True, exist_ok=True)
    
    def compose(
        self,
        pptx_path: Path,
        audio_path: Optional[Path],
        subtitle_path: Optional[Path],
        slides: List[SlideStructure]
    ) -> Path:
        """
        合成最终视频
        
        优先使用Xvfb + LibreOffice Impress放映录制（支持动画）
        
        Args:
            pptx_path: PPTX文件路径
            audio_path: 合并后的音频路径
            subtitle_path: SRT字幕路径
            slides: slide列表（用于时长信息）
        
        Returns:
            最终视频路径
        """
        print("  🎬 开始视频合成...")
        
        # 计算总时长（封面3秒 + 各slide时长）
        total_duration = 3.0 + sum(s.duration or 5.0 for s in slides)
        
        # 优先尝试Xvfb + LibreOffice放映录制
        video_no_audio = None
        if self._check_xvfb_available():
            print("    🖥️ 使用Xvfb + LibreOffice放映录制模式...")
            video_no_audio = self._record_pptx_playback(pptx_path, slides, total_duration)
        
        # 如果放映录制失败，使用备用方案
        if not video_no_audio or not video_no_audio.exists():
            print("    📸 放映录制失败，使用静态图片合成模式...")
            image_paths = self._pptx_to_images(pptx_path, len(slides) + 1)
            
            if not image_paths:
                print("    ⚠️ PPTX转换失败，使用占位图")
                image_paths = self._create_placeholder_images(slides)
            
            print("    🎞️ 生成视频帧序列...")
            video_no_audio = self._create_video_from_images(image_paths, slides)
        
        if not video_no_audio:
            print("    ❌ 视频生成失败")
            return None
        
        # Step 3: 添加音频
        if audio_path and audio_path.exists():
            print("    🔊 添加音频...")
            video_with_audio = self._add_audio(video_no_audio, audio_path)
        else:
            video_with_audio = video_no_audio
        
        # Step 4: 添加字幕
        if subtitle_path and subtitle_path.exists():
            print("    📝 添加字幕...")
            final_video = self._add_subtitles(video_with_audio, subtitle_path)
        else:
            final_video = video_with_audio
        
        print(f"  ✅ 视频合成完成: {final_video}")
        return final_video
    
    def _check_xvfb_available(self) -> bool:
        """检查Xvfb是否可用"""
        try:
            result = subprocess.run(["which", "Xvfb"], capture_output=True, text=True)
            if result.returncode != 0:
                print("      ⚠️ Xvfb未安装")
                return False
            
            result = subprocess.run(["which", "xdotool"], capture_output=True, text=True)
            if result.returncode != 0:
                print("      ⚠️ xdotool未安装（用于控制放映）")
                return False
            
            return True
        except Exception as e:
            print(f"      ⚠️ 检查Xvfb失败: {e}")
            return False
    
    def _record_pptx_playback(
        self, 
        pptx_path: Path, 
        slides: List[SlideStructure],
        total_duration: float,
        cover_duration: float = 3.0
    ) -> Optional[Path]:
        """
        使用Xvfb + LibreOffice Impress + FFmpeg录制PPTX放映
        
        流程：
        1. 启动Xvfb虚拟显示器
        2. 在虚拟显示器中启动LibreOffice Impress放映模式
        3. 使用FFmpeg录制虚拟显示器
        4. 使用xdotool控制翻页（按音频时长）
        5. 截掉开头的启动画面
        
        Args:
            pptx_path: PPTX文件路径
            slides: slide列表（用于控制翻页时机）
            total_duration: 总时长
            cover_duration: 封面页时长
        
        Returns:
            录制的视频路径
        """
        raw_output = self.videos_dir / "video_raw.mp4"
        output_path = self.videos_dir / "video_no_audio.mp4"
        display_num = 99  # 使用:99作为虚拟显示器
        
        xvfb_proc = None
        ffmpeg_proc = None
        impress_proc = None
        
        # LibreOffice启动和进入放映的时间（需要截掉）
        startup_delay = 4.0
        
        try:
            # Step 1: 启动Xvfb虚拟显示器
            print("      🖥️ 启动虚拟显示器...")
            xvfb_cmd = [
                "Xvfb", f":{display_num}",
                "-screen", "0", f"{self.WIDTH}x{self.HEIGHT}x24"
            ]
            xvfb_proc = subprocess.Popen(
                xvfb_cmd, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            time.sleep(1)  # 等待Xvfb启动
            
            # 设置DISPLAY环境变量
            env = os.environ.copy()
            env["DISPLAY"] = f":{display_num}"
            
            # Step 2: 启动LibreOffice Impress并进入放映模式
            print("      🎭 启动PPT并进入放映模式...")
            
            # 方法1: 尝试使用--show参数直接进入放映
            impress_cmd = [
                "libreoffice",
                "--impress",
                "--norestore",  # 不显示恢复对话框
                "--show",  # 直接进入放映模式
                str(pptx_path)
            ]
            impress_proc = subprocess.Popen(
                impress_cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # 等待LibreOffice启动
            time.sleep(4)
            
            # 关闭可能的恢复对话框
            subprocess.run(["xdotool", "key", "Escape"], env=env, capture_output=True)
            time.sleep(0.5)
            subprocess.run(["xdotool", "key", "Escape"], env=env, capture_output=True)
            time.sleep(0.5)
            
            # 如果--show没有生效，手动按F5
            print("      🎬 确保进入放映模式...")
            # 先激活窗口
            subprocess.run(["xdotool", "search", "--name", "LibreOffice", "windowactivate"], 
                          env=env, capture_output=True, timeout=2)
            time.sleep(0.5)
            
            # 按F5进入放映模式
            subprocess.run(["xdotool", "key", "F5"], env=env, capture_output=True)
            time.sleep(2)  # 等待进入放映模式
            
            # Step 3: 启动FFmpeg录制（从一开始就录，后面截掉开头）
            print("      🎥 开始录制...")
            record_duration = total_duration + startup_delay + 3  # 多录几秒
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-f", "x11grab",
                "-video_size", f"{self.WIDTH}x{self.HEIGHT}",
                "-framerate", str(self.FPS),
                "-i", f":{display_num}",
                "-t", str(record_duration),
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-pix_fmt", "yuv420p",
                str(raw_output)
            ]
            ffmpeg_proc = subprocess.Popen(
                ffmpeg_cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            
            # 额外等待确保放映模式已启动
            time.sleep(1)
            
            # Step 4: 控制翻页（按音频时长精确控制）
            print("      📄 控制翻页...")
            
            # 确保在放映模式下（全屏）
            # 先按一次Home确保在首页
            subprocess.run(["xdotool", "key", "Home"], env=env, capture_output=True)
            time.sleep(0.3)
            
            # 封面页等待
            print(f"        封面页: 等待 {cover_duration:.1f}秒")
            time.sleep(cover_duration)
            
            # 翻到第一个内容页（使用Right或PageDown）
            print("        翻到第1页...")
            subprocess.run(["xdotool", "key", "Right"], env=env, capture_output=True)
            time.sleep(0.3)  # 等待翻页动画
            
            # 按slide时长翻页
            for i, slide in enumerate(slides):
                duration = slide.duration or 5.0
                print(f"        Slide {i+1}: 等待 {duration:.1f}秒")
                
                # 等待当前slide的时长
                time.sleep(duration)
                
                # 按右箭头翻页（如果不是最后一页）
                if i < len(slides) - 1:
                    print(f"        翻到第{i+2}页...")
                    subprocess.run(
                        ["xdotool", "key", "Right"],
                        env=env,
                        capture_output=True
                    )
                    time.sleep(0.3)  # 等待翻页动画
            
            # 最后一页再等待1秒
            time.sleep(1)
            
            print("      ✅ 录制完成")
            
        except Exception as e:
            print(f"      ❌ 放映录制失败: {e}")
            return None
            
        finally:
            # 清理进程
            if ffmpeg_proc:
                ffmpeg_proc.terminate()
                try:
                    ffmpeg_proc.wait(timeout=10)
                except:
                    ffmpeg_proc.kill()
            
            if impress_proc:
                impress_proc.terminate()
                try:
                    impress_proc.wait(timeout=5)
                except:
                    impress_proc.kill()
            
            if xvfb_proc:
                xvfb_proc.terminate()
                try:
                    xvfb_proc.wait(timeout=5)
                except:
                    xvfb_proc.kill()
        
        # Step 5: 截掉开头的启动画面
        if raw_output.exists():
            print(f"      ✂️ 截掉开头 {startup_delay}秒...")
            trim_cmd = [
                "ffmpeg", "-y",
                "-ss", str(startup_delay),  # 跳过开头
                "-i", str(raw_output),
                "-c", "copy",
                str(output_path)
            ]
            result = subprocess.run(trim_cmd, capture_output=True, text=True, timeout=60)
            
            # 清理原始文件
            raw_output.unlink()
            
            if output_path.exists() and output_path.stat().st_size > 1000:
                return output_path
        
        return None
    
    def _pptx_to_images(self, pptx_path: Path, expected_count: int) -> List[Path]:
        """
        将PPTX转换为图片序列
        
        使用LibreOffice进行转换
        
        Args:
            pptx_path: PPTX文件路径
            expected_count: 预期的图片数量
        
        Returns:
            图片路径列表
        """
        # 先转PDF
        pdf_path = self.frames_dir / "presentation.pdf"
        
        try:
            # 使用LibreOffice转换
            cmd = [
                "libreoffice",
                "--headless",
                "--convert-to", "pdf",
                "--outdir", str(self.frames_dir),
                str(pptx_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                print(f"      ⚠️ LibreOffice转换失败: {result.stderr[:200]}")
                return []
            
            # 查找生成的PDF
            pdf_files = list(self.frames_dir.glob("*.pdf"))
            if not pdf_files:
                print("      ⚠️ 未找到PDF文件")
                return []
            
            pdf_path = pdf_files[0]
            
        except subprocess.TimeoutExpired:
            print("      ⚠️ LibreOffice转换超时")
            return []
        except FileNotFoundError:
            print("      ⚠️ LibreOffice未安装")
            return []
        except Exception as e:
            print(f"      ⚠️ 转换异常: {e}")
            return []
        
        # PDF转图片
        try:
            cmd = [
                "pdftoppm",
                "-png",
                "-r", "150",  # DPI
                str(pdf_path),
                str(self.frames_dir / "slide")
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                print(f"      ⚠️ PDF转图片失败: {result.stderr[:200]}")
                return []
            
            # 查找生成的图片
            image_paths = sorted(self.frames_dir.glob("slide-*.png"))
            
            return image_paths
            
        except FileNotFoundError:
            print("      ⚠️ pdftoppm未安装")
            return []
        except Exception as e:
            print(f"      ⚠️ PDF转图片异常: {e}")
            return []
    
    def _create_placeholder_images(self, slides: List[SlideStructure]) -> List[Path]:
        """
        创建占位图片（当PPTX转换失败时）
        
        使用支持中文的字体
        
        Args:
            slides: slide列表
        
        Returns:
            占位图片路径列表
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            print("      ⚠️ Pillow未安装")
            return []
        
        # 尝试找到中文字体
        chinese_fonts = [
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
            "/System/Library/Fonts/PingFang.ttc",  # macOS
            "C:/Windows/Fonts/msyh.ttc",  # Windows
        ]
        
        font = None
        small_font = None
        
        for font_path in chinese_fonts:
            try:
                if Path(font_path).exists():
                    font = ImageFont.truetype(font_path, 48)
                    small_font = ImageFont.truetype(font_path, 24)
                    print(f"      使用字体: {font_path}")
                    break
            except:
                continue
        
        if not font:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
                print("      ⚠️ 使用备用字体(不支持中文)")
            except:
                font = ImageFont.load_default()
                small_font = font
                print("      ⚠️ 使用默认字体")
        
        image_paths = []
        
        # 创建封面
        cover = Image.new('RGB', (self.WIDTH, self.HEIGHT), color='white')
        draw = ImageDraw.Draw(cover)
        
        # 封面标题
        title = "教学课件"
        try:
            draw.text((self.WIDTH//2, self.HEIGHT//2), title, fill='darkred', anchor='mm', font=font)
        except:
            draw.text((self.WIDTH//2-100, self.HEIGHT//2-30), title, fill='darkred', font=font)
        
        cover_path = self.frames_dir / "slide_000.png"
        cover.save(cover_path)
        image_paths.append(cover_path)
        
        # 创建内容页
        for i, slide in enumerate(slides):
            img = Image.new('RGB', (self.WIDTH, self.HEIGHT), color='white')
            draw = ImageDraw.Draw(img)
            
            # 标题（使用section_title更好）
            title_text = slide.section_title if slide.section_title else slide.title
            title_text = title_text[:40] if len(title_text) > 40 else title_text
            draw.text((80, 50), title_text, fill='darkred', font=font)
            
            # 内容 - 使用原始演讲稿（如果有）
            content_text = slide.original_text if slide.original_text else slide.text
            
            # 简单换行处理
            lines = []
            current_line = ""
            for char in content_text[:500]:  # 限制长度
                if char == '\n' or len(current_line) >= 45:
                    if current_line:
                        lines.append(current_line)
                    current_line = "" if char == '\n' else char
                else:
                    current_line += char
            if current_line:
                lines.append(current_line)
            
            # 绘制内容
            y = 150
            for line in lines[:12]:  # 最多12行
                draw.text((80, y), line, fill='black', font=small_font)
                y += 40
            
            # 如果有公式，显示
            if slide.formula:
                draw.text((80, y + 20), f"公式: {slide.formula}", fill='blue', font=small_font)
            
            # 如果有代码，显示
            if slide.coq_code:
                code_preview = slide.coq_code[:100].replace('\n', ' ')
                draw.text((80, y + 20), f"代码: {code_preview}...", fill='green', font=small_font)
            
            img_path = self.frames_dir / f"slide_{i+1:03d}.png"
            img.save(img_path)
            image_paths.append(img_path)
        
        return image_paths
    
    def _create_video_from_images(
        self,
        image_paths: List[Path],
        slides: List[SlideStructure]
    ) -> Path:
        """
        从图片序列创建视频，支持GIF动画叠加
        
        Args:
            image_paths: 图片路径列表
            slides: slide列表（用于时长和GIF路径）
        
        Returns:
            视频文件路径
        """
        # 为每个幻灯片生成视频片段
        segment_paths = []
        
        for i, img_path in enumerate(image_paths):
            # 确定这张图片的时长
            if i == 0:
                duration = 3.0  # 封面3秒
                slide = None
            elif i - 1 < len(slides):
                slide = slides[i - 1]
                duration = slide.duration or 5.0
            else:
                slide = None
                duration = 5.0
            
            segment_path = self.frames_dir / f"segment_{i:03d}.mp4"
            
            # 检查是否有GIF需要叠加
            if slide and slide.gif_path and Path(slide.gif_path).exists():
                # 有GIF：创建带动画叠加的视频片段
                self._create_segment_with_gif(
                    img_path, 
                    Path(slide.gif_path), 
                    segment_path, 
                    duration
                )
            else:
                # 无GIF：简单从图片创建视频
                self._create_segment_from_image(img_path, segment_path, duration)
            
            if segment_path.exists():
                segment_paths.append(segment_path)
        
        # 合并所有片段
        output_path = self.videos_dir / "video_no_audio.mp4"
        self._concat_segments(segment_paths, output_path)
        
        return output_path if output_path.exists() else None
    
    def _create_segment_from_image(self, img_path: Path, output_path: Path, duration: float):
        """从单张图片创建视频片段"""
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(img_path),
            "-t", str(duration),
            "-vf", f"scale={self.WIDTH}:{self.HEIGHT}:force_original_aspect_ratio=decrease,pad={self.WIDTH}:{self.HEIGHT}:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", str(self.FPS),
            str(output_path)
        ]
        
        subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    
    def _create_segment_with_gif(self, bg_img: Path, gif_path: Path, output_path: Path, duration: float):
        """
        创建带GIF叠加的视频片段
        
        GIF只播放一次，播放完后保持最后一帧直到幻灯片结束
        """
        # 首先将GIF转换为视频（不循环，只播放一次）
        gif_video = self.frames_dir / f"gif_temp_{bg_img.stem}.mp4"
        
        # 获取GIF信息（时长）
        probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
                     "-of", "default=noprint_wrappers=1:nokey=1", str(gif_path)]
        try:
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
            gif_duration = float(probe_result.stdout.strip()) if probe_result.stdout.strip() else 5.0
        except:
            gif_duration = 5.0  # 默认5秒
        
        # GIF转视频（只播放一次，不循环）
        cmd_gif = [
            "ffmpeg", "-y",
            "-i", str(gif_path),  # 不使用-ignore_loop，只播放一次
            "-vf", "scale=550:-1",  # 缩放GIF
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", str(self.FPS),
            str(gif_video)
        ]
        
        result = subprocess.run(cmd_gif, capture_output=True, text=True, timeout=60)
        
        if not gif_video.exists():
            # GIF转换失败，回退到普通图片
            self._create_segment_from_image(bg_img, output_path, duration)
            return
        
        # 如果slide时长大于GIF时长，需要创建两部分：
        # 1. GIF播放部分（前gif_duration秒，叠加动画）
        # 2. 静态部分（剩余时间，叠加GIF最后一帧）
        
        # overlay位置：右侧区域
        overlay_x = self.WIDTH - 600  # 距右边50像素
        overlay_y = 120  # 距顶部120像素
        
        if duration <= gif_duration + 0.5:
            # slide时长小于等于GIF时长，直接叠加整个GIF
            cmd_overlay = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", str(bg_img),
                "-i", str(gif_video),
                "-filter_complex", 
                f"[0:v]scale={self.WIDTH}:{self.HEIGHT}:force_original_aspect_ratio=decrease,pad={self.WIDTH}:{self.HEIGHT}:(ow-iw)/2:(oh-ih)/2[bg];"
                f"[bg][1:v]overlay={overlay_x}:{overlay_y}:eof_action=pass",
                "-t", str(duration),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-r", str(self.FPS),
                str(output_path)
            ]
            subprocess.run(cmd_overlay, capture_output=True, text=True, timeout=120)
        else:
            # slide时长大于GIF时长，需要拼接：动画部分 + 静态部分
            # 创建带动画的前半部分
            part1 = self.frames_dir / f"part1_{bg_img.stem}.mp4"
            cmd_part1 = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", str(bg_img),
                "-i", str(gif_video),
                "-filter_complex", 
                f"[0:v]scale={self.WIDTH}:{self.HEIGHT}:force_original_aspect_ratio=decrease,pad={self.WIDTH}:{self.HEIGHT}:(ow-iw)/2:(oh-ih)/2[bg];"
                f"[bg][1:v]overlay={overlay_x}:{overlay_y}:eof_action=pass",
                "-t", str(gif_duration + 0.5),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-r", str(self.FPS),
                str(part1)
            ]
            subprocess.run(cmd_part1, capture_output=True, text=True, timeout=120)
            
            # 提取GIF最后一帧
            last_frame = self.frames_dir / f"last_frame_{bg_img.stem}.png"
            cmd_last = [
                "ffmpeg", "-y",
                "-sseof", "-0.1",  # 从倒数0.1秒开始
                "-i", str(gif_video),
                "-frames:v", "1",
                str(last_frame)
            ]
            subprocess.run(cmd_last, capture_output=True, text=True, timeout=10)
            
            # 创建静态后半部分（背景+最后一帧）
            remaining = duration - gif_duration - 0.5
            part2 = self.frames_dir / f"part2_{bg_img.stem}.mp4"
            
            if last_frame.exists():
                cmd_part2 = [
                    "ffmpeg", "-y",
                    "-loop", "1",
                    "-i", str(bg_img),
                    "-loop", "1",
                    "-i", str(last_frame),
                    "-filter_complex", 
                    f"[0:v]scale={self.WIDTH}:{self.HEIGHT}:force_original_aspect_ratio=decrease,pad={self.WIDTH}:{self.HEIGHT}:(ow-iw)/2:(oh-ih)/2[bg];"
                    f"[1:v]scale=550:-1[gif];"
                    f"[bg][gif]overlay={overlay_x}:{overlay_y}",
                    "-t", str(remaining),
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-r", str(self.FPS),
                    str(part2)
                ]
                subprocess.run(cmd_part2, capture_output=True, text=True, timeout=60)
            else:
                # 如果提取最后一帧失败，创建纯背景
                self._create_segment_from_image(bg_img, part2, remaining)
            
            # 拼接两部分
            if part1.exists() and part2.exists():
                concat_file = self.frames_dir / f"concat_{bg_img.stem}.txt"
                with open(concat_file, 'w') as f:
                    f.write(f"file '{part1.absolute()}'\n")
                    f.write(f"file '{part2.absolute()}'\n")
                
                cmd_concat = [
                    "ffmpeg", "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(concat_file),
                    "-c", "copy",
                    str(output_path)
                ]
                subprocess.run(cmd_concat, capture_output=True, text=True, timeout=60)
                
                # 清理
                part1.unlink()
                part2.unlink()
                if last_frame.exists():
                    last_frame.unlink()
            elif part1.exists():
                import shutil
                shutil.move(str(part1), str(output_path))
        
        # 清理临时文件
        if gif_video.exists():
            gif_video.unlink()
    
    def _concat_segments(self, segment_paths: List[Path], output_path: Path):
        """合并视频片段"""
        if not segment_paths:
            return
        
        # 创建concat文件
        concat_file = self.frames_dir / "concat_segments.txt"
        
        with open(concat_file, 'w') as f:
            for seg_path in segment_paths:
                f.write(f"file '{seg_path.absolute()}'\n")
        
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(output_path)
        ]
        
        subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    def _add_audio(self, video_path: Path, audio_path: Path) -> Path:
        """
        添加音频轨道
        
        Args:
            video_path: 视频路径
            audio_path: 音频路径
        
        Returns:
            带音频的视频路径
        """
        output_path = self.videos_dir / "video_with_audio.mp4"
        
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            str(output_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                return output_path
            else:
                print(f"      ⚠️ 添加音频失败: {result.stderr[:200]}")
                return video_path
                
        except Exception as e:
            print(f"      ⚠️ 添加音频异常: {e}")
            return video_path
    
    def _add_subtitles(self, video_path: Path, subtitle_path: Path) -> Path:
        """
        添加字幕
        
        Args:
            video_path: 视频路径
            subtitle_path: SRT字幕路径
        
        Returns:
            最终视频路径
        """
        output_path = self.videos_dir / "final_video.mp4"
        
        # 字幕样式（字体14，靠底部，白字黑边）
        style = (
            "Alignment=2,"      # 底部居中
            "MarginV=20,"       # 距底部20像素
            "FontName=Microsoft YaHei,"
            "FontSize=14,"      # 更小的字体
            "PrimaryColour=&HFFFFFF,"
            "OutlineColour=&H000000,"
            "Outline=1,"
            "Shadow=1"
        )
        
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", f"subtitles={subtitle_path}:force_style='{style}'",
            "-c:a", "copy",
            str(output_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                return output_path
            else:
                print(f"      ⚠️ 添加字幕失败: {result.stderr[:200]}")
                return video_path
                
        except Exception as e:
            print(f"      ⚠️ 添加字幕异常: {e}")
            return video_path


def compose_video(
    pptx_path: Path,
    audio_path: Path,
    subtitle_path: Path,
    slides: List[SlideStructure],
    output_dir: str
) -> Path:
    """
    便捷函数：合成视频
    
    Args:
        pptx_path: PPTX路径
        audio_path: 音频路径
        subtitle_path: 字幕路径
        slides: slide列表
        output_dir: 输出目录
    
    Returns:
        最终视频路径
    """
    composer = VideoComposer(output_dir)
    return composer.compose(pptx_path, audio_path, subtitle_path, slides)


