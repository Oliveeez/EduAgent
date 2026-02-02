# Stage 1.5: PageDirector Agent 完整设计

## 范式级重构版本

### 核心架构：Planner/Executor分离

```python
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
        from utils.llm import CustomLLM
        self.llm = CustomLLM()
        self.planner = PagePlanner(self.llm)     # 决策层
        self.executor = BlockExecutor(self.llm)  # 执行层
        self.image_searcher = ImageSearcher()
    
    def process_slides(self, slides: List[SlideStructure]) -> List[SlideStructure]:
        """
        处理所有slides（两阶段流程）
        """
        enhanced_slides = []
        
        for slide in slides:
            # Phase 1: Planner - 生成执行计划
            plan = self.planner.create_plan(slide)
            
            # Phase 2: Executor - 执行计划生成具体blocks
            blocks = self.executor.execute_plan(slide, plan)
            
            # Phase 3: 搜索图片（如果需要）
            if plan.get('image_search_queries'):
                for query in plan['image_search_queries']:
                    url = self.image_searcher.search(query)
                    if url:
                        # 添加image block（二等公民）
                        blocks.append(self._create_image_block(url, query))
            
            # Phase 4: 验证计划（Schema Lock）
            self._validate_plan(plan, blocks)
            
            # Phase 5: 更新slide
            slide.page_intent = plan['page_intent']
            slide.page_atoms = plan['page_atoms']
            slide.blocks = blocks
            slide.manim_relation_config = plan.get('manim_relation_config')
            slide.image_search_queries = plan.get('image_search_queries', [])
            slide.needs_split = plan.get('needs_split', False)
            
            enhanced_slides.append(slide)
        
        return enhanced_slides
    
    def _validate_plan(self, plan: Dict, blocks: List[Dict]):
        """
        结构不可逃逸（Schema Lock）
        
        任何不合格计划，直接reject重采样
        """
        # 验证page_intent
        assert plan["page_intent"] in [e.value for e in PageIntent], \
            f"Invalid page_intent: {plan['page_intent']}"
        
        # 验证至少2个blocks
        assert len(blocks) >= 2, \
            f"Page must have at least 2 blocks, got {len(blocks)}"
        
        # 验证每个block的必需字段
        for block in blocks:
            assert "block_type" in block
            assert "semantic_role" in block
            assert "estimated_duration" in block
            
            # 验证text block的emphasis
            if block["block_type"] in ["text_line", "conceptual_statement"]:
                if "emphasis" in block:
                    bold_words = block["emphasis"].get("bold", [])
                    assert len(bold_words) <= 5, \
                        f"Too many bold keywords: {len(bold_words)} (max 5)"
        
        # 验证Image不能单独构成页面（Image是二等公民）
        image_blocks = [b for b in blocks if b["block_type"] == "image"]
        if len(image_blocks) == len(blocks):
            raise ValueError("Image blocks cannot be the only content on a page")
    
    def _create_image_block(self, url: str, query: str) -> Dict:
        """创建image block（二等公民）"""
        return {
            "block_type": "image",
            "content": url,
            "position_hint": "right",
            "semantic_role": "example",  # Image永远服务于Concept/Relation
            "emphasis": {},
            "estimated_duration": 2.0,
            "subtitle_text": query
        }
```

---

## PagePlanner：决策层（专注结构正确）

