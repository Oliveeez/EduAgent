"""
Step 2.5: 讲稿编辑模块
支持用户与LLM多轮对话，迭代修改讲稿
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class ScriptEditor:
    """讲稿编辑器 - 支持多轮对话修改"""
    
    def __init__(self, llm_client=None):
        """
        初始化讲稿编辑器
        
        Args:
            llm_client: LLM客户端（由用户提供的utils.llm）
        """
        self.llm_client = llm_client
        self.conversation_history = []
        self.current_script = None
        self.current_outline = None
        self.modification_history = []
        
    def initialize_session(self, outline: Dict, script: Dict):
        """
        初始化编辑会话
        
        Args:
            outline: 当前大纲
            script: 当前讲稿
        """
        self.current_outline = outline
        self.current_script = script
        self.conversation_history = []
        self.modification_history = []
        
        logger.info("✅ 讲稿编辑会话已初始化")
        logger.info(f"   章节数: {len(script.get('sections', []))}")
    
    async def process_user_message(self, user_message: str, 
                                   context: Optional[Dict] = None) -> Dict:
        """
        处理用户消息，返回LLM响应和更新后的讲稿
        
        Args:
            user_message: 用户输入的修改需求
            context: 额外上下文（如指定章节、知识点等）
            
        Returns:
            包含LLM响应、更新后的讲稿、应用的修改等
        """
        logger.info("=" * 60)
        logger.info("🗣️  处理用户消息")
        logger.info("=" * 60)
        
        try:
            # 1. 记录用户消息
            self.conversation_history.append({
                'role': 'user',
                'content': user_message,
                'timestamp': datetime.now().isoformat()
            })
            
            # 2. 构建提示词
            prompt = self._build_modification_prompt(user_message, context)
            
            # 3. 调用LLM获取修改方案
            logger.info("🤖 调用LLM生成修改方案...")
            llm_response = await self._call_llm(prompt)
            
            # 4. 解析LLM响应
            parsed_response = self._parse_llm_response(llm_response)
            
            # 5. 应用修改到讲稿
            if parsed_response.get('modifications'):
                logger.info("🔧 应用修改到讲稿...")
                self._apply_modifications(parsed_response['modifications'])
            
            # 6. 记录助手响应
            assistant_message = parsed_response.get('explanation', llm_response)
            self.conversation_history.append({
                'role': 'assistant',
                'content': assistant_message,
                'timestamp': datetime.now().isoformat(),
                'modifications': parsed_response.get('modifications', [])
            })
            
            # 7. 记录修改历史
            self.modification_history.append({
                'user_request': user_message,
                'modifications': parsed_response.get('modifications', []),
                'timestamp': datetime.now().isoformat()
            })
            
            result = {
                'success': True,
                'assistant_message': assistant_message,
                'updated_script': self.current_script,
                'modifications_applied': len(parsed_response.get('modifications', [])),
                'conversation_history': self.conversation_history
            }
            
            logger.info("=" * 60)
            logger.info("✅ 消息处理完成")
            logger.info(f"   应用修改: {result['modifications_applied']}项")
            logger.info("=" * 60)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 处理消息失败: {e}")
            import traceback
            traceback.print_exc()
            
            # 记录错误
            self.conversation_history.append({
                'role': 'assistant',
                'content': f"抱歉，处理您的请求时出现了错误：{str(e)}",
                'timestamp': datetime.now().isoformat(),
                'error': True
            })
            
            return {
                'success': False,
                'error': str(e),
                'assistant_message': f"抱歉，处理您的请求时出现了错误：{str(e)}",
                'conversation_history': self.conversation_history
            }
    
    def _build_modification_prompt(self, user_message: str, context: Optional[Dict] = None) -> str:
        """构建用于LLM的提示词"""
        
        # 准备当前讲稿的文本表示
        script_text = self._format_script_for_prompt(self.current_script)
        
        # 准备对话历史
        history_text = ""
        if len(self.conversation_history) > 1:
            history_text = "\n**对话历史：**\n"
            for msg in self.conversation_history[-6:]:  # 只包含最近3轮对话
                role = "用户" if msg['role'] == 'user' else "助手"
                history_text += f"{role}: {msg['content']}\n"
        
        prompt = f"""你是一位经验丰富的教学设计专家，正在帮助用户优化课程讲稿。

**当前讲稿：**
{script_text}

{history_text}

**用户的新需求：**
{user_message}

请根据用户需求，提供讲稿修改方案。你需要：
1. 理解用户的修改意图
2. 给出具体的修改建议和理由
3. 生成修改后的讲稿内容

请以以下JSON格式返回：
{{
  "explanation": "你对用户需求的理解和修改思路的说明（用自然语言解释）",
  "modifications": [
    {{
      "section_index": 章节索引（从0开始）,
      "modification_type": "修改类型（replace_opening/replace_closing/update_point/add_point/remove_point/reorder）",
      "target": "修改目标（opening/closing/points）",
      "point_index": 如果是修改具体知识点，则为知识点索引（从0开始），否则为null,
      "new_content": "新的内容",
      "reason": "修改理由"
    }}
  ]
}}

修改类型说明：
- replace_opening: 替换章节开场白
- replace_closing: 替换章节总结
- update_point: 更新某个知识点的讲解
- add_point: 添加新的知识点讲解
- remove_point: 删除某个知识点讲解
- reorder: 调整知识点顺序

