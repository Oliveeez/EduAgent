from manim import *

class RelationGraph5(Scene):
    def construct(self):
        # 定义节点位置
        pos_0 = LEFT * 4
        pos_1 = ORIGIN
        pos_2 = RIGHT * 4

        # 创建节点 0 (O)
        # 使用圆圈表示节点，Text表示标签
        circle_0 = Circle(radius=0.8, color=BLUE, fill_opacity=0.2)
        text_0 = Text("0\n(O)", font_size=24).move_to(circle_0.get_center())
        node_0 = VGroup(circle_0, text_0).move_to(pos_0)

        # 创建节点 1 (S O)
        # 稍微增大半径以容纳更长的文本
        circle_1 = Circle(radius=1.0, color=GREEN, fill_opacity=0.2)
        text_1 = Text("1\n(S O)", font_size=24).move_to(circle_1.get_center())
        node_1 = VGroup(circle_1, text_1).move_to(pos_1)

        # 创建节点 2 (S (S O))
        circle_2 = Circle(radius=1.2, color=RED, fill_opacity=0.2)
        text_2 = Text("2\n(S (S O))", font_size=20).move_to(circle_2.get_center())
        node_2 = VGroup(circle_2, text_2).move_to(pos_2)

        # 创建连接箭头和关系标签
        arrow_1 = Arrow(start=node_0.get_right(), end=node_1.get_left(), buff=0.1, color=GREY)
        label_s1 = Text("S", font_size=24, color=YELLOW).next_to(arrow_1, UP)

        arrow_2 = Arrow(start=node_1.get_right(), end=node_2.get_left(), buff=0.1, color=GREY)
        label_s2 = Text("S", font_size=24, color=YELLOW).next_to(arrow_2, UP)

        # 动画序列 (总时长约 3.5秒)
        
        # 1. 显示起始节点 0
        self.play(DrawBorderThenFill(node_0), run_time=0.7)
        
        # 2. 从 0 指向 1 (应用 S 操作)
        self.play(
            GrowArrow(arrow_1),
            Write(label_s1),
            run_time=0.5
        )
        self.play(FadeIn(node_1, shift=RIGHT), run_time=0.7)
        
        # 3. 从 1 指向 2 (再次应用 S 操作)
        self.play(
            GrowArrow(arrow_2),
            Write(label_s2),
            run_time=0.5
        )
        self.play(FadeIn(node_2, shift=RIGHT), run_time=0.7)

        # 停顿
        self.wait(0.5)