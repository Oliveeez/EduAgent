from manim import *

class RelationGraph3(Scene):
    def construct(self):
        # 创建坐标轴
        axes = Axes(
            x_range=[0, 10, 1],
            y_range=[0, 1.2, 0.2],
            x_length=8,
            y_length=5,
            axis_config={"include_tip": True, "tip_shape": ArrowTriangleFilled},
        ).add_coordinates()
        
        # 移动坐标轴位置
        axes.to_edge(LEFT, buff=1)

        # 添加坐标轴标签
        x_label = Text("问题规模/步骤数", font="Noto Sans CJK SC", font_size=20).next_to(axes.x_axis, RIGHT)
        y_label = Text("可靠性/准确率", font="Noto Sans CJK SC", font_size=20).next_to(axes.y_axis, UP)

        # 定义曲线函数
        # 曲线A（人脑）：指数衰减，初始高，随后快速下降
        graph_human = axes.plot(lambda x: 1.0 * np.exp(-0.4 * x), x_range=[0, 10], color=RED)
        
        # 曲线B（机器）：保持顶部水平直线
        graph_machine = axes.plot(lambda x: 0.98, x_range=[0, 10], color=BLUE)

        # 曲线标签
        label_human = Text("曲线A (人脑)", font="Noto Sans CJK SC", font_size=20, color=RED).next_to(graph_human.get_point_from_function(2), DOWN + RIGHT)
        label_machine = Text("曲线B (机器)", font="Noto Sans CJK SC", font_size=20, color=BLUE).next_to(graph_machine.get_point_from_function(2), UP)

        # 强调差距的虚线和文字
        x_pos = 9
        gap_line = DashedLine(
            start=axes.c2p(x_pos, 1.0 * np.exp(-0.4 * x_pos)),
            end=axes.c2p(x_pos, 0.98),
            color=YELLOW
        )
        gap_text = Text("巨大差距", font="Noto Sans CJK SC", font_size=24, color=YELLOW).next_to(gap_line, LEFT)

        # 动画播放
        # 1. 绘制坐标轴和标签 (1秒)
        self.play(Create(axes), Write(x_label), Write(y_label), run_time=1)
        
        # 2. 绘制两条曲线 (2秒)
        self.play(Create(graph_human), Create(graph_machine), run_time=2)
        
        # 3. 显示标签和差距强调 (1秒)
        self.play(
            Write(label_human), 
            Write(label_machine), 
            Create(gap_line), 
            Write(gap_text),
            run_time=1
        )
        
        self.wait(1)