# formula_scene.py
# Manim场景：数学公式动画

import os

# 延迟导入 manim（只在需要时导入，避免导入错误）
try:
    from manim import *
    MANIM_AVAILABLE = True
except ImportError:
    MANIM_AVAILABLE = False
    # 定义占位符类，避免导入错误
    class Scene:
        pass


# 只有在 manim 可用时才定义这些类
if MANIM_AVAILABLE:
    class FormulaScene(Scene):
        """
        数学公式书写动画场景
        
        特点：
        - 白色背景，黑色公式（适合PPT嵌入）
        - Write动画效果
        - 支持多行公式
        """
        
        def __init__(self, latex_formula: str = "", **kwargs):
            """
            初始化场景
            
            Args:
                latex_formula: LaTeX公式字符串
            """
            super().__init__(**kwargs)
            self.latex_formula = latex_formula
        
        def construct(self):
            """构建动画"""
            # 白色背景（适合PPT）
            self.camera.background_color = WHITE
            
            # 创建公式
            formula = self._create_formula()
            
            # 书写动画
            self.play(Write(formula), run_time=3)
            
            # 停留展示
            self.wait(2)
        
        def _create_formula(self) -> MathTex:
            """创建公式对象"""
            # 清理公式字符串
            formula_str = self.latex_formula.strip()
            
            # 如果不是LaTeX格式，尝试转换
            if not formula_str.startswith('\\') and '=' in formula_str:
                # 简单公式，直接使用
                pass
            
            # 创建MathTex对象
            formula = MathTex(
                formula_str,
                font_size=48,
                color=BLACK
            )
            
            # 如果公式太大，缩放
            if formula.width > 10:
                formula.scale(10 / formula.width)
            if formula.height > 5:
                formula.scale(5 / formula.height)
            
            return formula

    class FormulaSceneWithBox(Scene):
        """
        带装饰框的公式场景
        """
        
        def __init__(self, latex_formula: str = "", title: str = "", **kwargs):
            super().__init__(**kwargs)
            self.latex_formula = latex_formula
            self.title = title
        
        def construct(self):
            self.camera.background_color = WHITE
            
            # 创建标题（如果有）
            if self.title:
                title_text = Text(
                    self.title,
                    font_size=32,
                    color=BLACK,
                    weight=BOLD
                ).to_edge(UP, buff=0.5)
                self.play(FadeIn(title_text))
            
            # 创建公式
            formula = MathTex(
                self.latex_formula.strip(),
                font_size=48,
                color=BLACK
            )
            
            # 缩放处理
            if formula.width > 10:
                formula.scale(10 / formula.width)
            
            # 创建装饰框
            box = SurroundingRectangle(
                formula,
                color="#2196F3",  # 蓝色边框
                buff=0.3,
                corner_radius=0.1,
                stroke_width=2
            )
            
            # 动画
            self.play(Write(formula), run_time=3)
            self.play(Create(box), run_time=0.5)
            
            self.wait(2)

    class MultiFormulaScene(Scene):
        """
        多公式逐步推导场景
        """
        
        def __init__(self, formulas: list = None, **kwargs):
            super().__init__(**kwargs)
            self.formulas = formulas or []
        
        def construct(self):
            self.camera.background_color = WHITE
            
            formula_objs = VGroup()
            
            for i, formula_str in enumerate(self.formulas):
                formula = MathTex(
                    formula_str.strip(),
                    font_size=40,
                    color=BLACK
                )
                formula_objs.add(formula)
            
            # 垂直排列
            formula_objs.arrange(DOWN, buff=0.5)
            
            # 缩放以适应画面
            if formula_objs.width > 10:
                formula_objs.scale(10 / formula_objs.width)
            if formula_objs.height > 5:
                formula_objs.scale(5 / formula_objs.height)
            
            # 逐个显示
            for formula in formula_objs:
                self.play(Write(formula), run_time=2)
            
            self.wait(2)
else:
    # manim 不可用时，定义占位符类
    class FormulaScene:
        pass
    class FormulaSceneWithBox:
        pass
    class MultiFormulaScene:
        pass


def create_formula_scene_file(
    latex_formula: str,
    output_dir: str,
    scene_name: str = "FormulaScene",
    background: str = "transparent"
) -> str:
    """
    创建临时的Manim公式场景文件
    
    支持多个公式（用换行分隔），会垂直排列显示
    默认使用透明背景、黑色字体，适合嵌入白色背景PPT
    
    Args:
        latex_formula: LaTeX公式（可能包含多个，用换行分隔）
        output_dir: 输出目录
        scene_name: 场景类名
        background: 背景色 ("transparent", "white" 或 "dark")
    
    Returns:
        临时文件路径
    """
    # 透明背景用于PPT嵌入
    if background == "transparent":
        bg_setup = 'self.camera.background_color = WHITE  # 将在渲染时设为透明'
        text_color = "BLACK"
    elif background == "white":
        bg_setup = 'self.camera.background_color = WHITE'
        text_color = "BLACK"
    else:
        bg_setup = 'self.camera.background_color = "#1e1e1e"'
        text_color = "WHITE"
    
    # 处理多个公式（换行分隔）
    formulas = [f.strip() for f in latex_formula.split('\n') if f.strip()]
    
    if len(formulas) == 1:
        # 单个公式
        escaped_formula = formulas[0].replace('\\', '\\\\').replace('"', '\\"')
        scene_content = f'''
from manim import *

class {scene_name}(Scene):
    def construct(self):
        {bg_setup}
        
        formula = MathTex(
            r"{escaped_formula}",
            font_size=56,
            color={text_color}
        )
        
        if formula.width > 10:
            formula.scale(10 / formula.width)
        if formula.height > 5:
            formula.scale(5 / formula.height)
        
        self.play(Write(formula), run_time=2.5)
        self.wait(1.5)
'''
    else:
        # 多个公式（如方程组）- 垂直排列
        formula_list = ', '.join([f'r"{f.replace(chr(92), chr(92)+chr(92)).replace(chr(34), chr(92)+chr(34))}"' for f in formulas])
        scene_content = f'''
from manim import *

class {scene_name}(Scene):
    def construct(self):
        {bg_setup}
        
        formulas = [{formula_list}]
        formula_group = VGroup()
        
        for f_str in formulas:
            formula = MathTex(f_str, font_size=52, color={text_color})
            formula_group.add(formula)
        
        formula_group.arrange(DOWN, buff=0.6)
        
        if formula_group.width > 10:
            formula_group.scale(10 / formula_group.width)
        if formula_group.height > 5:
            formula_group.scale(5 / formula_group.height)
        
        for formula in formula_group:
            self.play(Write(formula), run_time=1.2)
        self.wait(1.5)
'''
    
    # 写入临时文件
    temp_file = os.path.join(output_dir, f"{scene_name.lower()}_scene.py")
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(scene_content)
    
    return temp_file


