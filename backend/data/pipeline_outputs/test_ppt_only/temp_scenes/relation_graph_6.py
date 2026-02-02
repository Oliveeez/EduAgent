from manim import *

class RelationGraph6(Scene):
    def construct(self):
        # 定义左侧节点：阿拉伯数字
        text_left = Text("Arabic Numeral (35)", font_size=24)
        rect_left = Rectangle(width=4.0, height=1.5, color=BLUE, fill_opacity=0.3, fill_color=BLUE_E)
        group_left = VGroup(rect_left, text_left).to_edge(LEFT, buff=1.5)

        # 定义右侧节点：内部表示
        text_right = Text("Internal Representation (S ... O)", font_size=24)
        rect_right = Rectangle(width=5.0, height=1.5, color=GREEN, fill_opacity=0.3, fill_color=GREEN_E)
        group_right = VGroup(rect_right, text_right).to_edge(RIGHT, buff=1.5)

        # 定义中间的双向箭头
        arrow = DoubleArrow(
            start=rect_left.get_right(),
            end=rect_right.get_left(),
            buff=0.1,
            color=WHITE,
            tip_length=0.2
        )

        # 定义箭头上方和下方的标签
        label_top = Text("Parsing", font_size=20, color=YELLOW).next_to(arrow, UP, buff=0.1)
        label_bottom = Text("Printing", font_size=20, color=YELLOW).next_to(arrow, DOWN, buff=0.1)

        # 动画过程 (总时长约3.5秒)
        # 1. 创建左右节点 (1.5秒)
        self.play(
            Create(rect_left), Write(text_left),
            Create(rect_right), Write(text_right),
            run_time=1.5
        )
        
        # 2. 生成双向箭头 (1秒)
        self.play(GrowFromCenter(arrow), run_time=1)
        
        # 3. 显示Parsing和Printing标签 (1秒)
        self.play(Write(label_top), Write(label_bottom), run_time=1)
        
        self.wait(0.5)