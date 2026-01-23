/**
 * Step 2: 选择知识点并生成大纲
 */

import React, { useState } from 'react';
import { Card, Button, Select, Table, Radio, Input, message, Spin } from 'antd';
import { ArrowLeftOutlined, ArrowRightOutlined, EditOutlined } from '@ant-design/icons';
import { generateOutline } from '../services/api';
import Step2ScriptEdit from './Step2ScriptEdit';

const { TextArea } = Input;

function Step2Outline({ sessionData, updateSessionData, onNext, onPrev }) {
  const [selectedPoints, setSelectedPoints] = useState([]);
  const [detailLevels, setDetailLevels] = useState({});
  const [style, setStyle] = useState('简约');
  const [otherRequirements, setOtherRequirements] = useState('');
  const [generating, setGenerating] = useState(false);
  const [outlineData, setOutlineData] = useState(null);
  const [isEditingScript, setIsEditingScript] = useState(false);

  const knowledgePoints = sessionData.kgData?.knowledge_points || [];

  // 如果正在编辑讲稿，显示编辑界面
  if (isEditingScript) {
    return (
      <Step2ScriptEdit
        sessionData={sessionData}
        updateSessionData={updateSessionData}
        onBack={() => setIsEditingScript(false)}
        onNext={onNext}
      />
    );
  }

  const columns = [
    {
      title: '选择',
      dataIndex: 'id',
      key: 'select',
      render: (id) => (
        <input
          type="checkbox"
          checked={selectedPoints.includes(id)}
          onChange={(e) => handlePointSelection(id, e.target.checked)}
        />
      ),
    },
    {
      title: '知识点',
      dataIndex: 'title',
      key: 'title',
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
    },
    {
      title: '详细程度',
      dataIndex: 'id',
      key: 'detail',
      render: (id) => (
        <Select
          value={detailLevels[id] || '标准'}
          onChange={(value) => setDetailLevels({ ...detailLevels, [id]: value })}
          disabled={!selectedPoints.includes(id)}
          style={{ width: 120 }}
        >
          <Select.Option value="精讲">精讲</Select.Option>
          <Select.Option value="标准">标准</Select.Option>
          <Select.Option value="粗讲">粗讲</Select.Option>
        </Select>
      ),
    },
  ];

  const handlePointSelection = (id, checked) => {
    if (checked) {
      setSelectedPoints([...selectedPoints, id]);
      if (!detailLevels[id]) {
        setDetailLevels({ ...detailLevels, [id]: '标准' });
      }
    } else {
      setSelectedPoints(selectedPoints.filter((p) => p !== id));
    }
  };

  const handleGenerate = async () => {
    if (selectedPoints.length === 0) {
      message.warning('请至少选择一个知识点');
      return;
    }

    try {
      setGenerating(true);
      
      const pointsData = selectedPoints.map((id) => ({
        id,
        title: knowledgePoints.find((p) => p.id === id)?.title || '',
        detail_level: detailLevels[id] || '标准',
      }));

      const result = await generateOutline(
        sessionData.kgId,
        pointsData,
        style,
        otherRequirements
      );

      setOutlineData(result);
      updateSessionData({
        outlineId: result.outline_id,
        outlineData: result,
      });

      message.success('大纲和讲稿生成成功！');
    } catch (error) {
      message.error('生成失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setGenerating(false);
    }
  };

  const handleNext = () => {
    if (!outlineData) {
      message.warning('请先生成大纲');
      return;
    }
    onNext();
  };

  return (
    <div className="step-container">
      <Card title="📝 Step 2: 选择知识点并生成大纲" className="step-card">
        <div className="selection-section">
          <h3>📚 选择要讲解的知识点</h3>
          <Table
            dataSource={knowledgePoints}
            columns={columns}
            rowKey="id"
            pagination={{ pageSize: 10 }}
          />

          <div className="style-section">
            <h3>🎨 选择PPT风格</h3>
            <Radio.Group value={style} onChange={(e) => setStyle(e.target.value)}>
              <Radio.Button value="简约">简约</Radio.Button>
              <Radio.Button value="学术">学术</Radio.Button>
              <Radio.Button value="商务">商务</Radio.Button>
              <Radio.Button value="活泼">活泼</Radio.Button>
            </Radio.Group>
          </div>

          <div className="requirements-section">
            <h3>✏️ 其他要求（可选）</h3>
            <TextArea
              rows={4}
              placeholder="例如：需要多添加一些例子，每页内容不要太多..."
              value={otherRequirements}
              onChange={(e) => setOtherRequirements(e.target.value)}
            />
          </div>

          <div className="action-buttons">
            <Button onClick={onPrev} icon={<ArrowLeftOutlined />}>
              上一步
            </Button>
            <Button
              type="primary"
              size="large"
              onClick={handleGenerate}
              loading={generating}
              disabled={selectedPoints.length === 0}
            >
              {generating ? '生成中...' : '生成大纲和讲稿'}
            </Button>
          </div>
        </div>

        {outlineData && (
          <div className="outline-result">
            <Card title="📋 生成的大纲" className="outline-card">
              <h2>{outlineData.outline?.title || '课程演示'}</h2>
              
              {outlineData.outline?.sections?.map((section, idx) => (
                <div key={idx} className="section-item">
                  <h3>第{idx + 1}部分: {section.title}</h3>
                  <p>详细程度: {section.detail_level}</p>
                  <ul>
                    {section.points?.map((point, pIdx) => (
                      <li key={pIdx}>
                        <strong>{point.title}</strong>
                        <p>{point.content}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}

              <div className="metadata">
                <p>📊 总章节数: {outlineData.metadata?.total_slides || 0}</p>
                <p>🎨 风格: {outlineData.metadata?.style || '默认'}</p>
              </div>
            </Card>

            <div className="next-step-button">
              <Button
                icon={<EditOutlined />}
                size="large"
                onClick={() => setIsEditingScript(true)}
                style={{ marginRight: 12 }}
              >
                编辑讲稿
              </Button>
              <Button
                type="primary"
                size="large"
                icon={<ArrowRightOutlined />}
                onClick={handleNext}
              >
                下一步：生成PPT
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

export default Step2Outline;