/**
 * Step 5: 视频生成页面
 * 美观的视频生成进度展示和结果播放
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  Layout,
  Card,
  Button,
  Space,
  Spin,
  message,
  Typography,
  Progress,
  Steps,
  Tag,
  Divider,
  Row,
  Col,
  Alert,
  Modal,
} from 'antd';
import {
  PlayCircleOutlined,
  DownloadOutlined,
  FilePptOutlined,
  SoundOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  ArrowLeftOutlined,
  VideoCameraOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import { generateVideo, getVideoStatus } from '../services/api';
import '../styles/VideoGeneration.css';

const { Content } = Layout;
const { Title, Text, Paragraph } = Typography;
const { Step } = Steps;

function Step5Video({ sessionData, updateSessionData, onBack, onComplete }) {
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [taskId, setTaskId] = useState(null);
  const [videoStatus, setVideoStatus] = useState(null);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);
  
  const pollIntervalRef = useRef(null);

  // 清理轮询
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  // 开始生成视频
  const handleGenerateVideo = async () => {
    if (!sessionData.outlineId) {
      message.error('请先完成前面的步骤');
      return;
    }

    setLoading(true);
    try {
      const response = await generateVideo(sessionData.outlineId, true);
      
      if (response.success) {
        setTaskId(response.task_id);
        setGenerating(true);
        setCurrentStep(0);
        message.success('视频生成任务已启动');
        
        // 开始轮询状态
        startPolling(response.task_id);
      }
    } catch (error) {
      message.error('启动视频生成失败：' + error.message);
    } finally {
      setLoading(false);
    }
  };

  // 轮询视频生成状态
  const startPolling = (taskId) => {
    const poll = async () => {
      try {
        const status = await getVideoStatus(taskId);
        setVideoStatus(status);
        
        if (status.status === 'completed') {
          // 生成完成
          setGenerating(false);
          setProgress(100);
          setCurrentStep(8);
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
          }
          message.success('视频生成完成！');
        } else if (status.status === 'processing') {
          // 正在生成，更新进度
          const estimatedProgress = Math.min(progress + 5, 90);
          setProgress(estimatedProgress);
          
          // 根据进度更新步骤（简化版）
          if (estimatedProgress < 20) setCurrentStep(1);
          else if (estimatedProgress < 40) setCurrentStep(2);
          else if (estimatedProgress < 60) setCurrentStep(3);
          else if (estimatedProgress < 80) setCurrentStep(5);
          else setCurrentStep(7);
        }
      } catch (error) {
        console.error('查询状态失败:', error);
      }
    };

    // 立即执行一次
    poll();
    
    // 每3秒轮询一次
    pollIntervalRef.current = setInterval(poll, 3000);
  };

  // 下载文件
  const handleDownload = (url, filename) => {
    const link = document.createElement('a');
    link.href = url.startsWith('http') ? url : `${process.env.REACT_APP_API_URL?.replace('/api', '')}${url}`;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const renderVideoPlayer = () => {
    if (!videoStatus || videoStatus.status !== 'completed') {
      return null;
    }

    const videoUrl = videoStatus.video_url.startsWith('http') 
      ? videoStatus.video_url 
      : `${process.env.REACT_APP_API_URL?.replace('/api', '')}${videoStatus.video_url}`;

    return (
      <Card className="video-player-card">
        <div className="video-container">
          <video
            controls
            src={videoUrl}
            className="video-player"
            poster={videoStatus.video_url} // 使用视频第一帧作为封面
          >
            您的浏览器不支持视频播放
          </video>
        </div>
      </Card>
    );
  };

  const renderDownloadSection = () => {
    if (!videoStatus || videoStatus.status !== 'completed') {
      return null;
    }

    const baseUrl = process.env.REACT_APP_API_URL?.replace('/api', '') || 'http://localhost:8000';

    return (
      <Card title="下载文件" className="download-card">
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={8}>
            <Card
              hoverable
              className="download-item"
              onClick={() => handleDownload(videoStatus.video_url, 'final_video.mp4')}
            >
              <VideoCameraOutlined className="download-icon" />
              <Title level={5}>完整视频</Title>
              <Text type="secondary">MP4格式</Text>
            </Card>
          </Col>
          {videoStatus.pptx_url && (
            <Col xs={24} sm={12} md={8}>
              <Card
                hoverable
                className="download-item"
                onClick={() => handleDownload(videoStatus.pptx_url, 'presentation.pptx')}
              >
                <FilePptOutlined className="download-icon" />
                <Title level={5}>PPTX文件</Title>
                <Text type="secondary">含动画</Text>
              </Card>
            </Col>
          )}
          {videoStatus.audio_url && (
            <Col xs={24} sm={12} md={8}>
              <Card
                hoverable
                className="download-item"
                onClick={() => handleDownload(videoStatus.audio_url, 'audio.mp3')}
              >
                <SoundOutlined className="download-icon" />
                <Title level={5}>音频文件</Title>
                <Text type="secondary">MP3格式</Text>
              </Card>
            </Col>
          )}
          {videoStatus.subtitle_url && (
            <Col xs={24} sm={12} md={8}>
              <Card
                hoverable
                className="download-item"
                onClick={() => handleDownload(videoStatus.subtitle_url, 'subtitles.srt')}
              >
                <FileTextOutlined className="download-icon" />
                <Title level={5}>字幕文件</Title>
                <Text type="secondary">SRT格式</Text>
              </Card>
            </Col>
          )}
        </Row>
      </Card>
    );
  };

  return (
    <div className="video-generation-container">
      <Layout>
        <Content className="video-content">
          {/* 页面标题 */}
          <div className="page-header">
            <Space>
              <Button icon={<ArrowLeftOutlined />} onClick={onBack}>
                返回
              </Button>
              <Title level={2}>
                <VideoCameraOutlined /> 视频生成
              </Title>
            </Space>
            {!generating && !videoStatus && (
              <Button
                type="primary"
                size="large"
                icon={<RocketOutlined />}
                onClick={handleGenerateVideo}
                loading={loading}
              >
                开始生成视频
              </Button>
            )}
          </div>

          <Divider />

          {/* 生成进度 */}
          {generating && (
            <Card className="progress-card">
              <Title level={4}>生成进度</Title>
              <Progress
                percent={progress}
                status={generating ? 'active' : 'success'}
                strokeColor={{
                  '0%': '#108ee9',
                  '100%': '#87d068',
                }}
              />
              
              <Steps current={currentStep} className="generation-steps">
                <Step title="解析讲稿" icon={<LoadingOutlined />} />
                <Step title="构建结构" />
                <Step title="渲染动画" />
                <Step title="生成PPTX" />
                <Step title="布局优化" />
                <Step title="生成语音" />
                <Step title="生成字幕" />
                <Step title="合成视频" />
                <Step title="完成" icon={videoStatus?.status === 'completed' ? <CheckCircleOutlined /> : null} />
              </Steps>

              <Alert
                message="视频生成中，请耐心等待..."
                description="预计需要5-10分钟，请勿关闭页面"
                type="info"
                showIcon
                style={{ marginTop: 16 }}
              />
            </Card>
          )}

          {/* 视频播放器 */}
          {videoStatus?.status === 'completed' && (
            <>
              <Alert
                message="视频生成成功！"
                description="您可以预览视频或下载相关文件"
                type="success"
                showIcon
                style={{ marginBottom: 24 }}
              />
              {renderVideoPlayer()}
              {renderDownloadSection()}
            </>
          )}

          {/* 未开始状态 */}
          {!generating && !videoStatus && (
            <Card className="start-card">
              <div className="start-content">
                <RocketOutlined className="start-icon" />
                <Title level={3}>准备生成视频</Title>
                <Paragraph>
                  系统将根据您编辑后的讲稿生成完整的教学视频，包括：
                </Paragraph>
                <ul className="feature-list">
                  <li>📊 精美的PPT演示文稿（含动画）</li>
                  <li>🎨 Manim代码/公式动画</li>
                  <li>🎤 自然流畅的语音讲解</li>
                  <li>📝 精准对齐的字幕</li>
                  <li>🎬 最终合成的完整视频</li>
                </ul>
                <Button
                  type="primary"
                  size="large"
                  icon={<RocketOutlined />}
                  onClick={handleGenerateVideo}
                  loading={loading}
                  className="start-button"
                >
                  开始生成视频
                </Button>
                <Text type="secondary" className="estimate-time">
                  预计耗时：5-10分钟
                </Text>
              </div>
            </Card>
          )}
        </Content>
      </Layout>
    </div>
  );
}

export default Step5Video;

