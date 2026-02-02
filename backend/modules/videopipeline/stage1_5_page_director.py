# stage1_5_page_director.py
# Stage 1.5: PageDirector Agent - 页面意图判别与Block规划

import json
import re
import os
import requests
from typing import List, Dict, Any, Optional
from pathlib import Path

# 尝试加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv 未安装，使用系统环境变量

from .models import SlideStructure, SlideBlock, PageIntent, PageAtom, SemanticRole, BlockType


class PageDirectorAgent:
    """
    页面导演Agent - 范式级重构版
    
    职责：
    1. 内容类型判别
    2. 页面意图判别（Intent Layer）
    3. 原子组合规划
    4. Block级执行计划生成
    """
    
    def __init__(self):
        """初始化Agent"""
        # 延迟导入避免循环依赖
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from utils.llm import CustomLLM
        
        self.llm = CustomLLM()
        self.planner = PagePlanner(self.llm)     # 决策层
        self.executor = BlockExecutor(self.llm)  # 执行层
        self.image_searcher = ImageSearcher()    # 图片搜索器
    
    def process_slides(self, slides: List[SlideStructure]) -> List[SlideStructure]:
        """
        处理所有slides（两阶段流程）
        
        Args:
            slides: Stage 1输出的slide列表
        
        Returns:
            增强后的slide列表（含blocks和决策信息）
        """
        print("  🎯 开始PageDirector Agent决策...")
        enhanced_slides = []
        
        for idx, slide in enumerate(slides):
            print(f"    处理 Slide {slide.slide_id}: {slide.title}")
            
            # 去除try-except，让异常直接抛出（No Fallback）
            # Phase 1: Planner - 生成执行计划
            plan = self.planner.create_plan(slide)
            print(f"      ✓ Intent: {plan.get('page_intent')}")
            print(f"      ✓ Atoms: {', '.join(plan.get('page_atoms', []))}")
            
            # Phase 2: Executor - 执行计划生成具体blocks
            blocks = self.executor.execute_plan(slide, plan)
            original_count = len(blocks)
            print(f"      ✓ Blocks: {original_count}个")
            
            # Phase 3: 文本去重（新增）
            blocks = self._deduplicate_text_blocks(blocks)
            if len(blocks) < original_count:
                print(f"      ✓ 去重后: {len(blocks)}个（移除了{original_count - len(blocks)}个重复项）")
            
            # Phase 4: 搜索图片（如果需要）
            if plan.get('image_search_queries'):
                for query in plan['image_search_queries']:
                    url = self.image_searcher.search(query)
                    if url:
                        # 添加image block（二等公民）
                        blocks.append(self._create_image_block(
                            slide.slide_id, len(blocks), url, query
                        ))
                        print(f"      ✓ Image: {query}")
            
            # Phase 5: 验证计划（Schema Lock）
            self._validate_plan(plan, blocks)
            
            # Phase 6: 更新slide
            slide.page_intent = plan['page_intent']
            slide.page_atoms = plan['page_atoms']
            slide.blocks = blocks
            slide.manim_relation_config = plan.get('manim_relation_config')
            slide.image_search_queries = plan.get('image_search_queries', [])
            slide.needs_split = plan.get('needs_split', False)
            
            enhanced_slides.append(slide)
        
        print(f"  ✅ PageDirector完成，共生成 {sum(len(s.blocks) for s in enhanced_slides)} 个blocks")
        return enhanced_slides
    
    def _validate_plan(self, plan: Dict, blocks: List[SlideBlock]):
        """
        结构不可逃逸（Schema Lock）
        
        任何不合格计划，直接抛出异常
        """
        # 验证page_intent
        valid_intents = [e.value for e in PageIntent]
        if plan["page_intent"] not in valid_intents:
            raise ValueError(f"Invalid page_intent: {plan['page_intent']}, must be one of {valid_intents}")
        
        # 验证至少1个block（放宽到1个，因为有些页面可能很简单）
        if len(blocks) < 1:
            raise ValueError(f"Page must have at least 1 block, got {len(blocks)}")
        
        # 验证每个block的必需字段
        for block in blocks:
            if not hasattr(block, 'block_type'):
                raise ValueError(f"Block missing block_type")
            if not hasattr(block, 'semantic_role'):
                raise ValueError(f"Block missing semantic_role")
            if not hasattr(block, 'estimated_duration'):
                raise ValueError(f"Block missing estimated_duration")
            
            # 验证text block的emphasis关键词数量
            if block.block_type in ["text_line", "conceptual_statement"]:
                if block.emphasis:
                    bold_words = block.emphasis.get("bold", [])
                    if len(bold_words) > 5:
                        print(f"      ⚠️ Too many bold keywords: {len(bold_words)} (max 5), truncating...")
                        block.emphasis["bold"] = bold_words[:5]
        
        # 验证Image不能单独构成页面（Image是二等公民）
        image_blocks = [b for b in blocks if b.block_type == BlockType.IMAGE.value]
        if len(image_blocks) == len(blocks) and len(blocks) > 0:
            raise ValueError("Image blocks cannot be the only content on a page")
    
    def _deduplicate_text_blocks(self, blocks: List[SlideBlock]) -> List[SlideBlock]:
        """
        文本块去重
        
        使用LLM判断哪些文本块内容高度重复，只保留最重要/最完整的那个
        
        Args:
            blocks: 原始blocks列表
        
        Returns:
            去重后的blocks列表
        """
        # 提取所有text_line类型的blocks
        text_blocks = []
        text_indices = []
        for idx, block in enumerate(blocks):
            block_type = block.block_type.value if hasattr(block.block_type, 'value') else str(block.block_type)
            if block_type == "text_line":
                text_blocks.append(block)
                text_indices.append(idx)
        
        # 如果少于2个文本块，无需去重
        if len(text_blocks) < 2:
            return blocks
        
        # 准备LLM输入
        text_contents = []
        for idx, block in enumerate(text_blocks):
            text_contents.append({
                "index": idx,
                "content": block.content,
                "semantic_role": block.semantic_role.value if hasattr(block.semantic_role, 'value') else str(block.semantic_role)
            })
        
        prompt = f"""你是一个文本去重专家。请分析以下文本块，判断哪些内容高度重复（语义相似度>80%）。

文本块列表：
{json.dumps(text_contents, ensure_ascii=False, indent=2)}

任务：
1. 识别内容高度重复的文本块（即使semantic_role不同）
2. 对于每组重复的文本，只保留最完整、最正式、信息量最大的那一个
3. 返回应该保留的文本块索引列表

输出格式（JSON）：
{{
  "duplicates": [
    {{
      "group": [0, 1],  // 这组文本是重复的
      "keep": 0,        // 保留索引0
      "reason": "索引0的表述更完整和正式"
    }}
  ],
  "keep_indices": [0, 2]  // 最终保留的索引列表
}}

只返回JSON，不要其他文字。"""

        try:
            response = self.llm(prompt)
            
            # 清理响应
            import re
            response = re.sub(r'<br\s*/?>', '\n', response)
            response = re.sub(r'```json\s*', '', response, flags=re.IGNORECASE)
            response = re.sub(r'```\s*', '', response)
            response = response.strip()
            
            # 解析JSON
            result = json.loads(response)
            keep_indices = result.get('keep_indices', list(range(len(text_blocks))))
            
            # 构建新的blocks列表
            new_blocks = []
            text_keep_set = set(keep_indices)
            text_block_counter = 0
            
            for idx, block in enumerate(blocks):
                block_type = block.block_type.value if hasattr(block.block_type, 'value') else str(block.block_type)
                if block_type == "text_line":
                    if text_block_counter in text_keep_set:
                        new_blocks.append(block)
                    text_block_counter += 1
                else:
                    new_blocks.append(block)
            
            # 输出去重信息
            if result.get('duplicates'):
                for dup in result['duplicates']:
                    print(f"        去重: {dup['reason']}")
            
            return new_blocks
            
        except Exception as e:
            print(f"      ⚠️ 文本去重失败: {e}，保留所有文本")
            return blocks
    
    def _create_image_block(self, slide_id: int, block_idx: int, url: str, query: str) -> SlideBlock:
        """创建image block（二等公民）"""
        return SlideBlock(
            block_id=f"slide_{slide_id}_block_{block_idx}",
            block_type=BlockType.IMAGE.value,
            content=url,
            semantic_role=SemanticRole.EXAMPLE.value,  # Image永远服务于Concept/Relation
            position_hint="right",
            emphasis=None,
            estimated_duration=2.0,
            subtitle_text=query
        )


