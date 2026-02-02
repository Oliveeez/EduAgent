from manim import *

class RelationGraph2(Scene):
    def construct(self):
        # 定义配置
        box_width = 3.5
        box_height = 1.5
        font_size = 24
        
        # 1. 创建左侧节点：现实世界
        rect_reality = Rectangle(width=box_width, height=box_height, color=BLUE, fill_opacity=0.5)
        text_reality = Text("现实世界\n(Reality)", font_size=font_size)
        node_reality = VGroup(rect_reality, text_reality)
        
        # 2. 创建中间节点：数学模型
        rect_math = Rectangle(width=box_width, height=box_height, color=TEAL, fill_opacity=0.5)
        text_math = Text("数学模型\n(Math Symbols)", font_size=font_size)
        node_math = VGroup(rect_math, text_math)
        
        # 3. 创建右侧节点：形式化验证
        rect_logic = Rectangle(width=box_width, height=box_height, color=GREEN, fill_opacity=0.5)
        text_logic = Text("形式化验证\n(Formal Logic)", font_size=font_size)
        node_logic = VGroup(rect_logic, text_logic)
        
        # 4. 布局位置 (左 -> 中 -> 右)
        node_math.move_to(ORIGIN)
        node_reality.next_to(node_math, LEFT, buff=2.5)
        node_logic.next_to(node_math, RIGHT, buff=2.5)
        
        # 5. 创建箭头
        arrow1 = Arrow(start=rect_reality.get_right(), end=rect_math.get_left(), color=YELLOW, buff=0.1)
        arrow2 = Arrow(start=rect_math.get_right(), end=rect_logic.get_left(), color=YELLOW, buff=0.1)
        
        # 6. 创建箭头下方的标签
        label1 = Text("Abstraction", font_size=20, color=GRAY_A).next_to(arrow1, DOWN, buff=0.1)
        label2 = Text("Formalization", font_size=20, color=GRAY_A).next_to(arrow2, DOWN, buff=0.1)
        
        # 7. 动画流程 (控制在3-4秒内)
        # 第一步：显示三个方框 (1.5秒)
        self.play(
            DrawBorderThenFill(node_reality),
            DrawBorderThenFill(node_math),
            DrawBorderThenFill(node_logic),
            run_time=1.5
        )
        
        # 第二步：显示箭头和标签 (1.5秒)
        self.play(
            GrowArrow(arrow1),
            GrowArrow(arrow2),
            Write(label1),
            Write(label2),
            run_time=1.5
        )
        
        self.wait(0.5)