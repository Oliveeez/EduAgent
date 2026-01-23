/**
 * Step 1: 上传LaTeX文件并提取知识图谱
 */

import React, { useEffect, useState } from 'react';
import { Upload, Button, Card, Spin, message, Progress, Result, Select } from 'antd';
import { InboxOutlined, ArrowRightOutlined } from '@ant-design/icons';
import { uploadLatex, extractKnowledgeGraph, listKnowledgeGraphVizFiles } from '../services/api';
import VisualGraphDashboard from '../components/visual/VisualGraphDashboard';

const { Dragger } = Upload;

function Step1Upload({ sessionData, updateSessionData, onNext }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [kgData, setKgData] = useState(null);
  const [vizOptions, setVizOptions] = useState([]);
  const [existingKgId, setExistingKgId] = useState(null);

  useEffect(() => {
    const fetchVizList = async () => {
      try {
        const data = await listKnowledgeGraphVizFiles();
        const items = data.items || [];
        setVizOptions(items);
        if (items.length > 0) {
          setExistingKgId(items[0].kg_id);
        }
      } catch (error) {
        console.error('Failed to fetch viz list:', error);
      }
    };
    fetchVizList();
  }, []);

  const handleFileChange = (info) => {
    // 当beforeUpload返回false时，直接从fileList获取文件
    if (info.fileList.length > 0) {
      const latestFile = info.fileList[info.fileList.length - 1];
      setFile(latestFile);
      message.success(`${latestFile.name} 文件准备就绪`);
    } else {
      setFile(null);
    }
  };

  const handleUploadAndExtract = async () => {
    if (!file) {
      message.error('请先选择LaTeX文件');
      return;
    }

    try {
      // Step 1: 上传文件
      setUploading(true);
      setProgress(20);
      
      const uploadResult = await uploadLatex(file.originFileObj);
      const fileId = uploadResult.file_id;
      
      message.success('文件上传成功！');
      setProgress(40);

      // Step 2: 提取知识图谱
      setUploading(false);
      setExtracting(true);
      setProgress(60);
      
      const kgResult = await extractKnowledgeGraph(fileId);
      
      setProgress(100);
      setKgData(kgResult);
      
      // 更新会话数据
      updateSessionData({
        fileId: fileId,
        kgId: kgResult.kg_id,
        kgData: kgResult,
      });

      message.success('知识图谱提取完成！');
      
    } catch (error) {
      message.error('处理失败: ' + (error.response?.data?.detail || error.message));
      setProgress(0);
    } finally {
      setUploading(false);
      setExtracting(false);
    }
  };

  const handleNext = () => {
    if (!kgData) {
      message.warning('请先提取知识图谱');
      return;
    }
    onNext();
  };

  const handleUseExisting = () => {
    if (!existingKgId) {
      message.warning('暂无可用的可视化图谱');
      return;
    }
    setKgData({
      kg_id: existingKgId,
      knowledge_points: [],
      statistics: {},
    });
    updateSessionData({
      kgId: existingKgId,
      kgData: { kg_id: existingKgId },
    });
    message.success('已加载已有知识图谱');
  };

  return (
    <div className="step-container">
      <Card title="📖 Step 1: 上传LaTeX文档并提取知识图谱" className="step-card">
        <div className="upload-section">
          <Dragger
            name="file"
            accept=".tex"
            multiple={false}
            fileList={file ? [file] : []}
            beforeUpload={() => false}
            onChange={handleFileChange}
            onRemove={() => setFile(null)}
            disabled={uploading || extracting}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">点击或拖拽LaTeX文件到此区域</p>
            <p className="ant-upload-hint">
              支持 .tex 格式的LaTeX文档
            </p>
          </Dragger>

          <div className="action-buttons">
            <Button
              type="primary"
              size="large"
              onClick={handleUploadAndExtract}
              loading={uploading || extracting}
              disabled={!file || kgData}
            >
              {uploading ? '上传中...' : extracting ? '提取知识图谱中...' : '上传并提取知识图谱'}
            </Button>
            <Button
              size="large"
              onClick={handleUseExisting}
              disabled={uploading || extracting}
            >
              使用已有图谱
            </Button>
            <Select
              style={{ minWidth: 260 }}
              value={existingKgId}
              onChange={setExistingKgId}
              placeholder="选择已有图谱"
              options={vizOptions.map((item) => ({
                value: item.kg_id,
                label: item.filename,
              }))}
              disabled={uploading || extracting}
            />
          </div>

          {(uploading || extracting) && (
            <div className="progress-section">
              <Progress percent={progress} status="active" />
              <p className="progress-text">
                {uploading ? '正在上传文件...' : '正在提取知识图谱，请稍候...'}
              </p>
            </div>
          )}
        </div>

        {kgData && (
          <div className="result-section">
            <Result
              status="success"
              title="知识图谱提取成功！"
              subTitle={
                <div>
                  <p>📊 总节点数: {kgData.statistics?.total_nodes || 0}</p>
                  <p>🔗 总边数: {kgData.statistics?.total_edges || 0}</p>
                  <p>📚 知识点数: {kgData.knowledge_points?.length || 0}</p>
                </div>
              }
            />

            <Card title="🔍 知识图谱可视化" className="visualization-card">
              <VisualGraphDashboard kgId={kgData?.kg_id || existingKgId} />
            </Card>

            <div className="knowledge-points-summary">
              <h3>📋 知识点列表</h3>
              <ul>
                {kgData.knowledge_points?.slice(0, 10).map((point) => (
                  <li key={point.id}>
                    <strong>{point.title}</strong> ({point.type})
                  </li>
                ))}
                {kgData.knowledge_points?.length > 10 && (
                  <li>... 还有 {kgData.knowledge_points.length - 10} 个知识点</li>
                )}
              </ul>
            </div>

            <div className="next-step-button">
              <Button
                type="primary"
                size="large"
                icon={<ArrowRightOutlined />}
                onClick={handleNext}
              >
                下一步：选择知识点
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

export default Step1Upload;
