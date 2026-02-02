# coq_scene.py
# Manim场景：Coq代码动画

import tempfile
import os

# 延迟导入 manim（只在需要时导入，避免导入错误）
try:
    from manim import *
    MANIM_AVAILABLE = True
except ImportError:
    MANIM_AVAILABLE = False
    # 定义占位符类，避免导入错误
    class Scene:
        pass


# 只有在 manim 可用时才定义这些类
if MANIM_AVAILABLE:
    class CoqCodeScene(Scene):
        """
        Coq代码打字机动画场景
        
        特点：
        - 黑色背景，白色/绿色文字
        - 逐字显示效果（打字机动画）
        - IDE风格窗口框架
        """
        
        def __init__(self, coq_code: str = "", **kwargs):
            """
            初始化场景
            
            Args:
                coq_code: Coq代码字符串
            """
            super().__init__(**kwargs)
            self.coq_code = coq_code
        
        def construct(self):
            """构建动画"""
            # 设置背景色
            self.camera.background_color = "#1e1e1e"  # VS Code暗色主题
            
            # 创建IDE窗口框架
            window = self._create_window_frame()
            self.add(window)
            
            # 创建代码文本
            code_text = self._create_code_text()
            
            # 打字机动画
            self.play(
                AddTextLetterByLetter(code_text, run_time=max(3, len(self.coq_code) * 0.05)),
                rate_func=linear
            )
            
            # 停留展示
            self.wait(2)
        
        def _create_window_frame(self) -> VGroup:
            """创建IDE风格窗口框架"""
            # 窗口背景
            bg = RoundedRectangle(
                corner_radius=0.1,
                width=12,
                height=6,
                fill_color="#252526",
                fill_opacity=1,
                stroke_color="#3c3c3c",
                stroke_width=2
            )
            
            # 标题栏
            title_bar = Rectangle(
                width=12,
                height=0.5,
                fill_color="#323233",
                fill_opacity=1,
                stroke_width=0
            ).move_to(bg.get_top() - DOWN * 0.25)
            
            # 窗口按钮（装饰）
            buttons = VGroup()
            colors = ["#ff5f56", "#ffbd2e", "#27c93f"]  # 红黄绿
            for i, color in enumerate(colors):
                btn = Circle(
                    radius=0.08,
                    fill_color=color,
                    fill_opacity=1,
                    stroke_width=0
                ).move_to(title_bar.get_left() + RIGHT * (0.4 + i * 0.25))
                buttons.add(btn)
            
            # 文件名标签
            file_label = Text(
                "coq_proof.v",
                font_size=16,
                color="#cccccc"
            ).move_to(title_bar.get_center())
            
            return VGroup(bg, title_bar, buttons, file_label)
        
        def _create_code_text(self) -> Text:
            """创建代码文本对象"""
            # 处理代码格式
            code = self.coq_code.strip()
            
            # 使用等宽字体
            code_text = Text(
                code,
                font="Monospace",
                font_size=24,
                color="#9cdcfe",  # VS Code蓝色变量色
                line_spacing=1.2
            )
            
            # 调整位置（在窗口内）
            code_text.move_to(ORIGIN + DOWN * 0.3)
            
            # 如果代码太长，缩小字体
            if code_text.width > 10:
                code_text.scale(10 / code_text.width)
            if code_text.height > 4.5:
                code_text.scale(4.5 / code_text.height)
            
            return code_text

    class CoqCodeSceneHighlight(Scene):
        """
        带语法高亮的Coq代码场景（进阶版）
        """
        
        # Coq关键字颜色映射
        KEYWORD_COLOR = "#c586c0"   # 紫色：关键字
        TYPE_COLOR = "#4ec9b0"      # 青色：类型
        COMMENT_COLOR = "#6a9955"   # 绿色：注释
        STRING_COLOR = "#ce9178"    # 橙色：字符串
        OPERATOR_COLOR = "#d4d4d4"  # 白色：操作符
        DEFAULT_COLOR = "#9cdcfe"   # 蓝色：默认
        
        COQ_KEYWORDS = [
            "Inductive", "Definition", "Fixpoint", "Theorem", "Lemma",
            "Proof", "Qed", "match", "with", "end", "forall", "exists",
            "fun", "let", "in", "if", "then", "else", "Type", "Prop",
            "nat", "bool", "true", "false", "Require", "Import", "Module"
        ]
        
        def __init__(self, coq_code: str = "", **kwargs):
            super().__init__(**kwargs)
            self.coq_code = coq_code
        
        def construct(self):
            self.camera.background_color = "#1e1e1e"
            
            # 创建窗口框架
            window = self._create_window_frame()
            self.add(window)
            
            # 创建高亮代码
            code_group = self._create_highlighted_code()
            
            # 逐行显示动画
            for line in code_group:
                self.play(FadeIn(line, shift=LEFT * 0.2), run_time=0.5)
            
            self.wait(2)
        
        def _create_window_frame(self) -> VGroup:
            """创建IDE窗口框架"""
            bg = RoundedRectangle(
                corner_radius=0.1,
                width=12,
                height=6,
                fill_color="#252526",
                fill_opacity=1,
                stroke_color="#3c3c3c",
                stroke_width=2
            )
            
            title_bar = Rectangle(
                width=12,
                height=0.5,
                fill_color="#323233",
                fill_opacity=1,
                stroke_width=0
            ).move_to(bg.get_top() - DOWN * 0.25)
            
            buttons = VGroup()
            colors = ["#ff5f56", "#ffbd2e", "#27c93f"]
            for i, color in enumerate(colors):
                btn = Circle(
                    radius=0.08,
                    fill_color=color,
                    fill_opacity=1,
                    stroke_width=0
                ).move_to(title_bar.get_left() + RIGHT * (0.4 + i * 0.25))
                buttons.add(btn)
            
            file_label = Text(
                "coq_proof.v",
                font_size=16,
                color="#cccccc"
            ).move_to(title_bar.get_center())
            
            return VGroup(bg, title_bar, buttons, file_label)
        
        def _create_highlighted_code(self) -> VGroup:
            """创建带语法高亮的代码"""
            lines = self.coq_code.strip().split('\n')
            code_group = VGroup()
            
            start_y = 2.0
            
            for i, line in enumerate(lines):
                line_text = self._highlight_line(line)
                line_text.move_to(ORIGIN + UP * (start_y - i * 0.5) + LEFT * 4)
                line_text.align_to(LEFT * 5, LEFT)
                code_group.add(line_text)
            
            # 整体居中
            code_group.move_to(ORIGIN + DOWN * 0.3)
            
            return code_group
        
        def _highlight_line(self, line: str) -> VGroup:
            """高亮单行代码"""
            # 简化处理：按空格分词，检查关键字
            words = line.split()
            word_group = VGroup()
            x_offset = 0
            
            for word in words:
                color = self.DEFAULT_COLOR
                
                # 检查是否是关键字
                clean_word = word.strip('(),:;.')
                if clean_word in self.COQ_KEYWORDS:
                    color = self.KEYWORD_COLOR
                elif clean_word in ["nat", "Type", "Prop", "bool"]:
                    color = self.TYPE_COLOR
                elif word.startswith("(*") or word.endswith("*)"):
                    color = self.COMMENT_COLOR
                
                word_text = Text(
                    word + " ",
                    font="Monospace",
                    font_size=20,
                    color=color
                )
                word_text.shift(RIGHT * x_offset)
                x_offset += word_text.width
                word_group.add(word_text)
            
            return word_group