注意：
1. 如果用户的需求比较模糊，你可以在explanation中请求澄清
2. 修改内容应该保持讲稿的连贯性和教学逻辑
3. 使用清晰、易懂的语言，适合口语表达
4. 只返回JSON，不要包含markdown代码块标记"""

        return prompt
    
    def _format_script_for_prompt(self, script: Dict) -> str:
        """将讲稿格式化为文本，方便LLM理解"""
        formatted_parts = []
        
        sections = script.get('sections', [])
        for idx, section in enumerate(sections):
            formatted_parts.append(f"\n## 章节 {idx + 1}: {section.get('title', '未命名')}")
            
            if section.get('opening'):
                formatted_parts.append(f"**开场白：**\n{section['opening']}")
            
            points = section.get('points', [])
            for p_idx, point in enumerate(points):
                formatted_parts.append(f"\n**知识点 {p_idx + 1}：**\n{point.get('text', '')}")
            
            if section.get('closing'):
                formatted_parts.append(f"\n**总结：**\n{section['closing']}")
        
        return "\n".join(formatted_parts)
    
    async def _call_llm(self, prompt: str) -> str:
        """调用LLM"""
        if not self.llm_client:
            # 如果没有LLM，返回模拟响应
            logger.warning("⚠️  未提供LLM客户端，返回模拟响应")
            return json.dumps({
                "explanation": "由于未配置LLM，无法处理您的请求。请配置LLM客户端后重试。",
                "modifications": []
            }, ensure_ascii=False)
        
        try:
            # 使用线程池执行同步LLM调用
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, self.llm_client, prompt)
            return response
            
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            raise
    
    def _parse_llm_response(self, response: str) -> Dict:
        """解析LLM响应"""
        try:
            # 清理响应
            response = response.replace("<br>", "\n").strip()
            
            # 移除可能的markdown标记
            import re
            response = re.sub(r'^```json\s*', '', response)
            response = re.sub(r'^```\s*', '', response)
            response = re.sub(r'\s*```$', '', response)
            
            # 解析JSON
            parsed = json.loads(response)
            
            # 验证格式
            if 'explanation' not in parsed:
                parsed['explanation'] = "已理解您的需求，正在应用修改..."
            
            if 'modifications' not in parsed:
                parsed['modifications'] = []
            
            logger.info(f"✅ 成功解析LLM响应，包含 {len(parsed['modifications'])} 项修改")
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            # 如果解析失败，尝试提取explanation
            return {
                'explanation': response,
                'modifications': []
            }
    
    def _apply_modifications(self, modifications: List[Dict]):
        """应用修改到当前讲稿"""
        for mod in modifications:
            try:
                section_idx = mod.get('section_index', 0)
                mod_type = mod.get('modification_type')
                new_content = mod.get('new_content', '')
                
                # 确保章节索引有效
                sections = self.current_script.get('sections', [])
                if section_idx >= len(sections):
                    logger.warning(f"⚠️  章节索引 {section_idx} 超出范围，跳过修改")
                    continue
                
                section = sections[section_idx]
                
                # 应用不同类型的修改
                if mod_type == 'replace_opening':
                    section['opening'] = new_content
                    logger.info(f"  ✓ 替换章节 {section_idx + 1} 的开场白")
                
                elif mod_type == 'replace_closing':
                    section['closing'] = new_content
                    logger.info(f"  ✓ 替换章节 {section_idx + 1} 的总结")
                
                elif mod_type == 'update_point':
                    point_idx = mod.get('point_index', 0)
                    points = section.get('points', [])
                    if point_idx < len(points):
                        points[point_idx]['text'] = new_content
                        logger.info(f"  ✓ 更新章节 {section_idx + 1} 的知识点 {point_idx + 1}")
                    else:
                        logger.warning(f"⚠️  知识点索引 {point_idx} 超出范围")
                
                elif mod_type == 'add_point':
                    if 'points' not in section:
                        section['points'] = []
                    section['points'].append({'text': new_content})
                    logger.info(f"  ✓ 添加知识点到章节 {section_idx + 1}")
                
                elif mod_type == 'remove_point':
                    point_idx = mod.get('point_index', 0)
                    points = section.get('points', [])
                    if point_idx < len(points):
                        points.pop(point_idx)
                        logger.info(f"  ✓ 删除章节 {section_idx + 1} 的知识点 {point_idx + 1}")
                
                elif mod_type == 'reorder':
                    # 重新排序需要特殊处理
                    new_order = mod.get('new_order', [])
                    if new_order and 'points' in section:
                        points = section['points']
                        reordered = [points[i] for i in new_order if i < len(points)]
                        section['points'] = reordered
                        logger.info(f"  ✓ 重新排序章节 {section_idx + 1} 的知识点")
                
                else:
                    logger.warning(f"⚠️  未知的修改类型: {mod_type}")
                
            except Exception as e:
                logger.error(f"应用修改失败: {e}")
                continue
    
    def get_conversation_history(self) -> List[Dict]:
        """获取对话历史"""
        return self.conversation_history
    
    def get_current_script(self) -> Dict:
        """获取当前讲稿"""
        return self.current_script
    
    def get_modification_history(self) -> List[Dict]:
        """获取修改历史"""
        return self.modification_history
    
    def export_session(self) -> Dict:
        """导出完整的编辑会话"""
        return {
            'conversation_history': self.conversation_history,
            'modification_history': self.modification_history,
            'final_script': self.current_script,
            'final_outline': self.current_outline,
            'session_metadata': {
                'total_messages': len(self.conversation_history),
                'total_modifications': len(self.modification_history),
                'exported_at': datetime.now().isoformat()
            }
        }
    
    def save_session(self, output_path: str):
        """保存编辑会话到文件"""
        try:
            session_data = self.export_session()
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 编辑会话已保存: {output_path}")
        except Exception as e:
            logger.error(f"❌ 保存失败: {e}")