class PagePlanner:
    """
    Planner阶段：渐进式分段生成（4个微阶段）
    
    Phase A: 判断页面意图（page_intent）
    Phase B: 选择原子类型（page_atoms）
    Phase C: 创建block骨架（block_blueprint简化版）
    Phase D: 在BlockExecutor中逐个生成block内容
    """
    
    def __init__(self, llm):
        self.llm = llm
    
    def create_plan(self, slide: SlideStructure) -> Dict:
        """
        渐进式生成执行计划（4个微阶段）
        
        Args:
            slide: 当前slide
        
        Returns:
            执行计划dict
        """
        # Phase A: 判断页面意图（单值输出，容易成功）
        page_intent = self._phase_a_judge_intent(slide)
        print(f"      ✓ Intent: {page_intent}")
        
        # Phase B: 选择原子类型（小数组输出）
        page_atoms = self._phase_b_select_atoms(slide, page_intent)
        print(f"      ✓ Atoms: {', '.join(page_atoms)}")
        
        # Phase C: 创建block骨架（简化的blueprint）
        block_blueprint, manim_config, image_queries = self._phase_c_create_blueprint(
            slide, page_intent, page_atoms
        )
        print(f"      ✓ Blueprint: {len(block_blueprint)}个block骨架")
        
        # 组装完整计划
        return {
            "page_intent": page_intent,
            "page_atoms": page_atoms,
            "block_blueprint": block_blueprint,
            "manim_relation_config": manim_config,
            "image_search_queries": image_queries,
            "needs_split": False,
            "reasoning": "Generated by progressive 4-phase planning"
        }
    
    def _phase_a_judge_intent(self, slide: SlideStructure) -> str:
        """
        Phase A: 判断页面意图（最简单，只输出单个枚举值）
        
        Returns:
            page_intent字符串
        """
        prompt = f"""你是PPT页面意图分类器。请判断以下内容的教学意图。

内容：{slide.text[:200]}

可选意图：
1. introduce_concept - 引入新概念
2. motivate_importance - 说明重要性
3. explain_mechanism - 解释原理
4. show_relation - 展示关系
5. walk_through_proof - 讲解证明

只返回意图名称（如：motivate_importance），不要其他文字。"""

        import time
        for attempt in range(3):  # 增加到3次
            try:
                response = self.llm(prompt).strip()
                
                # 检查是否是CustomLLM错误消息
                if "请求大模型失败" in response or "请求大模型超时" in response:
                    print(f"        ⚠️ Phase A API失败: {response[:100]}，等待重试...")
                    if attempt < 2:
                        time.sleep(5)  # 增加延迟到5秒
                        continue
                    else:
                        raise ValueError(f"API调用失败: {response}")
                
                # 验证是否是有效的intent
                valid_intents = ["introduce_concept", "motivate_importance", "explain_mechanism", 
                                "show_relation", "walk_through_proof"]
                if response in valid_intents:
                    return response
                elif attempt < 2:
                    time.sleep(1)
                    continue
            except ValueError as e:
                # 重新抛出API失败异常
                raise
            except:
                if attempt < 2:
                    time.sleep(1)
                    continue
        
        # 所有尝试都失败，抛出异常（去除fallback）
        raise RuntimeError("Failed to determine page intent after all retries")
    
    def _phase_b_select_atoms(self, slide: SlideStructure, page_intent: str) -> List[str]:
        """
        Phase B: 选择原子类型（输出小数组）
        
        Returns:
            page_atoms列表
        """
        prompt = f"""你是PPT内容原子选择器。请选择适合的内容类型。

内容：{slide.text[:200]}
意图：{page_intent}

可选类型（可多选2-3个）：
1. Conceptual Statement - 概念陈述
2. Formula Focus - 公式展示
3. Code Walkthrough - 代码讲解
4. Relational Visualization - 关系图
5. Concept + Visual - 概念+图片

返回JSON数组，如：["Conceptual Statement", "Relational Visualization"]
只返回JSON，不要其他文字。"""

        import time
        for attempt in range(3):  # 增加到3次
            try:
                response = self.llm(prompt).strip()
                
                # 检查是否是CustomLLM错误消息
                if "请求大模型失败" in response or "请求大模型超时" in response:
                    print(f"        ⚠️ Phase B API失败: {response[:100]}，等待重试...")
                    if attempt < 2:
                        time.sleep(5)  # 增加延迟到5秒
                        continue
                    else:
                        raise ValueError(f"API调用失败: {response}")
                
                response = re.sub(r'```json\s*', '', response)
                response = re.sub(r'```\s*', '', response)
                atoms = json.loads(response)
                if isinstance(atoms, list) and len(atoms) > 0:
                    return atoms
                elif attempt < 2:
                    time.sleep(1)
                    continue
            except ValueError as e:
                if "API调用失败" in str(e):
                    raise
                if attempt < 2:
                    time.sleep(1)
                    continue
            except:
                if attempt < 2:
                    time.sleep(1)
                    continue
        
        # 所有尝试都失败，抛出异常（去除fallback）
        raise RuntimeError("Failed to select atoms after all retries")
    
    def _phase_c_create_blueprint(self, slide: SlideStructure, page_intent: str, 
                                   page_atoms: List[str]) -> tuple:
        """
        Phase C: 创建block骨架（简化版，不含具体内容）
        
        Returns:
            (block_blueprint, manim_config, image_queries)
        """
        prompt = f"""你是PPT结构规划器。请规划block骨架。

内容：{slide.text[:300]}
意图：{page_intent}
类型：{', '.join(page_atoms)}
有公式：{'是' if slide.formula else '否'}
有代码：{'是' if slide.coq_code else '否'}

任务：规划需要哪些blocks（不写具体内容，只写类型和提示）

返回JSON：
{{
  "blocks": [
    {{"type": "text_line", "role": "motivation", "hint": "说明重要性"}},
    {{"type": "manim_relation", "manim_type": "function_plot", "desc": "画函数图"}}
  ],
  "manim_config": {{"type": "function_plot", "description": "..."}} or null,
  "images": ["search query"] or []
}}

只返回JSON，不要其他文字。"""

        import time
        for attempt in range(3):  # 增加到3次
            try:
                response = self.llm(prompt).strip()
                
                # 检查是否是CustomLLM错误消息
                if "请求大模型失败" in response or "请求大模型超时" in response:
                    print(f"        ⚠️ Phase C API失败: {response[:100]}，等待重试...")
                    if attempt < 2:
                        time.sleep(5)  # 增加延迟到5秒
                        continue
                    else:
                        raise ValueError(f"API调用失败: {response}")
                
                response = re.sub(r'```json\s*', '', response)
                response = re.sub(r'```\s*', '', response)
                response = re.sub(r'<[^>]+>', '', response)
                
                result = json.loads(response)
                blocks = result.get('blocks', [])
                manim_config = result.get('manim_config')
                images = result.get('images', [])
                
                if len(blocks) > 0:
                    # 转换为标准的block_blueprint格式
                    blueprint = []
                    for b in blocks:
                        blueprint.append({
                            "block_type": b.get('type', 'text_line'),
                            "semantic_role": b.get('role', 'explanation'),
                            "content_hint": b.get('hint', ''),
                            "estimated_duration": 3.0
                        })
                    return blueprint, manim_config, images
                elif attempt < 2:
                    time.sleep(1)
                    continue
            except ValueError as e:
                # API调用失败，直接抛出
                if "API调用失败" in str(e):
                    raise
                if attempt < 2:
                    print(f"        ⚠️ Phase C失败: {e}，重试...")
                    time.sleep(1)
                    continue
            except Exception as e:
                if attempt < 2:
                    print(f"        ⚠️ Phase C失败: {e}，重试...")
                    time.sleep(1)
                    continue
        
        # 所有尝试都失败，抛出异常（去除fallback）
        raise RuntimeError("Failed to create blueprint after all retries")
    
