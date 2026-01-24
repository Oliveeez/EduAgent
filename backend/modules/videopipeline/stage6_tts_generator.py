# stage6_tts_generator.py
# Stage 6: Edge TTS语音生成

import asyncio
import os
from typing import List, Optional
from pathlib import Path
import subprocess

from .models import SlideStructure


class TTSGenerator:
    """
    TTS语音生成器
    
    功能：
    1. 使用Edge TTS为每页生成语音
    2. 控制语速以匹配目标时长
    3. 合并所有音频
    """
    
    # 可用的中文语音
    VOICES = {
        "male": "zh-CN-YunxiNeural",      # 男声
        "female": "zh-CN-XiaoxiaoNeural",  # 女声
        "male2": "zh-CN-YunjianNeural",    # 男声2
    }
    
    def __init__(self, output_dir: str, voice: str = "female"):
        """
        初始化TTS生成器
        
        Args:
            output_dir: 输出目录
            voice: 语音类型 ("male", "female", "male2")
        """
        self.output_dir = Path(output_dir)
        self.audio_dir = self.output_dir / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        
        self.voice = self.VOICES.get(voice, self.VOICES["male"])
    
    async def generate_all_async(self, slides: List[SlideStructure], parallel: bool = True) -> List[SlideStructure]:
        """
        异步生成所有slides的语音
        
        Args:
            slides: slide列表
            parallel: 是否并行生成（默认True）
        
        Returns:
            更新了audio_path和duration的slides列表
        """
        import edge_tts
        
        # 筛选需要生成的slides
        valid_slides = [(i, s) for i, s in enumerate(slides) 
                        if (s.original_text or s.text)]
        
        if not valid_slides:
            return slides
        
        if parallel and len(valid_slides) > 1:
            # 并行生成
            print(f"  ⚡ 并行生成 {len(valid_slides)} 个音频...")
            
            async def generate_one(idx: int, slide: SlideStructure):
                tts_text = slide.original_text if slide.original_text else slide.text
                output_path = self.audio_dir / f"slide_{slide.slide_id:03d}.mp3"
                
                try:
                    communicate = edge_tts.Communicate(
                        text=tts_text,
                        voice=self.voice,
                        rate="+15%"
                    )
                    await communicate.save(str(output_path))
                    duration = self._get_audio_duration(output_path)
                    return idx, output_path, duration, None
                except Exception as e:
                    return idx, None, slide.estimated_duration or 5.0, str(e)
            
            # 并发执行所有TTS任务
            tasks = [generate_one(idx, slide) for idx, slide in valid_slides]
            results = await asyncio.gather(*tasks)
            
            # 处理结果
            for idx, output_path, duration, error in results:
                if error:
                    print(f"  🎤 Slide {slides[idx].slide_id}: ❌ {error}")
                else:
                    slides[idx].audio_path = output_path
                    slides[idx].duration = duration
                    print(f"  🎤 Slide {slides[idx].slide_id}: ✅ {duration:.1f}秒")
        else:
            # 串行生成（带语速调整）
            for idx, slide in valid_slides:
                tts_text = slide.original_text if slide.original_text else slide.text
                output_path = self.audio_dir / f"slide_{slide.slide_id:03d}.mp3"
                
                print(f"  🎤 生成语音: slide {slide.slide_id}")
                
                try:
                    communicate = edge_tts.Communicate(
                        text=tts_text,
                        voice=self.voice,
                        rate="+15%"
                    )
                    await communicate.save(str(output_path))
                    duration = self._get_audio_duration(output_path)
                    
                    # 语速调整逻辑
                    if slide.estimated_duration > 0:
                        target = slide.estimated_duration
                        if duration > 0 and abs(duration - target) / target > 0.15:
                            rate_adjust = int((target / duration - 1) * 50)
                            rate_adjust = max(-50, min(50, rate_adjust))
                            
                            if rate_adjust != 0:
                                print(f"     调整语速: {rate_adjust:+d}%")
                                communicate = edge_tts.Communicate(
                                    text=tts_text,
                                    voice=self.voice,
                                    rate=f"{rate_adjust:+d}%"
                                )
                                await communicate.save(str(output_path))
                                duration = self._get_audio_duration(output_path)
                    
                    slides[idx].audio_path = output_path
                    slides[idx].duration = duration
                    print(f"     ✅ 时长: {duration:.1f}秒")
                    
                except Exception as e:
                    print(f"     ❌ 生成失败: {e}")
                    slides[idx].duration = slide.estimated_duration or 5.0
        
        return slides
    
    def generate_all(self, slides: List[SlideStructure]) -> List[SlideStructure]:
        """
        同步包装：生成所有slides的语音
        
        Args:
            slides: slide列表
        
        Returns:
            更新了audio_path和duration的slides列表
        """
        return asyncio.run(self.generate_all_async(slides))
    
    def _get_audio_duration(self, audio_path: Path) -> float:
        """
        获取音频文件时长
        
        Args:
            audio_path: 音频文件路径
        
        Returns:
            时长（秒）
        """
        try:
            # 使用ffprobe获取时长
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return float(result.stdout.strip())
            
        except Exception as e:
            print(f"     ⚠️ 获取时长失败: {e}")
        
        # 备用方案：根据文件大小估算（MP3约128kbps）
        try:
            file_size = audio_path.stat().st_size
            return file_size / (128 * 1024 / 8)  # 128kbps
        except:
            return 5.0
    
    def merge_audio(self, slides: List[SlideStructure], cover_duration: float = 0.0) -> Path:
        """
        合并所有音频文件
        
        Args:
            slides: 包含audio_path的slides列表
            cover_duration: 封面页时长（秒），现在为0因为视频已截掉开头
        
        Returns:
            合并后的音频文件路径
        """
        # 创建文件列表（直接合并各slide的音频，不添加静音）
        list_file = self.audio_dir / "audio_list.txt"
        with open(list_file, 'w', encoding='utf-8') as f:
            # 直接添加各slide的音频
            for slide in slides:
                if slide.audio_path and slide.audio_path.exists():
                    # ffmpeg concat需要特殊格式
                    f.write(f"file '{slide.audio_path.absolute()}'\n")
        
        # 合并音频
        output_path = self.audio_dir / "full_audio.mp3"
        
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(output_path)
        ]
        
        print(f"  🎵 合并音频...")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"     ✅ 合并完成: {output_path}")
                return output_path
            else:
                print(f"     ❌ 合并失败: {result.stderr[:200]}")
                return None
                
        except Exception as e:
            print(f"     ❌ 合并异常: {e}")
            return None
    
    def get_total_duration(self, slides: List[SlideStructure]) -> float:
        """
        获取总时长
        
        Args:
            slides: slides列表
        
        Returns:
            总时长（秒）
        """
        return sum(s.duration or 0 for s in slides)


def generate_tts(slides: List[SlideStructure], output_dir: str, voice: str = "male") -> List[SlideStructure]:
    """
    便捷函数：生成TTS语音
    
    Args:
        slides: slide列表
        output_dir: 输出目录
        voice: 语音类型
    
    Returns:
        更新了audio_path的slides列表
    """
    generator = TTSGenerator(output_dir, voice)
    return generator.generate_all(slides)


