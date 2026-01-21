"""
知识图谱生成工具
基于LaTeX解析结果，生成层级知识图谱
"""

import json
import logging
from typing import Dict, List, Optional
from pathlib import Path
import networkx as nx
from datetime import datetime

logger = logging.getLogger(__name__)


class KnowledgeGraph:
    """知识图谱生成器"""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.nodes = []
        self.edges = []
        
    def build_from_latex(self, latex_data: Dict) -> Dict:
        """
        从LaTeX解析数据构建知识图谱
        
        Args:
            latex_data: LaTeX解析器返回的数据
            
        Returns:
            知识图谱数据
        """
        logger.info("🔨 开始构建知识图谱...")
        
        # 添加根节点（文档）
        doc_title = latex_data.get('document_info', {}).get('title', '未命名文档')
        root_id = "doc_root"
        self._add_node(root_id, doc_title, 'document', 0)
        
        # 构建层级结构
        self._build_hierarchy(latex_data['chapters'], root_id)
        
        # 添加方程关联
        self._link_equations(latex_data.get('equations', []))
        
        # 添加图表关联
        self._link_figures(latex_data.get('figures', []))
        
        # 生成统计信息
        stats = self._generate_statistics()
        
        result = {
            'graph': {
                'nodes': self.nodes,
                'edges': self.edges
            },
            'statistics': stats,
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'source_document': doc_title,
                'total_nodes': len(self.nodes),
                'total_edges': len(self.edges)
            }
        }
        
        logger.info(f"✅ 知识图谱构建完成: {len(self.nodes)}个节点, {len(self.edges)}条边")
        return result
    
    def _add_node(self, node_id: str, label: str, node_type: str, level: int, **kwargs):
        """添加节点"""
        node = {
            'id': node_id,
            'label': label,
            'type': node_type,
            'level': level,
            **kwargs
        }
        self.nodes.append(node)
        self.graph.add_node(node_id, **node)
    
    def _add_edge(self, source: str, target: str, relation: str = 'contains'):
        """添加边"""
        edge = {
            'source': source,
            'target': target,
            'relation': relation
        }
        self.edges.append(edge)
        self.graph.add_edge(source, target, relation=relation)
    
    def _build_hierarchy(self, chapters: List[Dict], parent_id: str, parent_level: int = 0):
        """
        递归构建章节层级
        
        层级结构：
        - Level 0: Document (root)
        - Level 1: Chapter
        - Level 2: Section
        - Level 3: Subsection
        """
        current_parents = {parent_level: parent_id}
        
        for idx, chapter in enumerate(chapters):
            level = chapter['level']
            title = chapter['title']
            node_id = f"{chapter['type']}_{idx}"
            
            # 确定父节点
            # 如果当前层级高于之前的层级，使用上一个合适的父节点
            parent = current_parents.get(level - 1, parent_id)
            
            # 添加节点
            self._add_node(
                node_id,
                title,
                chapter['type'],
                level,
                content=chapter.get('content', ''),
                content_length=len(chapter.get('content', ''))
            )
            
            # 添加边
            self._add_edge(parent, node_id, 'contains')
            
            # 更新父节点映射
            current_parents[level] = node_id
            
            # 清理更深层级的父节点映射
            keys_to_remove = [k for k in current_parents.keys() if k > level]
            for k in keys_to_remove:
                del current_parents[k]
    
    def _link_equations(self, equations: List[Dict]):
        """关联数学公式到相关章节"""
        if not equations:
            return
        
        logger.info(f"🔗 关联 {len(equations)} 个数学公式...")
        
        # 简化处理：为公式创建独立的节点组
        eq_group_id = "equations_group"
        self._add_node(eq_group_id, "数学公式", "equation_group", 1)
        self._add_edge("doc_root", eq_group_id, "contains")
        
        for idx, eq in enumerate(equations):
            eq_id = f"equation_{idx}"
            eq_label = f"公式 {idx + 1}"
            
            self._add_node(
                eq_id,
                eq_label,
                eq['type'],
                2,
                latex=eq['latex']
            )
            self._add_edge(eq_group_id, eq_id, "contains")
    
    def _link_figures(self, figures: List[Dict]):
        """关联图表到相关章节"""
        if not figures:
            return
        
        logger.info(f"🔗 关联 {len(figures)} 个图表...")
        
        # 简化处理：为图表创建独立的节点组
        fig_group_id = "figures_group"
        self._add_node(fig_group_id, "图表", "figure_group", 1)
        self._add_edge("doc_root", fig_group_id, "contains")
        
        for idx, fig in enumerate(figures):
            fig_id = f"figure_{idx}"
            fig_label = fig.get('caption', f"图表 {idx + 1}")
            
            self._add_node(
                fig_id,
                fig_label,
                fig['type'],
                2,
                caption=fig.get('caption'),
                image_path=fig.get('image_path')
            )
            self._add_edge(fig_group_id, fig_id, "contains")
    
    def _generate_statistics(self) -> Dict:
        """生成图谱统计信息"""
        stats = {
            'total_nodes': len(self.nodes),
            'total_edges': len(self.edges),
            'nodes_by_type': {},
            'nodes_by_level': {},
            'max_depth': 0
        }
        
        # 按类型统计
        for node in self.nodes:
            node_type = node['type']
            stats['nodes_by_type'][node_type] = stats['nodes_by_type'].get(node_type, 0) + 1
        
        # 按层级统计
        for node in self.nodes:
            level = node['level']
            stats['nodes_by_level'][level] = stats['nodes_by_level'].get(level, 0) + 1
            stats['max_depth'] = max(stats['max_depth'], level)
        
        return stats
    
    def save(self, output_path: str):
        """保存知识图谱为JSON"""
        graph_data = {
            'nodes': self.nodes,
            'edges': self.edges
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 知识图谱已保存: {output_path}")
    
    def to_visualization_data(self) -> Dict:
        """
        转换为可视化数据格式（用于前端渲染）
        
        Returns:
            适合D3.js或ECharts的数据格式
        """
        # 为节点添加坐标（使用力导向布局的初始位置）
        try:
            pos = nx.spring_layout(self.graph, k=2, iterations=50)
        except:
            pos = {}
        
        vis_nodes = []
        for node in self.nodes:
            node_id = node['id']
            node_copy = node.copy()
            
            # 添加位置信息
            if node_id in pos:
                node_copy['x'] = float(pos[node_id][0] * 500)
                node_copy['y'] = float(pos[node_id][1] * 500)
            
            # 根据层级设置节点大小
            node_copy['size'] = max(10, 30 - node['level'] * 5)
            
            # 根据类型设置颜色
            type_colors = {
                'document': '#1890ff',
                'chapter': '#52c41a',
                'section': '#faad14',
                'subsection': '#722ed1',
                'subsubsection': '#eb2f96',
                'equation': '#13c2c2',
                'figure': '#fa8c16'
            }
            node_copy['color'] = type_colors.get(node['type'], '#d9d9d9')
            
            vis_nodes.append(node_copy)
        
        return {
            'nodes': vis_nodes,
            'edges': self.edges
        }


def extract_knowledge_points(chapters: List[Dict], llm_client=None) -> List[Dict]:
    """
    使用LLM提取知识点（可选的高级功能）
    
    Args:
        chapters: 章节列表
        llm_client: LLM客户端实例
        
    Returns:
        知识点列表
    """
    if not llm_client:
        # 如果没有LLM，使用简单的基于规则的提取
        knowledge_points = []
        for chapter in chapters:
            # 简单地将subsection作为知识点
            if chapter['level'] >= 3:
                knowledge_points.append({
                    'title': chapter['title'],
                    'source_chapter': chapter.get('title'),
                    'content': chapter.get('content', '')
                })
        return knowledge_points
    
    # TODO: 使用LLM进行智能提取
    # prompt = f"从以下内容中提取主要知识点：\n{chapter_content}"
    # response = llm_client(prompt)
    
    return []