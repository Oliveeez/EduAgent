"""
Step 1: 知识图谱提取模块
从LaTeX电子书提取知识图谱
"""

import json
import logging
from typing import Dict, List
from datetime import datetime

from utils.latex_kg_extractor import LatexKGExtractor

logger = logging.getLogger(__name__)


class KnowledgeExtractor:
    """知识提取器 - Step 1"""
    
    def __init__(self):
        self.kg_extractor = LatexKGExtractor()
        
    async def extract_from_latex(self, latex_file_path: str) -> Dict:
        """
        从LaTeX文件提取知识图谱
        
        Args:
            latex_file_path: LaTeX文件路径
            
        Returns:
            提取结果，包含知识图谱和元数据
        """
        logger.info("=" * 60)
        logger.info("🚀 Step 1: 开始提取知识图谱")
        logger.info("=" * 60)
        
        try:
            # 1. 解析LaTeX文件并提取知识图谱
            logger.info("📖 Step 1.1: 解析LaTeX文档并抽取节点...")
            kg_data = self.kg_extractor.extract_from_file(latex_file_path)
            
            # 2. 生成可视化数据
            logger.info("🎨 Step 1.2: 生成可视化数据...")
            vis_data = self.kg_extractor.to_visualization_data(kg_data)
            
            # 3. 组装结果
            result = {
                'success': True,
                'latex_data': kg_data.get('latex_data', {}),
                'knowledge_graph': kg_data['graph'],
                'visualization': vis_data,
                'statistics': kg_data['statistics'],
                'metadata': {
                    'source_file': latex_file_path,
                    'extracted_at': datetime.now().isoformat(),
                    'total_nodes': kg_data['metadata']['total_nodes'],
                    'total_edges': kg_data['metadata']['total_edges']
                }
            }
            
            logger.info("=" * 60)
            logger.info("✅ Step 1: 知识图谱提取完成")
            logger.info(f"   📊 节点数: {result['metadata']['total_nodes']}")
            logger.info(f"   🔗 边数: {result['metadata']['total_edges']}")
            total_chapters = (
                kg_data.get('latex_data', {}).get('statistics', {}).get('total_chapters', 0)
            )
            logger.info(f"   📚 章节数: {total_chapters}")
            logger.info("=" * 60)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 知识图谱提取失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    def save_knowledge_graph(self, kg_data: Dict, output_path: str):
        """保存知识图谱到文件"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(kg_data, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 知识图谱已保存: {output_path}")
        except Exception as e:
            logger.error(f"❌ 保存失败: {e}")

    def save_visualization_graph(self, kg_data: Dict, output_path: str):
        """保存可视化JSON到文件（nodes/links + 虚拟根）"""
        try:
            viz_json = self.kg_extractor.build_viz_json(kg_data)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(viz_json, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 可视化JSON已保存: {output_path}")
        except Exception as e:
            logger.error(f"❌ 可视化JSON保存失败: {e}")
    
    def get_knowledge_points_summary(self, kg_data: Dict) -> List[Dict]:
        """
        从知识图谱中提取知识点摘要（用于用户选择）
        
        Returns:
            知识点列表，每个元素包含id, title, level等
        """
        knowledge_points = []
        
        nodes = kg_data.get('knowledge_graph', {}).get('nodes', [])
        
        for node in nodes:
            # 只提取章节级别的节点作为知识点
            if node['type'] in ['chapter', 'section', 'subsection']:
                knowledge_points.append({
                    'id': node['id'],
                    'title': node.get('label') or node.get('title', ''),
                    'level': node['level'],
                    'type': node['type'],
                    'content_preview': node.get('content', '')[:100] + '...' if node.get('content') else ''
                })
        
        return knowledge_points