```python
class PagePlanner:
    """
    Planner阶段：专注结构正确
    
    输入：slide原始内容
    输出：page_intent + page_atoms + block blueprint
    """
    
    def __init__(self, llm):
        self.llm = llm
    
    def create_plan(self, slide: SlideStructure) -> Dict:
        """
        生成执行计划（使用范式级Prompt）
        
        这是"规划合同"（Planning Contract）
        """
        prompt = f"""你是一个"教学型PPT页面规划器（Page Director）"。

你的任务不是写内容，而是：
1. 理解该页在教学叙事中的"意图"
2. 选择合适的页面原子（PageAtoms）
3. 生成可执行的 Block 级规划结果

--------------------
【可用页面意图 PageIntent】
- introduce_concept：引入一个新概念
- motivate_importance：说明为什么重要
- explain_mechanism：解释原理或机制
- show_relation：展示多个概念/思想之间的关系
- walk_through_proof：逐步讲解公式或代码

--------------------
【可用页面原子 PageAtom】
- Conceptual Statement：书面化概念陈述
- Formula Focus：公式展示
- Code Walkthrough：代码讲解
- Relational Visualization：关系图/函数图（仅表达关系/演化/依赖）
- Concept + Visual：概念+图片（仅作为语境强化）

--------------------
【Block 生成原则（强约束）】

1. 每个 Block 是一个"认知 + 时序"单位
2. 每个 Block 必须能：
   - 独立配音
   - 独立生成字幕
   - 独立控制出现时机
3. 文本 Block：
   - 必须是书面、完整、可朗读的陈述句
   - 禁止口语化（"我们"、"接下来"等）
4. Conceptual Statement：
   - 必须标注 emphasis（bold / color）
   - 关键词数量 ≤ 5
5. Relational Visualization：
   - 只能表达"关系 / 演化 / 依赖"
   - 不得包含无关装饰
6. Image Block：
   - 只能作为"语境强化"，不能承载核心概念
   - Image不能单独构成页面（二等公民）

--------------------
【当前内容分析】

标题: {slide.title}
章节: {slide.section_title}
文本: {slide.text[:200]}...
公式: {'有' if slide.formula else '无'}
代码: {'有' if slide.coq_code else '无'}

--------------------
【你的输出必须是一个"执行计划 JSON"】【严格遵守】

{{
  "page_intent": "...",              # 从PageIntent中选择
  "page_atoms": [...],               # 2-3个PageAtom
  "reasoning": "为什么这样设计",
  
  "block_blueprint": [
    {{
      "block_type": "...",
      "semantic_role": "...",        # definition | motivation | example | relation | transition
      "content_hint": "这个block应该说什么（不是完整文本）",
      "estimated_duration": 2.5      # 认知时长估计（秒）
    }}
  ],
  
  "manim_relation_config": {{
    "type": "function_plot | directed_graph | flowchart",
    "description": "要表达什么关系"
  }} or null,
  
  "image_search_queries": ["query1", "query2"] or [],
  "needs_split": false
}}

--------------------
【失败回退规则】

- 如果关系无法清晰表达 → 放弃 Relational Visualization
- 如果关键词不明确 → 不生成 emphasis
- 如果信息过载 → 标记 needs_split = true

请分析并输出执行计划JSON："""
        
        response = self.llm(prompt)
        
        # 解析LLM响应
        plan = self._parse_llm_response(response)
        
        return plan
    
    def _parse_llm_response(self, response: str) -> Dict:
        """解析LLM响应为结构化计划"""
        import json
        import re
        
        # 清理响应
        response = response.replace("<br>", "\n")
        response = re.sub(r'```json\s*', '', response, flags=re.IGNORECASE)
        response = re.sub(r'```\s*', '', response)
        response = response.strip()
        
        try:
            plan = json.loads(response)
            return plan
        except json.JSONDecodeError as e:
            print(f"⚠️ LLM响应解析失败: {e}")
            # 返回默认计划（Fallback）
            return {
                "page_intent": "introduce_concept",
                "page_atoms": ["Conceptual Statement"],
                "block_blueprint": [],
                "manim_relation_config": None,
                "image_search_queries": [],
                "needs_split": False
            }
```

---

## BlockExecutor：执行层（专注语言质量）

```python
class BlockExecutor:
    """
    Executor阶段：专注语言质量
    
    输入：block blueprint
    输出：最终blocks（含具体文本、emphasis）
    """
    
    def __init__(self, llm):
        self.llm = llm
    
    def execute_plan(self, slide: SlideStructure, plan: Dict) -> List[Dict]:
        """
        根据blueprint生成最终blocks
        """
        blocks = []
        
        for blueprint in plan.get('block_blueprint', []):
            block_type = blueprint['block_type']
            
            if block_type in ['text_line', 'conceptual_statement']:
                # 生成文本block（含emphasis）
                block = self._generate_text_block(slide, blueprint, plan)
                blocks.append(block)
            
            elif block_type == 'formula':
                block = self._generate_formula_block(slide, blueprint)
                blocks.append(block)
            
            elif block_type == 'code':
                block = self._generate_code_block(slide, blueprint)
                blocks.append(block)
            
            elif block_type == 'manim_relation':
                block = self._generate_manim_block(plan, blueprint)
                blocks.append(block)
        
        return blocks
    
    def _generate_text_block(self, slide: SlideStructure, 
                            blueprint: Dict, plan: Dict) -> Dict:
        """
        生成文本block（带emphasis）
        
        调用LLM改写为书面化文本，并标注关键词
        """
        prompt = f"""请将以下内容改写为书面化的概念陈述。

原始文本: {slide.text[:200]}
当前block作用: {blueprint.get('content_hint', '')}
语义角色: {blueprint.get('semantic_role', 'explanation')}
页面意图: {plan.get('page_intent', '')}

要求：
1. 必须是完整、可朗读的陈述句
2. 禁止口语化（"我们"、"接下来"等）
3. 标注关键概念词（用于加粗，最多5个）
4. 标注核心术语（用于标红，0-2个）

返回JSON格式：
{{
  "content": "改写后的书面化文本",
  "emphasis": {{
    "bold": ["关键词1", "关键词2"],
    "color": {{
      "核心术语": "red"
    }}
  }}
}}
"""
        
        response = self.llm(prompt)
        result = self._parse_json(response)
        
        return {
            "block_id": f"slide_{slide.slide_id}_block_{len(blocks)}",
            "block_type": blueprint['block_type'],
            "semantic_role": blueprint['semantic_role'],
            "content": result.get('content', slide.text[:100]),
            "position_hint": "left",
            "emphasis": result.get('emphasis', {}),
            "estimated_duration": blueprint.get('estimated_duration', 3.0),
            "subtitle_text": result.get('content', slide.text[:100])
        }
    
    def _generate_formula_block(self, slide: SlideStructure, blueprint: Dict) -> Dict:
        """生成公式block"""
        return {
            "block_type": "formula",
            "semantic_role": blueprint['semantic_role'],
            "content": slide.formula,
            "position_hint": "right",
            "emphasis": {},
            "estimated_duration": 3.0,
            "subtitle_text": f"公式展示"
        }
    
    def _generate_code_block(self, slide: SlideStructure, blueprint: Dict) -> Dict:
        """生成代码block"""
        return {
            "block_type": "code",
            "semantic_role": blueprint['semantic_role'],
            "content": slide.coq_code,
            "position_hint": "right",
            "emphasis": {},
            "estimated_duration": len(slide.coq_code.split('\n')) * 0.5,
            "subtitle_text": "代码示例"
        }
    
    def _generate_manim_block(self, plan: Dict, blueprint: Dict) -> Dict:
        """生成Manim关系图block"""
        return {
            "block_type": "manim_relation",
            "semantic_role": "relation",
            "content": plan.get('manim_relation_config', {}),
            "position_hint": "right",
            "emphasis": {},
            "estimated_duration": 5.0,
            "subtitle_text": plan.get('manim_relation_config', {}).get('description', '关系图')
        }
    
    def _parse_json(self, response: str) -> Dict:
        """解析JSON响应"""
        import json
        import re
        
        response = response.replace("<br>", "\n")
        response = re.sub(r'```json\s*', '', response, flags=re.IGNORECASE)
        response = re.sub(r'```\s*', '', response)
        
        try:
            return json.loads(response.strip())
        except:
            return {}
