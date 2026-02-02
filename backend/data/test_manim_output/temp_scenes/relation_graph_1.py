
from manim import *

class RelationGraph1(Scene):
    def construct(self):
        axes = Axes(
            x_range=[0, 10, 1],
            y_range=[0, 10, 1],
            x_length=7,
            y_length=5,
            axis_config={"include_tip": True}
        )
        x_label = axes.get_x_axis_label("X", direction=DOWN)
        y_label = axes.get_y_axis_label("Y", direction=LEFT)
        graph = axes.plot(lambda x: x**0.5, color=BLUE)
        
        self.play(Create(axes), Write(x_label), Write(y_label))
        self.play(Create(graph))
        self.wait(1)
