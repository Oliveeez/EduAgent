"""
FastAPI主应用 - 课堂视频生成Agent
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# 导入配置
from config.config import (
    API_CONFIG, DATA_DIR, LATEX_UPLOADS_DIR, 
    KNOWLEDGE_GRAPHS_DIR, OUTLINES_DIR, PPT_OUTPUT_DIR
)

# 导入模块
from modules.knowledge_extractor import KnowledgeExtractor
from modules.outline_generator import OutlineGenerator
from modules.ppt_creator import PPTCreator
from modules.script_editor import ScriptEditor
from modules.videopipeline.main_pipeline import VideoPipeline

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

# 创建FastAPI应用
app = FastAPI(
    title="Classroom Video Agent API",
    description="课堂视频生成Agent - 智能PPT生成系统",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=API_CONFIG['cors_origins'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory=str(DATA_DIR)), name="static")

# ==================== Pydantic模型 ====================

class KnowledgePoint(BaseModel):
    """知识点模型"""
    id: str
    title: str
    detail_level: str = "标准"  # 精讲/粗讲/标准


class OutlineRequest(BaseModel):
    """大纲生成请求"""
    kg_id: str  # 知识图谱ID
    knowledge_points: List[KnowledgePoint]
    style: str = "简约"  # 简约/学术/商务
    other_requirements: Optional[str] = None


class ModificationRequest(BaseModel):
    """PPT修改请求"""
    ppt_path: str
    description: str  # 自然语言描述或结构化指令


class ScriptEditRequest(BaseModel):
    """讲稿编辑请求"""
    outline_id: str  # 大纲ID
    user_message: str  # 用户消息
    context: Optional[Dict] = None  # 额外上下文


class ScriptSaveRequest(BaseModel):
    """讲稿保存请求"""
    outline_id: str  # 大纲ID
    updated_script: Dict  # 更新后的讲稿


class VideoGenerateRequest(BaseModel):
    """视频生成请求"""
    outline_id: str  # 大纲ID
    use_llm: bool = True  # 是否使用LLM优化


# ==================== 全局状态 ====================

# 初始化模块（LLM客户端由用户在外部提供）
knowledge_extractor = KnowledgeExtractor()
outline_generator = None  # 需要在启动时初始化
ppt_creator = None  # 需要在启动时初始化

# 存储会话数据
sessions = {}

# 存储讲稿编辑会话
script_edit_sessions = {}


# ==================== 启动事件 ====================

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    global outline_generator, ppt_creator
    
    logger.info("=" * 60)
    logger.info("🚀 启动 Classroom Video Agent API")
    logger.info("=" * 60)
    
    try:
        # 尝试导入LLM客户端（由用户提供）
        from utils.llm import CustomLLM
        llm_client = CustomLLM()
        logger.info("✅ LLM客户端加载成功")
    except ImportError:
        logger.warning("⚠️  未找到LLM客户端，将使用降级模式")
        llm_client = None
    
    # 初始化模块
    outline_generator = OutlineGenerator(llm_client)
    ppt_creator = PPTCreator(llm_client=llm_client)
    
    logger.info("✅ 所有模块初始化完成")
    logger.info(f"📂 数据目录: {DATA_DIR}")
    logger.info("=" * 60)


# ==================== API端点 ====================

@app.get("/")
async def root():
    """根端点"""
    return {
        "message": "Classroom Video Agent API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


# ==================== Step 1: 知识图谱提取 ====================

@app.post("/api/step1/upload-latex")
async def upload_latex(file: UploadFile = File(...)):
    """
    上传LaTeX文件
    
    Returns:
        file_id: 文件ID，用于后续提取知识图谱
    """
    try:
        # 保存文件
        file_id = f"latex_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        file_path = LATEX_UPLOADS_DIR / f"{file_id}.tex"
        
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"✅ LaTeX文件已上传: {file_path}")
        
        return {
            "success": True,
            "file_id": file_id,
            "file_path": str(file_path),
            "filename": file.filename
        }
        
    except Exception as e:
        logger.error(f"❌ 上传失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/step1/extract-kg")
async def extract_knowledge_graph(file_id: str, background_tasks: BackgroundTasks):
    """
    提取知识图谱（Step 1）
    
    Args:
        file_id: LaTeX文件ID
        
    Returns:
        知识图谱数据
    """
    try:
        # 查找文件
        file_path = LATEX_UPLOADS_DIR / f"{file_id}.tex"
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="LaTeX文件不存在")
        
        # 提取知识图谱
        logger.info(f"开始提取知识图谱: {file_id}")
        result = await knowledge_extractor.extract_from_latex(str(file_path))
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error', '提取失败'))
        
        # 保存知识图谱
        kg_id = f"kg_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        kg_path = KNOWLEDGE_GRAPHS_DIR / f"{kg_id}.json"
        knowledge_extractor.save_knowledge_graph(result, str(kg_path))

        # 保存可视化JSON（前端直接使用）
        viz_path = KNOWLEDGE_GRAPHS_DIR / f"{kg_id}.viz.json"
        knowledge_extractor.save_visualization_graph(result, str(viz_path))
        
        # 提取知识点摘要（用于前端选择）
        knowledge_points = knowledge_extractor.get_knowledge_points_summary(result)
        
        # 存储会话数据
        sessions[kg_id] = {
            'file_id': file_id,
            'kg_path': str(kg_path),
            'created_at': datetime.now().isoformat()
        }
        
        return {
            "success": True,
            "kg_id": kg_id,
            "knowledge_points": knowledge_points,
            "statistics": result['statistics'],
            "visualization": result['visualization'],
            "viz_file": str(viz_path)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 提取知识图谱失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/step1/kg/{kg_id}")
async def get_knowledge_graph(kg_id: str):
    """获取知识图谱数据"""
    try:
        kg_path = KNOWLEDGE_GRAPHS_DIR / f"{kg_id}.json"
        if not kg_path.exists():
            raise HTTPException(status_code=404, detail="知识图谱不存在")
        
        import json
        with open(kg_path, 'r', encoding='utf-8') as f:
            kg_data = json.load(f)
        
        return kg_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取知识图谱失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/step1/kg/{kg_id}/viz")
async def get_knowledge_graph_viz(kg_id: str):
    """获取可视化JSON（nodes/links + 虚拟根）"""
    try:
        viz_path = KNOWLEDGE_GRAPHS_DIR / f"{kg_id}.viz.json"
        if not viz_path.exists():
            raise HTTPException(status_code=404, detail="可视化文件不存在")

        import json
        with open(viz_path, 'r', encoding='utf-8') as f:
            viz_data = json.load(f)

        return viz_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取可视化JSON失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/step1/kg-viz-list")
async def list_knowledge_graph_viz_files():
    """列出可用的可视化图谱文件（按时间倒序）"""
    try:
        items = []
        for path in sorted(
            KNOWLEDGE_GRAPHS_DIR.glob("kg_*.viz.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ):
            kg_id = path.stem.replace(".viz", "")
            items.append(
                {
                    "kg_id": kg_id,
                    "filename": path.name,
                }
            )
        return {"items": items}
    except Exception as e:
        logger.error(f"❌ 获取可视化文件列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _resolve_viz_path(kg_id: Optional[str]) -> Path:
    if kg_id:
        viz_path = KNOWLEDGE_GRAPHS_DIR / f"{kg_id}.viz.json"
        return viz_path

    candidates = sorted(
        KNOWLEDGE_GRAPHS_DIR.glob("kg_*.viz.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return None
    return candidates[0]


def _load_viz_data(kg_id: Optional[str]) -> Dict:
    viz_path = _resolve_viz_path(kg_id)
    if not viz_path or not viz_path.exists():
        raise HTTPException(status_code=404, detail="可视化文件不存在")
    import json
    with open(viz_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _index_nodes(nodes: List[Dict]) -> Dict[str, Dict]:
    return {n.get("id"): n for n in nodes if n.get("id")}


@app.get("/api/stats")
async def get_graph_stats(kg_id: Optional[str] = None):
    """可视化统计信息（兼容 visual 前端）"""
    data = _load_viz_data(kg_id)
    nodes = data.get("nodes", [])
    stats = {
        "total_nodes": len(nodes),
        "level_0": 0,
        "level_1": 0,
        "level_2": 0,
        "level_3": 0,
        "level_4_plus": 0,
        "type_count": {},
        "categories": ["Root", "Section", "Block", "Nested"],
        "has_formulas": 0,
        "has_key_points": 0,
        "total_folders": 0,
    }
    for n in nodes:
        try:
            lvl = int(n.get("level", 5))
        except Exception:
            lvl = 5
        if lvl == 0:
            stats["level_0"] += 1
        elif lvl == 1:
            stats["level_1"] += 1
        elif lvl == 2:
            stats["level_2"] += 1
        elif lvl == 3:
            stats["level_3"] += 1
        else:
            stats["level_4_plus"] += 1

        ntype = n.get("type", "unknown") or "unknown"
        stats["type_count"][ntype] = stats["type_count"].get(ntype, 0) + 1

        if n.get("formulas"):
            stats["has_formulas"] += 1
        if n.get("key_points"):
            stats["has_key_points"] += 1
        if n.get("is_folder"):
            stats["total_folders"] += 1

    return stats


@app.get("/api/graph")
async def get_graph(max_level: Optional[str] = "10", kg_id: Optional[str] = None):
    """获取可视化图谱数据（nodes/links）"""
    data = _load_viz_data(kg_id)
    nodes = data.get("nodes", [])
    links = data.get("links", [])

    if max_level is None or str(max_level).lower() == "all":
        return {"nodes": nodes, "links": links}

    try:
        max_level_int = int(max_level)
    except Exception:
        max_level_int = 10

    filtered_nodes = []
    filtered_ids = set()
    for n in nodes:
        try:
            lvl = int(n.get("level", 999))
        except Exception:
            lvl = 999
        if lvl <= max_level_int:
            filtered_nodes.append(n)
            filtered_ids.add(n.get("id"))

    filtered_links = [
        l
        for l in links
        if l.get("source") in filtered_ids and l.get("target") in filtered_ids
    ]
    return {"nodes": filtered_nodes, "links": filtered_links}


@app.get("/api/search")
async def search_nodes(q: Optional[str] = "", kg_id: Optional[str] = None):
    """搜索节点"""
    query = (q or "").strip().lower()
    if not query:
        return []

    data = _load_viz_data(kg_id)
    nodes = data.get("nodes", [])
    results = []
    for n in nodes:
        title = (n.get("title", "") or "").lower()
        desc = (n.get("description", "") or "").lower()
        if query in title or query in desc:
            results.append(n)
            if len(results) >= 20:
                break
    return results


@app.get("/api/node/{node_id}")
async def get_node_detail(node_id: str, kg_id: Optional[str] = None):
    """获取节点详情"""
    data = _load_viz_data(kg_id)
    nodes = data.get("nodes", [])
    node_map = _index_nodes(nodes)
    node = node_map.get(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    pid = node.get("parent_id")
    parent = node_map.get(pid) if pid else None
    children = [n for n in nodes if n.get("parent_id") == node_id]

    return {"node": node, "parent": parent, "children": children}


# ==================== Step 2: 大纲和讲稿生成 ====================

@app.post("/api/step2/generate-outline")
async def generate_outline(request: OutlineRequest):
    """
    生成PPT大纲和讲稿（Step 2）
    
    Args:
        request: 大纲生成请求
        
    Returns:
        大纲和讲稿数据
    """
    try:
        # 加载知识图谱
        kg_path = KNOWLEDGE_GRAPHS_DIR / f"{request.kg_id}.json"
        if not kg_path.exists():
            raise HTTPException(status_code=404, detail="知识图谱不存在")
        
        import json
        with open(kg_path, 'r', encoding='utf-8') as f:
            kg_data = json.load(f)
        
        # 准备用户需求
        user_requirements = {
            'detail_level': {
                point.id: point.detail_level 
                for point in request.knowledge_points
            },
            'style': request.style,
            'other_requirements': request.other_requirements
        }
        
        # 转换知识点格式
        knowledge_points = []
        for point in request.knowledge_points:
            # 从知识图谱中查找对应的节点
            node = next(
                (n for n in kg_data.get('knowledge_graph', {}).get('nodes', []) 
                 if n['id'] == point.id),
                None
            )
            if node:
                knowledge_points.append({
                    'id': point.id,
                    'title': node['label'],
                    'content': node.get('content', '')
                })
        
        # 生成大纲和讲稿
        logger.info("开始生成大纲和讲稿...")
        result = await outline_generator.generate_outline_and_script(
            knowledge_points,
            user_requirements,
            kg_data
        )
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error', '生成失败'))
        
        # 保存大纲
        outline_id = f"outline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        outline_path = OUTLINES_DIR / f"{outline_id}.json"
        outline_generator.save_outline(result, str(outline_path))
        
        # 更新会话数据
        if request.kg_id in sessions:
            sessions[request.kg_id]['outline_id'] = outline_id
            sessions[request.kg_id]['outline_path'] = str(outline_path)
        
        return {
            "success": True,
            "outline_id": outline_id,
            "outline": result['outline'],
            "script": result['script'],
            "metadata": result['metadata']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 生成大纲失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Step 2.5: 讲稿编辑（新增） ====================

@app.post("/api/step2/init-script-edit")
async def init_script_edit_session(outline_id: str):
    """
    初始化讲稿编辑会话
    
    Args:
        outline_id: 大纲ID
        
    Returns:
        编辑会话信息
    """
    try:
        # 加载大纲和讲稿
        outline_path = OUTLINES_DIR / f"{outline_id}.json"
        if not outline_path.exists():
            raise HTTPException(status_code=404, detail="大纲不存在")
        
        import json
        with open(outline_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        outline = data.get('outline', {})
        script = data.get('script', {})
        
        # 创建编辑器实例
        try:
            from utils.llm import CustomLLM
            llm_client = CustomLLM()
        except ImportError:
            logger.warning("⚠️  未找到LLM客户端")
            llm_client = None
        
        editor = ScriptEditor(llm_client)
        editor.initialize_session(outline, script)
        
        # 存储编辑会话
        script_edit_sessions[outline_id] = editor
        
        logger.info(f"✅ 讲稿编辑会话已初始化: {outline_id}")
        
        return {
            "success": True,
            "outline_id": outline_id,
            "current_script": script,
            "current_outline": outline,
            "session_info": {
                "initialized_at": datetime.now().isoformat(),
                "sections_count": len(script.get('sections', []))
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 初始化编辑会话失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/step2/edit-script")
async def edit_script(request: ScriptEditRequest):
    """
    处理讲稿编辑请求（支持多轮对话）
    
    Args:
        request: 编辑请求
        
    Returns:
        LLM响应和更新后的讲稿
    """
    try:
        outline_id = request.outline_id
        
        # 检查编辑会话是否存在
        if outline_id not in script_edit_sessions:
            # 如果不存在，尝试初始化
            init_result = await init_script_edit_session(outline_id)
            if not init_result['success']:
                raise HTTPException(status_code=404, detail="无法初始化编辑会话")
        
        editor = script_edit_sessions[outline_id]
        
        # 处理用户消息
        result = await editor.process_user_message(
            request.user_message,
            request.context
        )
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error', '处理失败'))
        
        return {
            "success": True,
            "assistant_message": result['assistant_message'],
            "updated_script": result['updated_script'],
            "modifications_applied": result['modifications_applied'],
            "conversation_history": result['conversation_history']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 编辑讲稿失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/step2/script-conversation/{outline_id}")
async def get_script_conversation(outline_id: str):
    """获取讲稿编辑的对话历史"""
    try:
        if outline_id not in script_edit_sessions:
            raise HTTPException(status_code=404, detail="编辑会话不存在")
        
        editor = script_edit_sessions[outline_id]
        
        return {
            "success": True,
            "conversation_history": editor.get_conversation_history(),
            "modification_history": editor.get_modification_history(),
            "current_script": editor.get_current_script()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取对话历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/step2/save-script")
async def save_edited_script(request: ScriptSaveRequest):
    """
    保存编辑后的讲稿
    
    Args:
        request: 保存请求
        
    Returns:
        保存结果
    """
    try:
        outline_id = request.outline_id
        
        # 加载原始大纲数据
        outline_path = OUTLINES_DIR / f"{outline_id}.json"
        if not outline_path.exists():
            raise HTTPException(status_code=404, detail="大纲不存在")
        
        import json
        with open(outline_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 更新讲稿
        data['script'] = request.updated_script
        data['metadata']['last_modified'] = datetime.now().isoformat()
        
        # 保存到原文件
        with open(outline_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 如果存在编辑会话，也保存会话数据
        if outline_id in script_edit_sessions:
            editor = script_edit_sessions[outline_id]
            session_path = OUTLINES_DIR / f"{outline_id}_session.json"
            editor.save_session(str(session_path))
        
        logger.info(f"✅ 讲稿已保存: {outline_path}")
        
        return {
            "success": True,
            "outline_id": outline_id,
            "saved_at": datetime.now().isoformat(),
            "message": "讲稿已成功保存"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 保存讲稿失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Step 3: PPT创建 ====================

@app.post("/api/step3/create-ppt")
async def create_ppt(outline_id: str, template_path: Optional[str] = None):
    """
    创建初版PPT（Step 3）
    
    Args:
        outline_id: 大纲ID
        template_path: PPT模板路径（可选）
        
    Returns:
        PPT文件路径
    """
    try:
        # 加载大纲和讲稿
        outline_path = OUTLINES_DIR / f"{outline_id}.json"
        if not outline_path.exists():
            raise HTTPException(status_code=404, detail="大纲不存在")
        
        import json
        with open(outline_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        outline = data.get('outline', {})
        script = data.get('script', {})
        
        # 创建PPT
        logger.info("开始创建PPT...")
        
        # 如果提供了模板，使用模板
        if template_path:
            creator = PPTCreator(template_path=template_path)
        else:
            creator = PPTCreator()
        
        result = await creator.create_initial_ppt(outline, script)
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error', '创建失败'))
        
        ppt_path = result['output_path']
        
        # 返回文件下载路径
        relative_path = Path(ppt_path).relative_to(DATA_DIR)
        download_url = f"/static/{relative_path}"
        
        return {
            "success": True,
            "ppt_path": ppt_path,
            "download_url": download_url,
            "metadata": result['metadata']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 创建PPT失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Step 4: PPT修改 ====================

@app.post("/api/step4/modify-ppt")
async def modify_ppt(request: ModificationRequest):
    """
    修改PPT（Step 4 - 支持多轮交互）
    
    Args:
        request: 修改请求
        
    Returns:
        修改后的PPT路径
    """
    try:
        # 检查PPT文件是否存在
        if not Path(request.ppt_path).exists():
            raise HTTPException(status_code=404, detail="PPT文件不存在")
        
        # 修改PPT
        logger.info("开始修改PPT...")
        
        creator = PPTCreator()
        result = await creator.modify_ppt(
            request.ppt_path,
            {'description': request.description}
        )
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error', '修改失败'))
        
        ppt_path = result['output_path']
        
        # 返回文件下载路径
        relative_path = Path(ppt_path).relative_to(DATA_DIR)
        download_url = f"/static/{relative_path}"
        
        return {
            "success": True,
            "ppt_path": ppt_path,
            "download_url": download_url,
            "modifications_applied": result.get('modifications_applied', 0),
            "metadata": result['metadata']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 修改PPT失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 辅助端点 ====================

@app.get("/api/templates")
async def list_templates():
    """列出可用的PPT模板"""
    from utils.ppt_generator import PPTTemplateManager
    from config.config import TEMPLATES_DIR
    
    manager = PPTTemplateManager(str(TEMPLATES_DIR))
    templates = manager.list_templates()
    
    return {
        "templates": templates,
        "count": len(templates)
    }


@app.get("/api/sessions")
async def list_sessions():
    """列出所有会话"""
    return {
        "sessions": sessions,
        "count": len(sessions)
    }


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    if session_id in sessions:
        del sessions[session_id]
        return {"success": True, "message": "会话已删除"}
    else:
        raise HTTPException(status_code=404, detail="会话不存在")


# ==================== Step 5: 视频生成 ====================

@app.post("/api/step5/generate-video")
async def generate_video(request: VideoGenerateRequest, background_tasks: BackgroundTasks):
    """
    生成视频（Step 5）
    
    从最终修改后的讲稿生成完整视频（PPTX + 动画 + 语音 + 字幕）
    
    Args:
        request: 视频生成请求
        
    Returns:
        视频生成任务信息
    """
    try:
        # 加载大纲和讲稿
        outline_path = OUTLINES_DIR / f"{request.outline_id}.json"
        if not outline_path.exists():
            raise HTTPException(status_code=404, detail="大纲不存在")
        
        import json
        with open(outline_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        outline = data.get('outline', {})
        script = data.get('script', {})
        
        if not script:
            raise HTTPException(status_code=400, detail="讲稿不存在，请先生成讲稿")
        
        # 将script转换为videopipeline需要的JSON格式
        pipeline_json = _convert_script_to_pipeline_format(outline, script)
        
        # 保存临时JSON文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_json_path = OUTLINES_DIR / f"video_input_{timestamp}.json"
        with open(temp_json_path, 'w', encoding='utf-8') as f:
            json.dump(pipeline_json, f, ensure_ascii=False, indent=2)
        
        # 设置输出目录
        output_dir = DATA_DIR / "pipeline_outputs" / f"video_{request.outline_id}_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 模板路径
        template_path = Path(__file__).parent / "modules" / "videopipeline" / "template" / "template.pptx"
        
        # 创建Pipeline实例
        pipeline = VideoPipeline(
            json_path=str(temp_json_path),
            template_path=str(template_path),
            output_dir=str(output_dir)
        )
        
        # 在后台任务中执行Pipeline（因为耗时较长）
        task_id = f"video_{request.outline_id}_{timestamp}"
        
        def run_pipeline():
            try:
                result = pipeline.run()
                logger.info(f"✅ 视频生成完成: {task_id}")
            except Exception as e:
                logger.error(f"❌ 视频生成失败: {e}")
                import traceback
                traceback.print_exc()
        
        # 启动后台任务
        background_tasks.add_task(run_pipeline)
        
        return {
            "success": True,
            "task_id": task_id,
            "outline_id": request.outline_id,
            "status": "processing",
            "message": "视频生成任务已启动，请使用task_id查询进度",
            "estimated_time": "5-10分钟"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 启动视频生成失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/step5/video-status/{task_id}")
async def get_video_status(task_id: str):
    """
    查询视频生成状态
    
    Args:
        task_id: 任务ID
        
    Returns:
        视频生成状态和结果
    """
    try:
        # 从task_id解析outline_id和timestamp
        # task_id格式: video_{outline_id}_{timestamp}
        parts = task_id.split('_', 2)
        if len(parts) < 3:
            raise HTTPException(status_code=400, detail="无效的任务ID")
        
        outline_id = parts[1]
        timestamp = parts[2]
        
        # 查找输出目录
        output_dir = DATA_DIR / "pipeline_outputs" / f"video_{outline_id}_{timestamp}"
        
        if not output_dir.exists():
            return {
                "success": False,
                "status": "not_found",
                "message": "任务不存在"
            }
        
        # 检查是否完成（存在final_video.mp4）
        video_path = output_dir / "videos" / "final_video.mp4"
        pptx_path = output_dir / "pptx" / "presentation_optimized.pptx"
        audio_path = output_dir / "audio" / "full_audio.mp3"
        subtitle_path = output_dir / "subtitles" / "subtitles.srt"
        
        if video_path.exists():
            # 生成下载URL
            video_relative = video_path.relative_to(DATA_DIR)
            pptx_relative = pptx_path.relative_to(DATA_DIR) if pptx_path.exists() else None
            audio_relative = audio_path.relative_to(DATA_DIR) if audio_path.exists() else None
            subtitle_relative = subtitle_path.relative_to(DATA_DIR) if subtitle_path.exists() else None
            
            return {
                "success": True,
                "status": "completed",
                "task_id": task_id,
                "video_url": f"/static/{video_relative}",
                "pptx_url": f"/static/{pptx_relative}" if pptx_relative else None,
                "audio_url": f"/static/{audio_relative}" if audio_relative else None,
                "subtitle_url": f"/static/{subtitle_relative}" if subtitle_relative else None,
                "video_path": str(video_path),
                "message": "视频生成完成"
            }
        else:
            # 检查是否在生成中（存在slides_data.json表示至少开始了）
            slides_data = output_dir / "slides_data.json"
            if slides_data.exists():
                return {
                    "success": True,
                    "status": "processing",
                    "message": "视频正在生成中，请稍候..."
                }
            else:
                return {
                    "success": True,
                    "status": "queued",
                    "message": "任务已排队，等待处理..."
                }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 查询视频状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _convert_script_to_pipeline_format(outline: Dict, script: Dict) -> Dict:
    """
    将outline和script转换为videopipeline需要的JSON格式
    
    Args:
        outline: 大纲数据
        script: 讲稿数据
        
    Returns:
        videopipeline格式的JSON
    """
    return {
        "success": True,
        "outline": outline,
        "script": script,
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "source": "api"
        }
    }


# ==================== 文件下载 ====================

@app.get("/api/download/{file_type}/{file_id}")
async def download_file(file_type: str, file_id: str):
    """
    下载文件
    
    Args:
        file_type: 文件类型 (kg/outline/ppt)
        file_id: 文件ID
    """
    try:
        if file_type == 'kg':
            file_path = KNOWLEDGE_GRAPHS_DIR / f"{file_id}.json"
        elif file_type == 'outline':
            file_path = OUTLINES_DIR / f"{file_id}.json"
        elif file_type == 'ppt':
            # file_id是完整路径
            file_path = Path(file_id)
        else:
            raise HTTPException(status_code=400, detail="不支持的文件类型")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        return FileResponse(
            path=str(file_path),
            filename=file_path.name,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 下载文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 运行应用 ====================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host=API_CONFIG['host'],
        port=API_CONFIG['port'],
        log_level="info"
    )
