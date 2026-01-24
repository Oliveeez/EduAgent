import { useRef, useEffect, useState } from 'react';
import * as d3 from 'd3';
import ForceGraph2D from 'react-force-graph-2d';

function GraphVisualization({ data, onNodeClick, selectedNodeId }) {
  const containerRef = useRef();
  const graphRef = useRef();
  const didZoomToFitRef = useRef(false);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [hoverNodeId, setHoverNodeId] = useState(null);

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth - 32,
          height: containerRef.current.clientHeight - 32,
        });
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  useEffect(() => {
    if (!graphRef.current) {
      return;
    }
    const linkForce = graphRef.current.d3Force('link');
    if (linkForce) {
      linkForce.distance(50);
    }
    const chargeForce = graphRef.current.d3Force('charge');
    if (chargeForce) {
      chargeForce.strength(-220);
    }
    graphRef.current.d3Force(
      'collide',
      d3.forceCollide((node) => getNodeSize(node) + 6)
    );
    didZoomToFitRef.current = false;
  }, [data]);

  if (!data || !data.nodes || data.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        <div className="text-center">
          <p className="text-lg mb-2">暂无数据</p>
          <p className="text-sm">请检查数据源或调整层级过滤</p>
        </div>
      </div>
    );
  }

  const getNodeColor = (node) => {
    const level = node.level || 0;
    const colors = [
      '#3b82f6',
      '#10b981',
      '#f59e0b',
      '#f97316',
      '#ef4444',
    ];
    return colors[Math.min(level, colors.length - 1)];
  };

  const getNodeSize = (node) => {
    const level = node.level || 0;
    const sizes = [30, 15, 12, 10, 8];
    return sizes[Math.min(level, sizes.length - 1)];
  };

  const handleNodeClick = (node) => {
    if (onNodeClick) {
      onNodeClick(node.id);
    }
  };

  const shouldShowLabel = (node, globalScale) => {
    if (hoverNodeId === node.id) {
      return true;
    }
    if (selectedNodeId === node.id) {
      return true;
    }
    if ((node.level || 0) <= 1 && globalScale < 1.4) {
      return true;
    }
    return globalScale >= 1.4;
  };

  return (
    <div className="w-full h-full" ref={containerRef}>
      <ForceGraph2D
        ref={graphRef}
        graphData={data}
        nodeId="id"
        nodeLabel={(node) => `${node.title}\n(Level ${node.level})`}
        nodeColor={(node) => {
          if (selectedNodeId === node.id) {
            return '#8b5cf6';
          }
          return getNodeColor(node);
        }}
        nodeVal={getNodeSize}
        nodeRelSize={4}
        linkDirectionalArrowLength={6}
        linkDirectionalArrowRelPos={1}
        linkCurvature={0.1}
        linkColor={() => 'rgba(0, 0, 0, 0.2)'}
        onNodeClick={handleNodeClick}
        onNodeHover={(node) => {
          setHoverNodeId(node ? node.id : null);
        }}
        width={dimensions.width}
        height={dimensions.height}
        cooldownTicks={100}
        onEngineStop={() => {
          if (graphRef.current && !didZoomToFitRef.current) {
            graphRef.current.zoomToFit(400, 20);
            didZoomToFitRef.current = true;
          }
        }}
        nodeCanvasObject={(node, ctx, globalScale) => {
          const label = node.title || node.id;
          const fontSize = 12 / globalScale;
          ctx.font = `${fontSize}px Sans-Serif`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillStyle = '#333';

          const size = getNodeSize(node);
          const color = selectedNodeId === node.id ? '#8b5cf6' : getNodeColor(node);

          ctx.beginPath();
          ctx.arc(node.x, node.y, size, 0, 2 * Math.PI, false);
          ctx.fillStyle = color;
          ctx.fill();
          ctx.strokeStyle = selectedNodeId === node.id ? '#6366f1' : '#fff';
          ctx.lineWidth = 2 / globalScale;
          ctx.stroke();

          if (shouldShowLabel(node, globalScale)) {
            const textWidth = ctx.measureText(label).width;
            const bckgDimensions = [textWidth, fontSize].map((n) => n + fontSize * 0.2);
            ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
            ctx.fillRect(
              node.x - bckgDimensions[0] / 2,
              node.y + size + 2,
              ...bckgDimensions
            );

            ctx.fillStyle = '#333';
            ctx.fillText(label, node.x, node.y + size + fontSize / 2 + 2);
          }
        }}
        nodePointerAreaPaint={(node, color, ctx) => {
          ctx.fillStyle = color;
          const size = getNodeSize(node);
          ctx.beginPath();
          ctx.arc(node.x, node.y, size + 5, 0, 2 * Math.PI, false);
          ctx.fill();
        }}
      />
    </div>
  );
}

export default GraphVisualization;
