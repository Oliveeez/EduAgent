/**
 * Step 4: 修改PPT（支持多轮交互）
 */

import React, { useState } from 'react';
import { Card, Button, Input, message, List, Tag } from 'antd';
import { ArrowLeftOutlined, DownloadOutlined, SendOutlined } from '@ant-design/icons';
import { modifyPPT } from '../services/api';

const { TextArea } = Input;

function Step4Modify({ sessionData, updateSessionData, onPrev }) {
  const [modifications, setModifications] = useState([]);
  const [currentInput, setCurrentInput] = useState('');
  const [modifying, setModifying] = useState(false);
  const [currentPptPath, setCurrentPptPath] = useState(sessionData.pptPath);

  const handleModify = async () => {
    if (!currentInput.trim()) {
      message.warning('请输入修改要求');
      return;
    }

    try {
      setModifying(true);
      
      const result = await modifyPPT(currentPptPath, currentInput);
      
      // 添加到修改历史
      setModifications([
        ...modifications,
        {
          input: currentInput,
          result: result,
          timestamp: new Date().toLocaleString(),
        },
      ]);

      // 更新当前PPT路径
      setCurrentPptPath(result.ppt_path);
      updateSessionData({
        pptPath: result.ppt_path,
      });

      message.success('PPT修改成功！');
      setCurrentInput('');
      
    } catch (error) {
      message.error('修改失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setModifying(false);
    }
  };

  const handleDownload = (pptPath) => {
    const relativePath = pptPath.replace(/^.*[\\/]data[\\/]/, '');
    window.open(`/static/${relativePath}`, '_blank');
  };

  return (
    <div className="step-container">
      <Card title="✏️ Step 4: 修改PPT（支持多轮交互）" className="step-card">
        <div className="modify-section">
          <h3>💬 输入修改要求</h3>
          <p className="hint-text">
            支持自然语言描述，例如：
            <ul>
              <li>"第3页的文字太多，精简一些"</li>
              <li>"第5页内容过多，分成2页"</li>
              <li>"为所有章节添加一个引言"</li>
              <li>"调整第2页的动画效果"</li>
            </ul>
          </p>

          <TextArea
            rows={4}
            placeholder="请描述你想要的修改..."
            value={currentInput}
            onChange={(e) => setCurrentInput(e.target.value)}
          />

          <div className="action-buttons">
            <Button onClick={onPrev} icon={<ArrowLeftOutlined />}>
              上一步
            </Button>
            <Button
              type="primary"
              size="large"
              icon={<SendOutlined />}
              onClick={handleModify}
              loading={modifying}
            >
              {modifying ? '修改中...' : '应用修改'}
            </Button>
          </div>
        </div>

        {modifications.length > 0 && (
          <div className="modifications-history">
            <h3>📝 修改历史</h3>
            <List
              dataSource={modifications}
              renderItem={(mod, idx) => (
                <List.Item
                  key={idx}
                  actions={[
                    <Button
                      icon={<DownloadOutlined />}
                      onClick={() => handleDownload(mod.result.ppt_path)}
                    >
                      下载
                    </Button>,
                  ]}
                >
                  <List.Item.Meta
                    title={
                      <div>
                        <Tag color="blue">修改 {idx + 1}</Tag>
                        <span>{mod.timestamp}</span>
                      </div>
                    }
                    description={
                      <div>
                        <p><strong>要求:</strong> {mod.input}</p>
                        <p><strong>应用了:</strong> {mod.result.modifications_applied} 项修改</p>
                        <p><strong>文件:</strong> {mod.result.ppt_path}</p>
                      </div>
                    }
                  />
                </List.Item>
              )}
            />
          </div>
        )}

        <div className="current-ppt-info">
          <Card title="📄 当前PPT" size="small">
            <p><strong>路径:</strong> {currentPptPath}</p>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={() => handleDownload(currentPptPath)}
            >
              下载最新版本
            </Button>
          </Card>
        </div>
      </Card>
    </div>
  );
}

export default Step4Modify;