```

---

## PageIntent驱动的决策示例

### 示例1：孙子算经页面

**Input**:
- 标题：从《孙子算经》说起
- 文本：引出'鸡兔同笼'问题，建立数学直觉与形式化验证之间的联系...

**Planner输出**:
```json
{
  "page_intent": "motivate_importance",
  "page_atoms": ["Conceptual Statement", "Formula Focus", "Concept + Visual"],
  "block_blueprint": [
    {
      "block_type": "text_line",
      "semantic_role": "definition",
      "content_hint": "定义鸡兔同笼问题",
      "estimated_duration": 3.0
    },
    {
      "block_type": "text_line",
      "semantic_role": "motivation",
      "content_hint": "为什么重要：形式化验证的典型案例",
      "estimated_duration": 3.5
    },
    {
      "block_type": "formula",
      "semantic_role": "relation",
      "content_hint": "方程组",
      "estimated_duration": 3.0
    }
  ],
  "image_search_queries": ["孙子算经 古籍"],
  "needs_split": false
}
```

**Executor输出**:
```json
{
  "blocks": [
    {
      "block_type": "text_line",
      "semantic_role": "definition",
      "content": "鸡兔同笼问题源自《孙子算经》，描述了已知头数和脚数，求解鸡兔各有多少只的数学问题。",
      "emphasis": {
        "bold": ["鸡兔同笼", "孙子算经", "头数", "脚数"],
        "color": {
          "鸡兔同笼": "red"
        }
      },
      "estimated_duration": 3.0
    },
    {
      "block_type": "text_line",
      "semantic_role": "motivation",
      "content": "该问题是形式化验证的典型案例，展示了从自然语言描述到数学模型的转换过程。",
      "emphasis": {
        "bold": ["形式化验证", "数学模型", "转换过程"],
        "color": {}
      },
      "estimated_duration": 3.5
    },
    {
      "block_type": "formula",
      "semantic_role": "relation",
      "content": "x + y = 35\n2x + 4y = 94",
      "estimated_duration": 3.0
    },
    {
      "block_type": "image",
      "semantic_role": "example",
      "content": "https://example.com/sunzi.jpg",
      "estimated_duration": 2.0
    }
  ]
}
```

---

## 关键设计决策

### 1. 为什么要Planner/Executor分离？

**原因**：
- **Planner**：专注"结构正确性"，不需要写出完美文字
- **Executor**：专注"语言打磨"，不需要做决策

**好处**：
- Planner的prompt可以更短、更聚焦
- Executor可以反复调用（如果文本质量不满意）
- 两个prompt独立调优，不会互相干扰

### 2. 为什么要Schema Lock？

**原因**：
- LLM输出格式不稳定
- 后续Stage依赖严格的数据结构

**实现**：
- `_validate_plan`函数强制约束
- 不合格直接抛异常，可触发重试或Fallback

### 3. 为什么Image是二等公民？

**原因**：
- Image只能"强化语境"，不能"承载核心概念"
- 如果一页只有图片，教学价值低

**约束**：
- 在`_validate_plan`中检测
- 在Planner的prompt中明确说明

### 4. 为什么要estimated_duration在Stage 1.5？

**原因**：
- Stage 1.5估算的是"认知时长"（学习者需要多久理解）
- Stage 6测量的是"物理时长"（TTS实际播放时长）
- 两者可能不同，但都有意义

**用途**：
- estimated_duration用于判断是否needs_split
- duration用于视频合成的精确时序控制



