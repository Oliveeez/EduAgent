"""
Step 2: 大纲和讲稿生成模块
根据用户选择的知识点，生成PPT大纲和讲稿
"""

import json
import logging
import re
from typing import Dict, List
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class OutlineGenerator:
    """大纲生成器 - Step 2（优化版）"""
    
    def __init__(self, llm_client=None):
        """
        初始化大纲生成器
        
        Args:
            llm_client: LLM客户端（由用户提供的utils.llm）
        """
        self.llm_client = llm_client
        
    async def generate_outline_and_script(self, 
                                         knowledge_points: List[Dict],
                                         user_requirements: Dict,
                                         kg_data: Dict = None) -> Dict:
        """
        生成PPT大纲和讲稿
        
        Args:
            knowledge_points: 用户选择的知识点列表
            user_requirements: 用户需求
                - detail_level: Dict，知识点ID到详细程度的映射 (e.g., {'point1': '精讲', 'point2': '粗讲'})
                - style: 排版风格 (e.g., '简约', '学术', '商务')
                - other_requirements: 其他要求
            kg_data: 知识图谱数据（可选，用于获取更多上下文）
            
        Returns:
            大纲和讲稿数据
        """
        logger.info("=" * 60)
        logger.info("🚀 Step 2: 开始生成大纲和讲稿")
        logger.info("=" * 60)
        
        try:
            # 1. 准备上下文信息
            logger.info("📝 Step 2.1: 准备上下文信息...")
            context = self._prepare_context(knowledge_points, user_requirements, kg_data)
            
            # 2. 使用LLM生成大纲
            logger.info("🤖 Step 2.2: 使用AI生成大纲...")
            outline = await self._generate_outline_with_llm(context, user_requirements)
            
            # 3. 使用LLM生成讲稿
            logger.info("📖 Step 2.3: 使用AI生成讲稿...")
            script = await self._generate_script_with_llm(outline, context, user_requirements)
            
            # 4. 为讲稿添加公式和代码标记（新增功能）
            logger.info("🔖 Step 2.4: 为公式和代码添加标志符...")
            script = self._add_formula_code_markers(script)
            
            # 5. 组装结果
            result = {
                'success': True,
                'outline': outline,
                'script': script,
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'knowledge_points_count': len(knowledge_points),
                    'style': user_requirements.get('style', '默认'),
                    'total_slides': len(outline.get('sections', [])),
                    'has_formula_markers': True,  # 标记已添加公式标志符
                    'has_code_markers': True      # 标记已添加代码标志符
                }
            }
            
            logger.info("=" * 60)
            logger.info("✅ Step 2: 大纲和讲稿生成完成")
            logger.info(f"   📊 章节数: {len(outline.get('sections', []))}")
            logger.info(f"   🎨 风格: {user_requirements.get('style', '默认')}")
            logger.info(f"   🔖 已添加公式/代码标志符")
            logger.info("=" * 60)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 生成大纲和讲稿失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    def _prepare_context(self, knowledge_points: List[Dict], 
                        user_requirements: Dict, kg_data: Dict = None) -> str:
        """准备上下文信息（用于LLM输入）"""
        context_parts = []
        
        # 添加知识点信息
        context_parts.append("**选择的知识点：**\n")
        for idx, point in enumerate(knowledge_points, 1):
            title = point.get('title', '')
            detail_level = user_requirements.get('detail_level', {}).get(point['id'], '标准')
            context_parts.append(f"{idx}. {title} (详细程度: {detail_level})")
            
            # 添加内容预览
            if 'content' in point and point['content']:
                preview = point['content'][:200] + '...'
                context_parts.append(f"   内容预览: {preview}\n")
        
        # 添加用户要求
        context_parts.append("\n**用户要求：**\n")
        context_parts.append(f"- 排版风格: {user_requirements.get('style', '默认')}")
        
        if user_requirements.get('other_requirements'):
            context_parts.append(f"- 其他要求: {user_requirements['other_requirements']}")
        
        return "\n".join(context_parts)
    
    async def _generate_outline_with_llm(self, context: str, user_requirements: Dict) -> Dict:
        """使用LLM生成大纲"""
        if not self.llm_client:
            # 如果没有LLM，使用模板生成
            logger.warning("⚠️  未提供LLM客户端，使用模板生成大纲")
            return self._generate_outline_template(context, user_requirements)
        
        # 构建提示词
        prompt = f"""你是一位经验丰富的教师，请根据以下信息生成一份课程PPT大纲。

{context}

**大纲要求：**
1. 结构清晰，逻辑连贯
2. 每个章节包含3-5个关键点
3. 根据详细程度调整内容密度（精讲的知识点应该有更多细节和例子）
4. 适合{user_requirements.get('style', '默认')}风格的演示
5. 每张幻灯片内容适中，避免信息过载

请以JSON格式返回大纲，格式如下：
{{
  "title": "课程标题",
  "sections": [
    {{
      "title": "章节标题",
      "detail_level": "精讲/粗讲/标准",
      "points": [
        {{
          "title": "知识点标题",
          "content": "简要说明",
          "examples": ["示例1", "示例2"],
          "key_concepts": ["概念1", "概念2"]
        }}
      ]
    }}
  ]
}}

只返回JSON，不要包含其他说明文字。"""

        try:
            # 调用LLM
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, self.llm_client, prompt)
            
            # 清理响应
            response = response.replace("<br>", "\n").strip()
            
            # 移除可能的markdown标记
            response = re.sub(r'^```json\s*', '', response)
            response = re.sub(r'^```\s*', '', response)
            response = re.sub(r'\s*```$', '', response)
            
            # 解析JSON
            outline = json.loads(response)
            logger.info("✅ LLM成功生成大纲")
            return outline
            
        except Exception as e:
            logger.error(f"LLM生成大纲失败: {e}，使用模板生成")
            return self._generate_outline_template(context, user_requirements)
    
    async def _generate_script_with_llm(self, outline: Dict, context: str, 
                                       user_requirements: Dict) -> Dict:
        """使用LLM生成讲稿"""
        if not self.llm_client:
            logger.warning("⚠️  未提供LLM客户端，使用模板生成讲稿")
            return self._generate_script_template(outline)
        
        # 构建提示词（不再要求LLM标记，改由后处理完成）
        prompt = f"""你是一位经验丰富的教师，请根据以下大纲生成详细的讲稿（演讲备注）。

**课程大纲：**
{json.dumps(outline, ensure_ascii=False, indent=2)}

**原始上下文：**
{context}

**讲稿要求：**
1. 为每个章节生成清晰的讲解文本
2. 语言流畅自然，适合口语表达
3. 包含过渡语句，帮助串联内容
4. 根据详细程度调整讲解深度
5. 突出重点，适当举例说明
6. 自然地使用LaTeX公式（用$...$或$$...$$包裹）和代码示例（用```...```或反引号包裹）

请以JSON格式返回讲稿，格式如下：
{{
  "sections": [
    {{
      "title": "章节标题",
      "opening": "章节开场白",
      "points": [
        {{
          "text": "知识点的讲解文本，包含解释、例子和重点..."
        }}
      ],
      "closing": "章节总结"
    }}
  ]
}}

只返回JSON，不要包含其他说明文字。"""

        try:
            # 调用LLM
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, self.llm_client, prompt)
            
            # 清理响应
            response = response.replace("<br>", "\n").strip()
            
            # 移除可能的markdown标记
            response = re.sub(r'^```json\s*', '', response)
            response = re.sub(r'^```\s*', '', response)
            response = re.sub(r'\s*```$', '', response)
            
            # 解析JSON
            script = json.loads(response)
            logger.info("✅ LLM成功生成讲稿")
            return script
            
        except Exception as e:
            logger.error(f"LLM生成讲稿失败: {e}，使用模板生成")
            return self._generate_script_template(outline)
    
    def _add_formula_code_markers(self, script: Dict) -> Dict:
        """
        为讲稿中的公式和代码自动添加标志符（后处理）
        
        Args:
            script: 讲稿数据
            
        Returns:
            添加标记后的讲稿数据
        """
        logger.info("🔖 开始添加公式和代码标志符...")
        
        sections = script.get('sections', [])
        formula_count = 0
        code_count = 0
        
        for section in sections:
            # 处理开场白
            if 'opening' in section:
                section['opening'], f_count, c_count = self._mark_text(section['opening'])
                formula_count += f_count
                code_count += c_count
            
            # 处理知识点
            if 'points' in section:
                for point in section['points']:
                    if 'text' in point:
                        point['text'], f_count, c_count = self._mark_text(point['text'])
                        formula_count += f_count
                        code_count += c_count
            
            # 处理总结
            if 'closing' in section:
                section['closing'], f_count, c_count = self._mark_text(section['closing'])
                formula_count += f_count
                code_count += c_count
        
        logger.info(f"✅ 标记完成：添加了 {formula_count} 个公式标记，{code_count} 个代码标记")
        
        return script
    
    def _should_mark_formula(self, content: str) -> bool:
        """
        判断公式是否需要标记
        
        标记规则：
        - 纯数字：不标记（如 $35$, $94$）
        - 单个字母：不标记（如 $x$, $n$）
        - 过短内容：不标记（<5个字符）
        - 简单表达式：不标记（如 $a+b$, $2x$）
        - 复杂公式：标记（包含\frac, \lim等LaTeX命令或长度>15字符）
        """
        content = content.strip()
        
        # 1. 纯数字，不标记
        if re.match(r'^-?\d+\.?\d*$', content):
            return False
        
        # 2. 单个字母或单个变量，不标记
        if re.match(r'^[a-zA-Z]$', content):
            return False
        
        # 3. 太短（少于5个字符），不标记
        if len(content) < 5:
            return False
        
        # 4. 包含复杂LaTeX命令，一定标记
        complex_commands = [
            r'\\frac', r'\\sum', r'\\int', r'\\lim', r'\\prod',
            r'\\sqrt', r'\\partial', r'\\nabla', r'\\infty',
            r'\\alpha', r'\\beta', r'\\gamma', r'\\theta', r'\\delta',
            r'\\lambda', r'\\mu', r'\\sigma', r'\\phi', r'\\psi',
            r'\\matrix', r'\\begin', r'\\end', r'\\left', r'\\right',
            r'\\cdot', r'\\times', r'\\div'
        ]
        for cmd in complex_commands:
            if cmd in content:
                return True
        
        # 5. 较长的表达式（超过15个字符），标记
        if len(content) > 15:
            return True
        
        # 默认不标记简单表达式
        return False
    
    def _should_mark_code(self, content: str) -> bool:
        """
        判断行内代码是否需要标记
        
        标记规则：
        - 简单变量名：不标记（如 variable, count, x）
        - 纯英文单词：不标记（如 reflexivity, Theorem）
        - 较长代码：标记（>30字符）
        - 包含特殊字符：标记（括号、运算符等）
        """
        content = content.strip()
        
        # 1. 纯英文字母、数字、下划线的简短标识符，不标记
        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', content):
            # 如果长度合理（<30字符），认为是变量名或关键字，不标记
            if len(content) < 30:
                return False
        
        # 2. 包含空格、括号、运算符等，标记
        if re.search(r'[\s()\[\]{}<>+\-*/=.,;:]', content):
            return True
        
        # 3. 较长的内容，标记
        if len(content) > 30:
            return True
        
        # 默认不标记
        return False
    
    def _mark_text(self, text: str) -> tuple:
        """
        为单个文本字段添加标记
        
        Args:
            text: 原始文本
            
        Returns:
            (标记后的文本, 公式数量, 代码数量)
        """
        if not text or not isinstance(text, str):
            return text, 0, 0
        
        formula_count = 0
        code_count = 0
        
        # ===== 第一步：标记代码块（```...```）- 始终标记 =====
        def mark_code_block(match):
            nonlocal code_count
            code = match.group(0)
            # 检查是否已经有标记（避免重复）
            before_text = text[max(0, match.start()-20):match.start()]
            after_text = text[match.end():min(len(text), match.end()+20)]
            
            if '<code_start>' in before_text or '<code_end>' in after_text:
                return code
            
            code_count += 1
            return f'<code_start>{code}<code_end>'
        
        text = re.sub(r'```[\s\S]*?```', mark_code_block, text)
        
        # ===== 第二步：标记行内代码 - 根据规则选择性标记 =====
        def mark_inline_code(match):
            nonlocal code_count
            code = match.group(0)  # 包含反引号，如 `variable`
            content = match.group(1)  # 反引号内的内容
            
            # 检查是否已标记
            before_text = text[max(0, match.start()-20):match.start()]
            after_text = text[match.end():min(len(text), match.end()+20)]
            
            if '<code_start>' in before_text or '<code_end>' in after_text:
                return code
            
            # 判断是否需要标记
            if self._should_mark_code(content):
                code_count += 1
                return f'<code_start>{code}<code_end>'
            
            return code  # 不标记简单变量名
        
        text = re.sub(r'`([^`]+?)`', mark_inline_code, text)
        
        # ===== 第三步：标记公式 - 根据规则选择性标记 =====
        
        # 3.1 行间公式 $$...$$
        def mark_display_formula(match):
            nonlocal formula_count
            formula = match.group(0)  # 包含 $$
            content = match.group(1)  # $$ 之间的内容
            
            # 检查是否已标记
            before_text = text[max(0, match.start()-20):match.start()]
            after_text = text[match.end():min(len(text), match.end()+20)]
            
            if '<formula_start>' in before_text or '<formula_end>' in after_text:
                return formula
            
            # 判断是否需要标记
            if self._should_mark_formula(content):
                formula_count += 1
                return f'<formula_start>{formula}<formula_end>'
            
            return formula
        
        text = re.sub(r'\$\$(.*?)\$\$', mark_display_formula, text)
        
        # 3.2 行内公式 $...$
        def mark_inline_formula(match):
            nonlocal formula_count
            formula = match.group(0)
            content = match.group(1)  # $ 之间的内容
            
            # 检查是否已标记
            before_text = text[max(0, match.start()-20):match.start()]
            after_text = text[match.end():min(len(text), match.end()+20)]
            
            if '<formula_start>' in before_text or '<formula_end>' in after_text:
                return formula
            
            if self._should_mark_formula(content):
                formula_count += 1
                return f'<formula_start>{formula}<formula_end>'
            
            return formula
        
        text = re.sub(r'(?<!\$)\$([^\$]+?)\$(?!\$)', mark_inline_formula, text)
        
        # 3.3 LaTeX 括号格式 \(...\) 和 \[...\]
        def mark_latex_paren(match):
            nonlocal formula_count
            formula = match.group(0)
            content = match.group(1)
            
            # 检查是否已标记
            before_text = text[max(0, match.start()-20):match.start()]
            after_text = text[match.end():min(len(text), match.end()+20)]
            
            if '<formula_start>' in before_text or '<formula_end>' in after_text:
                return formula
            
            if self._should_mark_formula(content):
                formula_count += 1
                return f'<formula_start>{formula}<formula_end>'
            
            return formula
        
        text = re.sub(r'\\\((.*?)\\\)', mark_latex_paren, text)
        text = re.sub(r'\\\[(.*?)\\\]', mark_latex_paren, text)
        
        return text, formula_count, code_count
    
    def _generate_outline_template(self, context: str, user_requirements: Dict) -> Dict:
        """使用模板生成大纲（不使用LLM的降级方案）"""
        return {
            "title": "课程演示",
            "sections": [
                {
                    "title": "第一部分",
                    "detail_level": "标准",
                    "points": [
                        {
                            "title": "知识点1",
                            "content": "这是知识点1的说明",
                            "examples": ["示例1"],
                            "key_concepts": ["概念1"]
                        }
                    ]
                }
            ]
        }
    
    def _generate_script_template(self, outline: Dict) -> Dict:
        """使用模板生成讲稿（不使用LLM的降级方案）"""
        sections = []
        
        for section in outline.get('sections', []):
            section_script = {
                "title": section.get('title', ''),
                "opening": f"现在我们来学习{section.get('title', '')}。",
                "points": [
                    {"text": f"关于{point.get('title', '')}的讲解..."}
                    for point in section.get('points', [])
                ],
                "closing": "以上就是本章节的主要内容。"
            }
            sections.append(section_script)
        
        return {"sections": sections}
    
    def save_outline(self, outline_data: Dict, output_path: str):
        """保存大纲到文件"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(outline_data, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 大纲已保存: {output_path}")
        except Exception as e:
            logger.error(f"❌ 保存失败: {e}")
    
    def remove_formula_code_markers(self, script: Dict) -> Dict:
        """
        移除讲稿中的公式和代码标志符（如果需要的话）
        
        这个函数用于在某些场景下移除标记，比如导出为纯文本时。
        
        Args:
            script: 包含标记的讲稿数据
            
        Returns:
            移除标记后的讲稿数据
        """
        sections = script.get('sections', [])
        
        for section in sections:
            # 处理开场白
            if 'opening' in section:
                section['opening'] = self._remove_markers(section['opening'])
            
            # 处理知识点
            if 'points' in section:
                for point in section['points']:
                    if 'text' in point:
                        point['text'] = self._remove_markers(point['text'])
            
            # 处理总结
            if 'closing' in section:
                section['closing'] = self._remove_markers(section['closing'])
        
        return script
    
    def _remove_markers(self, text: str) -> str:
        """移除单个文本中的所有标记"""
        if not text or not isinstance(text, str):
            return text
        
        # 移除公式标记
        text = text.replace('<formula_start>', '')
        text = text.replace('<formula_end>', '')
        
        # 移除代码标记
        text = text.replace('<code_start>', '')
        text = text.replace('<code_end>', '')
        
        return text