"""
Step 2: 大纲和讲稿生成模块
根据用户选择的知识点，生成PPT大纲和讲稿
"""

import json
import logging
from typing import Dict, List
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class OutlineGenerator:
    """大纲生成器 - Step 2"""
    
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
            
            # 4. 组装结果
            result = {
                'success': True,
                'outline': outline,
                'script': script,
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'knowledge_points_count': len(knowledge_points),
                    'style': user_requirements.get('style', '默认'),
                    'total_slides': len(outline.get('sections', []))
                }
            }
            
            logger.info("=" * 60)
            logger.info("✅ Step 2: 大纲和讲稿生成完成")
            logger.info(f"   📊 章节数: {len(outline.get('sections', []))}")
            logger.info(f"   🎨 风格: {user_requirements.get('style', '默认')}")
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
            import re
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
        
        # 构建提示词
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

请以JSON格式返回讲稿，格式如下：
{{
  "sections": [
    {{
      "title": "章节标题",
      "opening": "章节开场白",
      "points": [
        {{
          "text": "这个知识点的讲解文本，包含解释、例子和重点..."
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
            import re
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