/**
 * 知识图谱可视化组件
 * 使用D3.js渲染知识图谱
 */

import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

function KnowledgeGraphVisualization({ data }) {
  const svgRef = useRef();

  useEffect(() => {
    if (!data || !data.nodes || !data.edges) {
      return;
    }

    renderGraph();
  }, [data]);

  const renderGraph = () => {
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = 800;
    const height = 600;

    svg.attr('width', width).attr('height', height);

    // 创建力导向图
    const simulation = d3
      .forceSimulation(data.nodes)
      .force('link', d3.forceLink(data.edges).id((d) => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2));

    // 绘制连线
    const link = svg
      .append('g')
      .selectAll('line')
      .data(data.edges)
      .enter()
      .append('line')
      .attr('stroke', '#999')
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', 2);

    // 绘制节点
    const node = svg
      .append('g')
      .selectAll('circle')
      .data(data.nodes)
      .enter()
      .append('circle')
      .attr('r', (d) => d.size || 10)
      .attr('fill', (d) => d.color || '#69b3a2')
      .call(drag(simulation));

    // 添加节点标签
    const label = svg
      .append('g')
      .selectAll('text')
      .data(data.nodes)
      .enter()
      .append('text')
      .text((d) => d.label)
      .attr('font-size', 12)
      .attr('dx', 15)
      .attr('dy', 4);

    // 更新位置
    simulation.on('tick', () => {
      link
        .attr('x1', (d) => d.source.x)
        .attr('y1', (d) => d.source.y)
        .attr('x2', (d) => d.target.x)
        .attr('y2', (d) => d.target.y);

      node.attr('cx', (d) => d.x).attr('cy', (d) => d.y);

      label.attr('x', (d) => d.x).attr('y', (d) => d.y);
    });

    // 拖拽功能
    function drag(simulation) {
      function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      }

      function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
      }

      function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      }

      return d3.drag().on('start', dragstarted).on('drag', dragged).on('end', dragended);
    }
  };

  return (
    <div className="kg-visualization">
      <svg ref={svgRef}></svg>
    </div>
  );
}

export default KnowledgeGraphVisualization;