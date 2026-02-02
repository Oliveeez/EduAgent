from manim import *

class RelationGraph2(Scene):
    def construct(self):
        # 1. 定义节点 (Nodes)
        # 左侧节点：Input: 35
        # 使用圆角矩形，设为蓝色
        node_left_shape = RoundedRectangle(
            corner_radius=0.5, 
            height=1.5, 
            width=3.5, 
            color=BLUE, 
            fill_opacity=0.2
        ).shift(LEFT * 3.5)
        
        node_left_text = Text("Input: 35", font_size=28).move_to(node_left_shape.get_center())
        node_left_group = VGroup(node_left_shape, node_left_text)

        # 右侧节点：Internal: S (S ... O)
        # 使用圆角矩形，设为绿色
        node_right_shape = RoundedRectangle(
            corner_radius=0.5, 
            height=1.5, 
            width=4.5, 
            color=GREEN, 
            fill_opacity=0.2
        ).shift(RIGHT * 3.5)
        
        node_right_text = Text("Internal: S (S ... O)", font_size=28).move_to(node_right_shape.get_center())
        node_right_group = VGroup(node_right_shape, node_right_text)

        # 2. 定义箭头 (Arrows)
        # 上方箭头：从左向右，标记为 'Parse'
        # 使用 CurvedArrow 让连线看起来更像流程图的循环
        arrow_parse = CurvedArrow(
            start_point=node_left_shape.get_top(),
            end_point=node_right_shape.get_top(),
            angle=-TAU/8,  # 向上弯曲
            color=YELLOW
        )
        label_parse = Text("Parse", font_size=24, color=YELLOW).next_to(arrow_parse, UP, buff=0.1)

        # 下方箭头：从右向左，标记为 'Print'
        arrow_print = CurvedArrow(
            start_point=node_right_shape.get_bottom(),
            end_point=node_left_shape.get_bottom(),
            angle=-TAU/8,  # 向下弯曲
            color=RED
        )
        label_print = Text("Print", font_size=24, color=RED).next_to(arrow_print, DOWN, buff=0.1)

        # 3. 动画播放 (Animations)
        # 动画总时长控制在 3.5 秒左右
        
        # 步骤 1: 生成左右节点 (1秒)
        self.play(
            DrawBorderThenFill(node_left_shape),
            Write(node_left_text),
            DrawBorderThenFill(node_right_shape),
            Write(node_right_text),
            run_time=1.0
        )
        
        # 步骤 2: 生成 Parse 过程 (1秒)
        self.play(
            Create(arrow_parse),
            Write(label_parse),
            run_time=1.0
        )
        
        # 步骤 3: 生成 Print 过程 (1秒)
        self.play(
            Create(arrow_print),
            Write(label_print),
            run_time=1.0
        )
        
        self.wait(0.5)