class BlockExecutor:
    """
    Executor阶段：专注语言质量
    
    输入：block blueprint
    输出：最终blocks（含具体文本、emphasis）
    """
    
    def __init__(self, llm):
        self.llm = llm
    
    def execute_plan(self, slide: SlideStructure, plan: Dict) -> List[SlideBlock]:
        """
        根据blueprint生成最终blocks
        
        Args:
            slide: 当前slide
            plan: Planner生成的执行计划
        
        Returns:
            SlideBlock列表
        """
        blocks = []
        block_idx = 0
        
        for blueprint in plan.get('block_blueprint', []):
            block_type = blueprint.get('block_type', 'text_line')
            
            if block_type in ['text_line', 'conceptual_statement']:
                # 生成文本block（含emphasis）
                block = self._generate_text_block(slide, blueprint, plan, block_idx)
                if block:
                    blocks.append(block)
                    block_idx += 1
            
            elif block_type == 'formula':
                # 生成公式block
                if slide.formula:
                    block = self._generate_formula_block(slide, blueprint, block_idx)
                    blocks.append(block)
                    block_idx += 1
            
            elif block_type == 'code':
                # 生成代码block
                if slide.coq_code:
                    block = self._generate_code_block(slide, blueprint, block_idx)
                    blocks.append(block)
                    block_idx += 1
            
            elif block_type == 'manim_relation':
                # 生成Manim关系图block
                block = self._generate_manim_block(slide, plan, blueprint, block_idx)
                blocks.append(block)
                block_idx += 1
        
        return blocks
    
    def _generate_text_block(self, slide: SlideStructure, blueprint: Dict, 
                            plan: Dict, block_idx: int) -> Optional[SlideBlock]:
        """
        生成文本block（带emphasis，带重试）
        
        调用LLM改写为书面化文本，并标注关键词
        """
        prompt = f"""请将以下内容改写为书面化的概念陈述。

原始文本: {slide.text[:300]}
当前block作用: {blueprint.get('content_hint', '')}
语义角色: {blueprint.get('semantic_role', 'explanation')}
页面意图: {plan.get('page_intent', '')}

要求：
1. 必须是完整、可朗读的陈述句
2. 禁止口语化（"我们"、"接下来"、"大家"等）
3. **content字段必须是纯文本，不要包含任何markdown符号（如**、*、_等）**
4. 标注关键概念词（用于加粗，最多5个），放在emphasis.bold中
5. 标注核心术语（用于标红，0-2个），放在emphasis.color中

返回JSON格式：
{{
  "content": "改写后的书面化纯文本（不含任何markdown符号）",
  "emphasis": {{
    "bold": ["关键词1", "关键词2"],
    "color": {{
      "核心术语": "red"
    }}
  }}
}}

示例：
{{
  "content": "尽管开发者追求代码的完美，但传统的单元测试由于覆盖率局限，难以穷尽所有潜在缺陷。",
  "emphasis": {{
    "bold": ["单元测试", "覆盖率局限", "穷尽"],
    "color": {{"Coq": "red"}}
  }}
}}

只返回JSON，不要其他文字。"""
        
        # 重试机制（最多3次）
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.llm(prompt)
                
                # 调试：打印原始响应（前200字符）
                print(f"        🔍 LLM原始响应: {response[:200] if response else '(空)'}")
                
                # 检查响应是否为空
                if not response or len(response.strip()) < 10:
                    if attempt < max_retries - 1:
                        print(f"        ⚠️ LLM响应为空，重试 {attempt + 1}/{max_retries}")
                        time.sleep(2)  # 增加延迟
                        continue
                    else:
                        raise ValueError("LLM响应为空")
                
                # 检查是否是CustomLLM返回的错误消息
                if "请求大模型失败" in response or "请求大模型超时" in response:
                    if attempt < max_retries - 1:
                        print(f"        ⚠️ API调用失败: {response[:100]}，重试 {attempt + 1}/{max_retries}")
                        time.sleep(3)  # API失败时延迟更长
                        continue
                    else:
                        raise ValueError(f"API调用失败: {response}")
                
                result = self._parse_json(response)
                
                # 验证结果
                if not result or 'content' not in result:
                    if attempt < max_retries - 1:
                        print(f"        ⚠️ LLM响应解析失败，重试 {attempt + 1}/{max_retries}")
                        time.sleep(1)
                        continue
                    else:
                        raise ValueError("JSON解析失败或缺少content字段")
                
                content = result.get('content', '').strip()
                if not content:
                    if attempt < max_retries - 1:
                        print(f"        ⚠️ content为空，重试 {attempt + 1}/{max_retries}")
                        time.sleep(1)
                        continue
                    else:
                        raise ValueError("content字段为空")
                
                # 成功生成
                return SlideBlock(
                    block_id=f"slide_{slide.slide_id}_block_{block_idx}",
                    block_type=blueprint.get('block_type', 'text_line'),
                    content=content,
                    semantic_role=blueprint.get('semantic_role', 'explanation'),
                    position_hint="left",
                    emphasis=result.get('emphasis', {}),
                    estimated_duration=blueprint.get('estimated_duration', len(content) / 50.0),
                    subtitle_text=content
                )
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"        ⚠️ 尝试 {attempt + 1} 失败: {e}，重试...")
                    time.sleep(1)
                else:
                    print(f"        ❌ 生成文本block失败（所有重试都失败）: {e}")
                    raise RuntimeError(f"Failed to generate text block after {max_retries} attempts: {e}")
        
        # 理论上不会到这里
        raise RuntimeError("Unexpected: reached end of _generate_text_block without return")
    
    def _generate_formula_block(self, slide: SlideStructure, 
                               blueprint: Dict, block_idx: int) -> SlideBlock:
        """生成公式block"""
        return SlideBlock(
            block_id=f"slide_{slide.slide_id}_block_{block_idx}",
            block_type=BlockType.FORMULA.value,
            content=slide.formula,
            semantic_role=blueprint.get('semantic_role', SemanticRole.RELATION.value),
            position_hint="right",
            emphasis=None,
            estimated_duration=3.0,
            subtitle_text="公式展示"
        )
    
    def _generate_code_block(self, slide: SlideStructure, 
                            blueprint: Dict, block_idx: int) -> SlideBlock:
        """生成代码block"""
        code_lines = slide.coq_code.split('\n') if slide.coq_code else []
        duration = max(len(code_lines) * 0.5, 2.0)
        
        return SlideBlock(
            block_id=f"slide_{slide.slide_id}_block_{block_idx}",
            block_type=BlockType.CODE.value,
            content=slide.coq_code,
            semantic_role=blueprint.get('semantic_role', SemanticRole.EXAMPLE.value),
            position_hint="right",
            emphasis=None,
            estimated_duration=duration,
            subtitle_text="代码示例"
        )
    
    def _generate_manim_block(self, slide: SlideStructure, plan: Dict,
                             blueprint: Dict, block_idx: int) -> SlideBlock:
        """生成Manim关系图block（增强版：生成PPT显示文字）"""
        manim_config = plan.get('manim_relation_config', {})
        description = manim_config.get('description', '关系图')
        manim_type = manim_config.get('type', 'flowchart')
        
        # 生成简洁的PPT显示文字（用LLM提炼）
        ppt_text = self._generate_ppt_text_for_manim(description, manim_type)
        
        # 将PPT文字添加到manim_config中
        manim_config['ppt_text'] = ppt_text
        
        return SlideBlock(
            block_id=f"slide_{slide.slide_id}_block_{block_idx}",
            block_type=BlockType.MANIM_RELATION.value,
            content=manim_config,
            semantic_role=SemanticRole.RELATION.value,
            position_hint="right",
            emphasis=None,
            estimated_duration=5.0,
            subtitle_text=ppt_text  # 使用简洁的PPT文字
        )
    
    def _generate_ppt_text_for_manim(self, description: str, manim_type: str) -> str:
        """
        为Manim图表生成简洁的PPT显示文字
        
        将详细的绘图描述转换为观众可读的说明
        """
        type_map = {
            'function_plot': '函数关系图',
            'directed_graph': '逻辑关系图',
            'flowchart': '流程图'
        }
        
        prompt = f"""请将以下Manim绘图描述转换为简洁的PPT显示文字（1-2句话）。

绘图类型：{type_map.get(manim_type, '关系图')}
详细描述：{description}

要求：
1. 提炼核心信息，说明图表展示的是什么关系或对比
2. 使用观众能理解的语言，不要提及"节点"、"箭头"等技术细节
3. 如果涉及坐标轴，明确说明X轴和Y轴代表什么
4. 如果涉及对比，明确说明对比的双方和结论
5. 控制在50字以内
6. 不要有"下图展示"、"如图所示"等冗余表达

只输出转换后的文字，不要有其他内容。"""

        try:
            response = self.llm(prompt)
            
            # 检查是否是CustomLLM错误消息
            if "请求大模型失败" in response or "请求大模型超时" in response:
                print(f"        ⚠️ PPT文字生成API失败，使用默认描述")
                return f"{type_map.get(manim_type, '关系图')}: {description[:40]}..."
            
            ppt_text = response.strip()
            # 限制长度
            if len(ppt_text) > 80:
                ppt_text = ppt_text[:77] + "..."
            return ppt_text
        except Exception as e:
            print(f"        ⚠️ 生成PPT文字失败: {e}")
            # 回退：使用类型+简短描述（这里可以保留fallback，因为不是核心内容）
            return f"{type_map.get(manim_type, '关系图')}: {description[:40]}..."
    
    def _parse_json(self, response: str) -> Dict:
        """
        解析JSON响应（增强版，失败时抛出异常）
        
        Args:
            response: LLM的原始响应
        
        Returns:
            解析后的字典
        
        Raises:
            ValueError: 解析失败时
        """
        if not response:
            raise ValueError("响应为空")
        
        # 清理响应
        response = response.replace("<br>", "\n")
        response = re.sub(r'<[^>]+>', '', response)  # 移除HTML标签
        response = re.sub(r'```json\s*', '', response, flags=re.IGNORECASE)
        response = re.sub(r'```\s*', '', response)
        response = response.strip()
        
        if not response:
            raise ValueError("清理后响应为空")
        
        try:
            result = json.loads(response)
            if not isinstance(result, dict):
                raise ValueError(f"解析结果不是字典，而是 {type(result)}")
            return result
        except json.JSONDecodeError as e:
            # 调试：打印导致解析失败的原始内容
            print(f"        🔍 JSON解析失败，原始响应:\n{response[:500]}")
            
            # 尝试提取JSON（有时LLM会在JSON前后加文字）
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                try:
                    result = json.loads(json_match.group(0))
                    if isinstance(result, dict):
                        return result
                except:
                    pass
            raise ValueError(f"JSON解析失败: {str(e)[:100]}")