else:
    # manim 不可用时，定义占位符类
    class CoqCodeScene:
        pass
    class CoqCodeSceneHighlight:
        pass


def create_coq_scene_file(coq_code: str, output_dir: str, scene_name: str = "CoqScene") -> str:
    """
    创建临时的Manim场景文件
    
    Args:
        coq_code: Coq代码
        output_dir: 输出目录
        scene_name: 场景类名
    
    Returns:
        临时文件路径
    """
    # 转义代码中的特殊字符
    escaped_code = coq_code.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    
    scene_content = f'''
from manim import *

class {scene_name}(Scene):
    def construct(self):
        self.camera.background_color = "#1e1e1e"
        
        # 窗口框架
        bg = RoundedRectangle(
            corner_radius=0.1, width=12, height=6,
            fill_color="#252526", fill_opacity=1,
            stroke_color="#3c3c3c", stroke_width=2
        )
        title_bar = Rectangle(
            width=12, height=0.5,
            fill_color="#323233", fill_opacity=1, stroke_width=0
        ).move_to(bg.get_top() - DOWN * 0.25)
        
        buttons = VGroup()
        for i, color in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
            btn = Circle(radius=0.08, fill_color=color, fill_opacity=1, stroke_width=0)
            btn.move_to(title_bar.get_left() + RIGHT * (0.4 + i * 0.25))
            buttons.add(btn)
        
        file_label = Text("coq_proof.v", font_size=16, color="#cccccc")
        file_label.move_to(title_bar.get_center())
        
        self.add(bg, title_bar, buttons, file_label)
        
        # 代码文本
        code = """{escaped_code}"""
        code_text = Text(code, font="Monospace", font_size=24, color="#9cdcfe", line_spacing=1.2)
        code_text.move_to(ORIGIN + DOWN * 0.3)
        
        if code_text.width > 10:
            code_text.scale(10 / code_text.width)
        if code_text.height > 4.5:
            code_text.scale(4.5 / code_text.height)
        
        self.play(AddTextLetterByLetter(code_text, run_time=max(3, len(code) * 0.03)), rate_func=linear)
        self.wait(2)
'''
    
    # 写入临时文件
    temp_file = os.path.join(output_dir, f"{scene_name.lower()}_scene.py")
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(scene_content)
    
    return temp_file


