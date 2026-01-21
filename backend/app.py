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

# 导入配置
from config.config import (
    API_CONFIG, DATA_DIR, LATEX_UPLOADS_DIR, 
    KNOWLEDGE_GRAPHS_DIR, OUTLINES_DIR, PPT_OUTPUT_DIR
)

# 导入模块
from modules.knowledge_extractor import KnowledgeExtractor
from modules.outline_generator import OutlineGenerator
from modules.ppt_creator import PPTCreator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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


# ==================== 全局状态 ====================

# 初始化模块（LLM客户端由用户在外部提供）
knowledge_extractor = KnowledgeExtractor()
outline_generator = None  # 需要在启动时初始化
ppt_creator = None  # 需要在启动时初始化

# 存储会话数据
sessions = {}


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
            "visualization": result['visualization']
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