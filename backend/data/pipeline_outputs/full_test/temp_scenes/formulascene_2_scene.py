
from manim import *

class FormulaScene_2(Scene):
    def construct(self):
        self.camera.background_color = WHITE
        
        formula = MathTex(
            r"x + y = 35",
            font_size=48,
            color=BLACK
        )
        
        if formula.width > 10:
            formula.scale(10 / formula.width)
        if formula.height > 5:
            formula.scale(5 / formula.height)
        
        self.play(Write(formula), run_time=3)
        self.wait(2)
