
from manim import *

class CoqScene_5(Scene):
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
        code = """Inductive nat : Type := | O : nat | S : nat -> nat."""
        code_text = Text(code, font="Monospace", font_size=24, color="#9cdcfe", line_spacing=1.2)
        code_text.move_to(ORIGIN + DOWN * 0.3)
        
        if code_text.width > 10:
            code_text.scale(10 / code_text.width)
        if code_text.height > 4.5:
            code_text.scale(4.5 / code_text.height)
        
        self.play(AddTextLetterByLetter(code_text, run_time=max(3, len(code) * 0.03)), rate_func=linear)
        self.wait(2)
