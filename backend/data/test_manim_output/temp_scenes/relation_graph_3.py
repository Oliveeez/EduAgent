from manim import *

class RelationGraph3(Scene):
    def construct(self):
        # 配置通用样式
        box_kwargs = {
            "height": 2, 
            "width": 3, 
            "fill_opacity": 0.2, 
            "stroke_width": 2
        }
        text_kwargs = {"font_size": 24}

        # 1. 创建节点
        # 节点1：现实世界
        rect1 = Rectangle(color=BLUE, **box_kwargs)
        text1 = Text("现实世界\n(鸡兔)", **text_kwargs)
        node1 = VGroup(rect1, text1)

        # 节点2：数学符号
        rect2 = Rectangle(color=BLUE, **box_kwargs)
        text2 = Text("数学符号\n(方程)", **text_kwargs)
        node2 = VGroup(rect2, text2)

        # 节点3：机器语言 (重点强调，使用不同颜色和填充度)
        rect3 = Rectangle(color=GOLD, **box_kwargs)
        rect3.set_fill(GOLD, opacity=0.3)
        text3 = Text("机器语言\n(Coq代码)", **text_kwargs)
        node3 = VGroup(rect3, text3)

        # 布局：水平排列
        all_nodes = VGroup(node1, node2, node3).arrange(RIGHT, buff=2.5)

        # 2. 创建箭头和标签
        # 箭头1：建模
        arrow1 = Arrow(start=node1.get_right(), end=node2.get_left(), buff=0.1, color=GREY)
        label1 = Text("数学建模", font_size=20, color=GREY_A).next_to(arrow1, UP, buff=0.1)

        # 箭头2：形式化 (重点强调)
        arrow2 = Arrow(start=node2.get_right(), end=node3.get_left(), buff=0.1, color=GOLD)
        label2 = Text("形式化", font_size=20, color=GOLD).next_to(arrow2, UP, buff=0.1)

        # 3. 动画序列 (总时长约 3.5秒)
        
        # 步骤1：出现现实世界
        self.play(FadeIn(node1, shift=UP), run_time=0.6)
        
        # 步骤2：建模过程 -> 数学符号
        self.play(
            GrowArrow(arrow1),
            Write(label1),
            run_time=0.6
        )
        self.play(FadeIn(node2, shift=UP), run_time=0.6)

        # 步骤3：形式化过程 -> 机器语言 (强调此步骤)
        self.play(
            GrowArrow(arrow2),
            Write(label2),
            run_time=0.6
        )
        self.play(
            DrawBorderThenFill(rect3),
            Write(text3),
            run_time=0.8
        )
        
        # 最后的强调效果
        self.play(
            Indicate(node3, scale_factor=1.1, color=YELLOW),
            run_time=0.8
        )
        
        self.wait(0.5)