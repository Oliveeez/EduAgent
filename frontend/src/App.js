/**
 * 主应用组件
 */

import React, { useState } from 'react';
import { Layout, Steps, Button, message } from 'antd';
import {
  FileTextOutlined,
  NodeIndexOutlined,
  FileWordOutlined,
  EditOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons';

import Step1Upload from './pages/Step1Upload';
import Step2Outline from './pages/Step2Outline';
import Step3PPT from './pages/Step3PPT';
import Step4Modify from './pages/Step4Modify';
import Step5Video from './pages/Step5Video';

import './styles/App.css';

const { Header, Content, Footer } = Layout;

function App() {
  const [current, setCurrent] = useState(0);
  const [sessionData, setSessionData] = useState({
    fileId: null,
    kgId: null,
    kgData: null,
    outlineId: null,
    outlineData: null,
    pptPath: null,
  });

  const steps = [
    {
      title: 'Step 1',
      description: '上传LaTeX & 提取知识图谱',
      icon: <FileTextOutlined />,
    },
    {
      title: 'Step 2',
      description: '选择知识点 & 生成大纲',
      icon: <NodeIndexOutlined />,
    },
    {
      title: 'Step 3',
      description: '生成PPT',
      icon: <FileWordOutlined />,
    },
    {
      title: 'Step 4',
      description: '修改PPT',
      icon: <EditOutlined />,
    },
    {
      title: 'Step 5',
      description: '生成视频',
      icon: <VideoCameraOutlined />,
    },
  ];

  const next = () => {
    setCurrent(current + 1);
  };

  const prev = () => {
    setCurrent(current - 1);
  };

  const updateSessionData = (data) => {
    setSessionData({ ...sessionData, ...data });
  };

  const renderStepContent = () => {
    switch (current) {
      case 0:
        return (
          <Step1Upload
            sessionData={sessionData}
            updateSessionData={updateSessionData}
            onNext={next}
          />
        );
      case 1:
        return (
          <Step2Outline
            sessionData={sessionData}
            updateSessionData={updateSessionData}
            onNext={next}
            onPrev={prev}
          />
        );
      case 2:
        return (
          <Step3PPT
            sessionData={sessionData}
            updateSessionData={updateSessionData}
            onNext={next}
            onPrev={prev}
          />
        );
      case 3:
        return (
          <Step4Modify
            sessionData={sessionData}
            updateSessionData={updateSessionData}
            onNext={next}
            onPrev={prev}
          />
        );
      case 4:
        return (
          <Step5Video
            sessionData={sessionData}
            updateSessionData={updateSessionData}
            onBack={prev}
            onComplete={() => message.success('视频生成流程完成！')}
          />
        );
      default:
        return null;
    }
  };

  return (
    <Layout className="app-layout">
      <Header className="app-header">
        <div className="header-content">
          <div className="header-left">
            <img src="/logo_white.png" alt="SJTU Logo" className="header-logo" />
          </div>
          <div className="header-right">
            <h1>📚 课堂视频生成Agent</h1>
            <p>智能教学视频生成系统 - 让教学更高效</p>
          </div>
        </div>
      </Header>

      <Content className="app-content">
        <div className="steps-container">
          <Steps
            current={current}
            items={steps.map((step) => ({
              title: step.title,
              description: step.description,
              icon: step.icon,
            }))}
          />
        </div>

        <div className="step-content">{renderStepContent()}</div>
      </Content>

      <Footer className="app-footer">
        <p>Classroom Video Agent © 2026 | Powered by Gemini3-pro | Shanghai Jiao Tong University</p>
      </Footer>
    </Layout>
  );
}

export default App;