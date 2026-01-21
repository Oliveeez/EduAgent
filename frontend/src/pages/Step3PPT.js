/**
 * Step 3: 生成PPT
 */

import React, { useState } from 'react';
import { Card, Button, Select, message, Result } from 'antd';
import { ArrowLeftOutlined, ArrowRightOutlined, DownloadOutlined } from '@ant-design/icons';
import { createPPT, listTemplates } from '../services/api';

function Step3PPT({ sessionData, updateSessionData, onNext, onPrev }) {
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [pptResult, setPptResult] = useState(null);

  React.useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      const result = await listTemplates();
      setTemplates(result.templates || []);
    } catch (error) {
      console.error('加载模板失败:', error);
    }
  };

  const handleGenerate = async () => {
    try {
      setGenerating(true);
      
      const result = await createPPT(sessionData.outlineId, selectedTemplate);
      
      setPptResult(result);
      updateSessionData({
        pptPath: result.ppt_path,
      });

      message.success('PPT生成成功！');
    } catch (error) {
      message.error('生成失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = () => {
    if (pptResult?.download_url) {
      window.open(pptResult.download_url, '_blank');
    }
  };

  return (
    <div className="step-container">
      <Card title="📊 Step 3: 生成PPT" className="step-card">
        <div className="template-section">
          <h3>🎨 选择PPT模板（可选）</h3>
          <Select
            placeholder="选择模板或使用默认模板"
            style={{ width: '100%', marginBottom: 20 }}
            value={selectedTemplate}
            onChange={setSelectedTemplate}
            allowClear
          >
            {templates.map((template) => (
              <Select.Option key={template.path} value={template.path}>
                {template.name}
              </Select.Option>
            ))}
          </Select>

          <div className="action-buttons">
            <Button onClick={onPrev} icon={<ArrowLeftOutlined />}>
              上一步
            </Button>
            <Button
              type="primary"
              size="large"
              onClick={handleGenerate}
              loading={generating}
            >
              {generating ? '生成中...' : '生成PPT'}
            </Button>
          </div>
        </div>

        {pptResult && (
          <div className="ppt-result">
            <Result
              status="success"
              title="PPT生成成功！"
              subTitle={
                <div>
                  <p>📄 幻灯片数: {pptResult.metadata?.total_slides || 0}</p>
                  <p>💾 文件路径: {pptResult.ppt_path}</p>
                </div>
              }
              extra={[
                <Button
                  type="primary"
                  icon={<DownloadOutlined />}
                  onClick={handleDownload}
                  key="download"
                >
                  下载PPT
                </Button>,
                <Button
                  icon={<ArrowRightOutlined />}
                  onClick={onNext}
                  key="next"
                >
                  下一步：修改PPT
                </Button>,
              ]}
            />
          </div>
        )}
      </Card>
    </div>
  );
}

export default Step3PPT;