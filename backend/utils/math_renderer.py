"""
数学公式渲染工具
将LaTeX数学公式转换为图片，用于插入PPT
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional
import hashlib
import os

logger = logging.getLogger(__name__)


class MathRenderer:
    """数学公式渲染器"""
    
    def __init__(self, cache_dir: str = None):
        """
        初始化渲染器
        
        Args:
            cache_dir: 缓存目录，用于存储已渲染的公式图片
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path("data/math_cache")
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        
    def render_to_image(self, latex: str, output_path: str = None, 
                       dpi: int = 300, fontsize: int = 12) -> str:
        """
        将LaTeX公式渲染为PNG图片
        
        Args:
            latex: LaTeX公式字符串
            output_path: 输出路径，如果为None则自动生成
            dpi: 图片分辨率
            fontsize: 字体大小
            
        Returns:
            图片文件路径
        """
        # 检查缓存
        cache_key = self._get_cache_key(latex, dpi, fontsize)
        cached_path = self.cache_dir / f"{cache_key}.png"
        
        if cached_path.exists():
            logger.info(f"📦 使用缓存的公式图片: {cache_key}")
            if output_path:
                import shutil
                shutil.copy(cached_path, output_path)
                return output_path
            return str(cached_path)
        
        # 确定输出路径
        if not output_path:
            output_path = str(cached_path)
        
        # 方法1: 使用matplotlib (推荐，无需额外依赖)
        try:
            return self._render_with_matplotlib(latex, output_path, dpi, fontsize)
        except Exception as e:
            logger.warning(f"Matplotlib渲染失败: {e}, 尝试备用方法")
        
        # 方法2: 使用LaTeX + dvipng (需要系统安装LaTeX)
        try:
            return self._render_with_latex(latex, output_path, dpi)
        except Exception as e:
            logger.error(f"LaTeX渲染失败: {e}")
            # 返回占位符图片
            return self._create_placeholder(output_path, latex)
    
    def _render_with_matplotlib(self, latex: str, output_path: str, 
                                dpi: int, fontsize: int) -> str:
        """使用matplotlib渲染公式（推荐方法）"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib as mpl
            
            # 配置matplotlib使用LaTeX
            mpl.rcParams['text.usetex'] = False  # 先尝试不使用系统LaTeX
            
            # 创建图形
            fig = plt.figure(figsize=(8, 2))
            fig.patch.set_facecolor('white')
            
            # 添加公式文本
            # 确保公式被$包裹
            if not latex.strip().startswith('$'):
                latex_text = f"${latex}$"
            else:
                latex_text = latex
            
            plt.text(0.5, 0.5, latex_text, 
                    fontsize=fontsize,
                    horizontalalignment='center',
                    verticalalignment='center',
                    transform=fig.transFigure)
            
            plt.axis('off')
            
            # 保存为PNG
            plt.savefig(output_path, dpi=dpi, bbox_inches='tight', 
                       pad_inches=0.1, facecolor='white')
            plt.close()
            
            logger.info(f"✅ 公式已渲染 (matplotlib): {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Matplotlib渲染错误: {e}")
            raise
    
    def _render_with_latex(self, latex: str, output_path: str, dpi: int) -> str:
        """使用系统LaTeX + dvipng渲染公式（备用方法）"""
        # 创建临时LaTeX文件
        temp_dir = self.cache_dir / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        tex_file = temp_dir / "temp.tex"
        
        # 生成完整的LaTeX文档
        tex_content = f"""
\\documentclass[12pt]{{article}}
\\usepackage{{amsmath}}
\\usepackage{{amssymb}}
\\pagestyle{{empty}}
\\begin{{document}}
\\[
{latex}
\\]
\\end{{document}}
"""
        
        # 写入文件
        with open(tex_file, 'w', encoding='utf-8') as f:
            f.write(tex_content)
        
        # 编译LaTeX
        try:
            subprocess.run(
                ['latex', '-interaction=nonstopmode', 'temp.tex'],
                cwd=temp_dir,
                check=True,
                capture_output=True
            )
            
            # 转换DVI到PNG
            subprocess.run(
                ['dvipng', '-D', str(dpi), '-T', 'tight', 
                 '-o', output_path, 'temp.dvi'],
                cwd=temp_dir,
                check=True,
                capture_output=True
            )
            
            logger.info(f"✅ 公式已渲染 (LaTeX): {output_path}")
            return output_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"LaTeX编译失败: {e}")
            raise
        except FileNotFoundError:
            logger.error("系统未安装LaTeX或dvipng")
            raise
    
    def _create_placeholder(self, output_path: str, latex: str) -> str:
        """创建占位符图片（渲染失败时使用）"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # 创建白色背景图片
            img = Image.new('RGB', (400, 100), color='white')
            draw = ImageDraw.Draw(img)
            
            # 绘制文本
            text = f"公式渲染失败:\n{latex[:50]}..."
            draw.text((10, 10), text, fill='red')
            
            img.save(output_path)
            logger.warning(f"⚠️  创建占位符图片: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"创建占位符失败: {e}")
            return None
    
    def _get_cache_key(self, latex: str, dpi: int, fontsize: int) -> str:
        """生成缓存键"""
        content = f"{latex}_{dpi}_{fontsize}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def batch_render(self, equations: list, output_dir: str = None) -> dict:
        """
        批量渲染公式
        
        Args:
            equations: 公式列表，每个元素包含latex字段
            output_dir: 输出目录
            
        Returns:
            公式ID到图片路径的映射
        """
        if not output_dir:
            output_dir = self.cache_dir
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(exist_ok=True, parents=True)
        
        results = {}
        
        for idx, eq in enumerate(equations):
            latex = eq.get('latex', '')
            if not latex:
                continue
            
            output_path = output_dir / f"equation_{idx}.png"
            
            try:
                rendered_path = self.render_to_image(latex, str(output_path))
                results[f"equation_{idx}"] = rendered_path
                logger.info(f"✅ 渲染公式 {idx + 1}/{len(equations)}")
            except Exception as e:
                logger.error(f"❌ 渲染公式 {idx} 失败: {e}")
                results[f"equation_{idx}"] = None
        
        logger.info(f"✅ 批量渲染完成: {len(results)}/{len(equations)} 成功")
        return results


def latex_to_text(latex: str) -> str:
    """
    将简单的LaTeX公式转换为纯文本（用于无法渲染时的降级处理）
    
    Args:
        latex: LaTeX公式
        
    Returns:
        近似的文本表示
    """
    # 简单的转换规则
    replacements = {
        r'\frac': '/',
        r'\sqrt': '√',
        r'\sum': '∑',
        r'\int': '∫',
        r'\alpha': 'α',
        r'\beta': 'β',
        r'\gamma': 'γ',
        r'\delta': 'δ',
        r'\pi': 'π',
        r'\theta': 'θ',
        r'\lambda': 'λ',
        r'\mu': 'μ',
        r'\sigma': 'σ',
        r'\infty': '∞',
        r'\leq': '≤',
        r'\geq': '≥',
        r'\neq': '≠',
        r'\approx': '≈',
        r'\times': '×',
        r'\div': '÷',
    }
    
    text = latex
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # 移除花括号
    text = text.replace('{', '').replace('}', '')
    
    # 移除其他LaTeX命令
    import re
    text = re.sub(r'\\[a-zA-Z]+', '', text)
    
    return text.strip()