class ImageSearcher:
    """
    在线图片搜索（使用Unsplash API）
    
    配置：需要设置环境变量 UNSPLASH_API_KEY
    """
    
    def __init__(self):
        self.api_key = os.environ.get("UNSPLASH_API_KEY", "")
        self.enabled = bool(self.api_key)
        
        if not self.enabled:
            print("    ⚠️ UNSPLASH_API_KEY未设置，图片搜索功能禁用")
    
    def search(self, query: str) -> Optional[str]:
        """
        搜索图片并返回URL
        
        Args:
            query: 搜索关键词
        
        Returns:
            图片URL，失败返回None
        """
        if not self.enabled:
            return None
        
        try:
            url = f"https://api.unsplash.com/search/photos"
            params = {
                "query": query,
                "per_page": 1,
                "orientation": "landscape"
            }
            headers = {
                "Authorization": f"Client-ID {self.api_key}",
                "Accept-Version": "v1"
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    return data['results'][0]['urls']['regular']
            else:
                print(f"        ⚠️ Unsplash API error: {response.status_code}")
                
        except Exception as e:
            print(f"        ⚠️ 图片搜索失败: {e}")
        
        return None


# 便捷函数
def process_slides_with_agent(slides: List[SlideStructure]) -> List[SlideStructure]:
    """
    便捷函数：使用PageDirector Agent处理slides
    
    Args:
        slides: Stage 1输出的slide列表
    
    Returns:
        增强后的slide列表
    """
    agent = PageDirectorAgent()
    return agent.process_slides(slides)

