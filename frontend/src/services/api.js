/**
 * API服务 - 与后端通信
 */

import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5分钟超时（某些操作可能很耗时）
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    console.log(`[API] Response:`, response.data);
    return response;
  },
  (error) => {
    console.error('[API] Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// ========== Step 1: 知识图谱提取 ==========

/**
 * 上传LaTeX文件
 */
export const uploadLatex = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post('/step1/upload-latex', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  
  return response.data;
};

/**
 * 提取知识图谱
 */
export const extractKnowledgeGraph = async (fileId) => {
  const response = await api.post('/step1/extract-kg', null, {
    params: { file_id: fileId },
  });
  return response.data;
};

/**
 * 获取知识图谱
 */
export const getKnowledgeGraph = async (kgId) => {
  const response = await api.get(`/step1/kg/${kgId}`);
  return response.data;
};

// ========== Step 2: 大纲和讲稿生成 ==========

/**
 * 生成大纲和讲稿
 */
export const generateOutline = async (kgId, knowledgePoints, style, otherRequirements) => {
  const response = await api.post('/step2/generate-outline', {
    kg_id: kgId,
    knowledge_points: knowledgePoints,
    style: style || '简约',
    other_requirements: otherRequirements,
  });
  return response.data;
};

// ========== Step 2.5: 讲稿编辑 ==========

/**
 * 初始化讲稿编辑会话
 */
export const initScriptEdit = async (outlineId) => {
  const response = await api.post('/step2/init-script-edit', null, {
    params: {
      outline_id: outlineId,
    },
  });
  return response.data;
};

/**
 * 编辑讲稿（发送消息）
 */
export const editScript = async (data) => {
  const response = await api.post('/step2/edit-script', data);
  return response.data;
};

/**
 * 获取讲稿编辑对话历史
 */
export const getScriptConversation = async (outlineId) => {
  const response = await api.get(`/step2/script-conversation/${outlineId}`);
  return response.data;
};

/**
 * 保存编辑后的讲稿
 */
export const saveScript = async (data) => {
  const response = await api.post('/step2/save-script', data);
  return response.data;
};

// ========== Step 3: PPT创建 ==========

/**
 * 创建PPT
 */
export const createPPT = async (outlineId, templatePath = null) => {
  const response = await api.post('/step3/create-ppt', null, {
    params: {
      outline_id: outlineId,
      template_path: templatePath,
    },
  });
  return response.data;
};

// ========== Step 4: PPT修改 ==========

/**
 * 修改PPT
 */
export const modifyPPT = async (pptPath, description) => {
  const response = await api.post('/step4/modify-ppt', {
    ppt_path: pptPath,
    description: description,
  });
  return response.data;
};

// ========== 辅助接口 ==========

/**
 * 获取可用模板列表
 */
export const listTemplates = async () => {
  const response = await api.get('/templates');
  return response.data;
};

/**
 * 获取会话列表
 */
export const listSessions = async () => {
  const response = await api.get('/sessions');
  return response.data;
};

/**
 * 健康检查
 */
export const healthCheck = async () => {
  const response = await api.get('/health');
  return response.data;
};

export default api;