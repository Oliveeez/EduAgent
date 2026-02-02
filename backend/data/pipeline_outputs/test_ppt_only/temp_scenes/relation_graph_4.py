from manim import *

class RelationGraph4(Scene):
    def construct(self):
        # 1. 定义左侧节点：C/Python -> Built-in Integer
        # 左上：语言节点
        left_node = RoundedRectangle(corner_radius=0.2, height=1, width=2.5, color=BLUE, fill_opacity=0.3)
        left_label = Text("C/Python", font_size=24)
        left_group = VGroup(left_node, left_label).shift(LEFT * 3.5 + UP * 1.5)

        # 左下：黑盒节点（Built-in Integer）
        # 使用实心填充模拟“黑盒”概念
        left_target_node = Rectangle(height=1, width=2.5, color=WHITE, fill_color=DARK_GREY, fill_opacity=1)
        left_target_label = Text("Built-in Integer", font_size=24, color=WHITE)
        left_target_group = VGroup(left_target_node, left_target_label).shift(LEFT * 3.5 + DOWN * 1.5)

        # 左侧箭头：实线
        left_arrow = Arrow(left_group.get_bottom(), left_target_group.get_top(), buff=0.1, color=BLUE)
        left_arrow_label = Text("Direct Access", font_size=16, color=BLUE).next_to(left_arrow, LEFT)

        # 2. 定义右侧节点：Coq -> Constructed Natural
        # 右上：语言节点
        right_node = RoundedRectangle(corner_radius=0.2, height=1, width=2.5, color=GREEN, fill_opacity=0.3)
        right_label = Text("Coq", font_size=24)
        right_group = VGroup(right_node, right_label).shift(RIGHT * 3.5 + UP * 1.5)

        # 右下：构建过程节点（Constructed Natural）
        # 使用边框表示容器，内部通过动画展示构建
        right_target_node = Rectangle(height=1.5, width=3.5, color=GREEN_E, stroke_width=2)
        # 内部结构：表示 Peano 公理的构建过程 (O -> S O -> S S O)
        nat_zero = Text("O", font_size=24, color=YELLOW).move_to(right_target_node.get_left() + RIGHT * 0.5)
        arrow_1 = Arrow(start=LEFT, end=RIGHT, max_stroke_width_to_length_ratio=5, color=GREEN).next_to(nat_zero, RIGHT, buff=0.1).scale(0.5)
        nat_succ = Text("S n", font_size=24, color=YELLOW).next_to(arrow_1, RIGHT, buff=0.1)
        
        right_target_inner = VGroup(nat_zero, arrow_1, nat_succ)
        right_target_label = Text("Constructed Natural", font_size=20, color=WHITE).next_to(right_target_node.get_bottom(), UP, buff=0.15)
        
        # 组合右下部分位置
        right_target_container = VGroup(right_target_node, right_target_inner, right_target_label).shift(RIGHT * 3.5 + DOWN * 1.5)
        # 修正内部元素位置以匹配容器移动
        right_target_inner.move_to(right_target_node.get_center() + UP * 0.2)
        right_target_label.move_to(right_target_node.get_bottom() + UP * 0.3)

        # 右侧箭头：虚线
        right_arrow = DashedLine(right_group.get_bottom(), right_target_node.get_top(), buff=0.1, color=GREEN)
        right_arrow.add_tip()
        right_arrow_label = Text("Inductive Def", font_size=16, color=GREEN).next_to(right_arrow, RIGHT)

        # 3. 动画序列 (总时长控制在 3-4秒)
        
        # 步骤 1: 出现上方语言节点 (0.8s)
        self.play(
            FadeIn(left_group, shift=DOWN),
            FadeIn(right_group, shift=DOWN),
            run_time=0.8
        )

        # 步骤 2: 出现连接关系 (1.0s)
        # 左侧实线箭头直接生长，右侧虚线箭头生成
        self.play(
            GrowArrow(left_arrow),
            Write(left_arrow_label),
            Create(right_arrow),
            Write(right_arrow_label),
            run_time=1.0
        )

        # 步骤 3: 出现结果节点 (1.5s)
        # 左侧：黑盒直接出现
        self.play(FadeIn(left_target_group, scale=0.8), run_time=0.5)
        
        # 右侧：展现从无到有的构建过程
        self.play(Create(right_target_node), run_time=0.5)
        self.play(
            Write(nat_zero),
            run_time=0.3
        )
        self.play(
            GrowArrow(arrow_1),
            Write(nat_succ),
            FadeIn(right_target_label, shift=UP),
            run_time=0.7
        )

        # 4. 停顿
        self.wait(0.5)