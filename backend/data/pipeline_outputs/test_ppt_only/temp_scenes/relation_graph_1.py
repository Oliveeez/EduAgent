from manim import *
import numpy as np

class RelationGraph1(Scene):
    def construct(self):
        # 字体配置
        font_style = "Noto Sans CJK SC"
        
        # 1. 创建坐标轴
        # 左侧坐标轴 (单元测试)
        ax_left = Axes(
            x_range=[0, 5, 1],
            y_range=[0, 5, 1],
            x_length=4.5,
            y_length=4,
            axis_config={"include_tip": True, "tip_length": 0.2}
        ).shift(LEFT * 3.5)
        
        # 右侧坐标轴 (形式化验证)
        ax_right = Axes(
            x_range=[0, 5, 1],
            y_range=[0, 5, 1],
            x_length=4.5,
            y_length=4,
            axis_config={"include_tip": True, "tip_length": 0.2}
        ).shift(RIGHT * 3.5)

        # 2. 坐标轴标签 (中文)
        x_label_left = ax_left.get_x_axis_label(Text("X轴", font=font_style, font_size=20), edge=DOWN, direction=DOWN, buff=0.2)
        y_label_left = ax_left.get_y_axis_label(Text("Y轴", font=font_style, font_size=20), edge=LEFT, direction=LEFT, buff=0.2)
        
        x_label_right = ax_right.get_x_axis_label(Text("X轴", font=font_style, font_size=20), edge=DOWN, direction=DOWN, buff=0.2)
        y_label_right = ax_right.get_y_axis_label(Text("Y轴", font=font_style, font_size=20), edge=LEFT, direction=LEFT, buff=0.2)

        # 标题
        title_left = Text("单元测试 (离散覆盖)", font=font_style, font_size=24).next_to(ax_left, UP)
        title_right = Text("形式化验证 (全域覆盖)", font=font_style, font_size=24).next_to(ax_right, UP)

        # 3. 绘制内容
        # 定义一个基础函数 (例如平滑曲线)
        def target_function(x):
            return 0.5 * (x - 2) ** 2 + 1

        # 左侧：散点图 (模拟有限的测试用例)
        sample_inputs = [0.5, 1.2, 2.0, 2.8, 3.5, 4.2]
        dots = VGroup()
        for x in sample_inputs:
            point = ax_left.c2p(x, target_function(x))
            dot = Dot(point, color=YELLOW, radius=0.08)
            dots.add(dot)

        # 右侧：连续曲线和区域 (模拟全域覆盖)
        curve = ax_right.plot(target_function, x_range=[0, 4.5], color=GREEN)
        area = ax_right.get_area(curve, x_range=[0, 4.5], color=GREEN, opacity=0.3)

        # 中间：演进箭头
        arrow = Arrow(start=LEFT, end=RIGHT, color=WHITE, buff=0.5).shift(DOWN * 0.5)
        arrow_text = Text("从概率到确定", font=font_style, font_size=18).next_to(arrow, UP, buff=0.1)

        # 4. 动画流程 (控制在3-4秒左右)
        
        # 第一阶段：显示坐标系和标题 (1秒)
        self.play(
            Create(ax_left), Create(ax_right),
            Write(x_label_left), Write(y_label_left),
            Write(x_label_right), Write(y_label_right),
            Write(title_left), Write(title_right),
            run_time=1
        )

        # 第二阶段：左侧生成散点，中间出现箭头 (1秒)
        self.play(
            LaggedStart(*[GrowFromCenter(dot) for dot in dots], lag_ratio=0.1),
            GrowArrow(arrow),
            Write(arrow_text),
            run_time=1
        )

        # 第三阶段：右侧生成连续曲线和区域 (1.5秒)
        self.play(
            Create(curve),
            FadeIn(area),
            run_time=1.5
        )

        self.wait(0.5)