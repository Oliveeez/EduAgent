import { useState, useEffect } from 'react';
import { BarChart3 } from 'lucide-react';
import StatisticsPanel from './StatisticsPanel';
import GraphVisualization from './GraphVisualization';
import NodeDetails from './NodeDetails';
import SearchBar from './SearchBar';
import {
  getVisualGraphStats,
  getVisualGraphData,
  getVisualNodeDetail,
} from '../../services/api';

function VisualGraphDashboard({ kgId }) {
  const [stats, setStats] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showStats, setShowStats] = useState(true);
  const [maxLevel, setMaxLevel] = useState(2);

  useEffect(() => {
    fetchStats();
    fetchGraphData();
  }, [maxLevel, kgId]);

  const fetchStats = async () => {
    try {
      const data = await getVisualGraphStats(kgId);
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const fetchGraphData = async () => {
    try {
      setLoading(true);
      const data = await getVisualGraphData(maxLevel, kgId);
      setGraphData(data);
    } catch (error) {
      console.error('Failed to fetch graph data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleNodeClick = async (nodeId) => {
    try {
      const data = await getVisualNodeDetail(nodeId, kgId);
      setSelectedNode(data);
    } catch (error) {
      console.error('Failed to fetch node details:', error);
    }
  };

  const handleSearchResult = (node) => {
    handleNodeClick(node.id);
  };

  return (
    <div className="bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 rounded-2xl p-4">
      <div className="bg-white/10 backdrop-blur-md border border-white/20 shadow-lg rounded-xl mb-4">
        <div className="px-4 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="inline-flex w-3 h-3 rounded-full bg-white/70"></span>
            <h2 className="text-xl font-bold text-white">知识图谱可视化</h2>
          </div>
          <button
            onClick={() => setShowStats(!showStats)}
            className="px-3 py-2 bg-white/20 hover:bg-white/30 rounded-lg text-white transition-colors flex items-center space-x-2"
          >
            <BarChart3 className="w-4 h-4" />
            <span>统计信息</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-3 space-y-4">
          {showStats && stats && <StatisticsPanel stats={stats} />}
          <SearchBar onResultClick={handleSearchResult} kgId={kgId} />

          <div className="bg-white/90 backdrop-blur-md rounded-xl shadow-lg p-4">
            <h3 className="text-lg font-semibold text-gray-800 mb-3">层级过滤</h3>
            <div className="space-y-2">
              {[0, 1, 2, 3, 4].map((level) => (
                <label key={level} className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="radio"
                    name="level"
                    value={level}
                    checked={maxLevel === level}
                    onChange={() => setMaxLevel(level)}
                    className="w-4 h-4 text-indigo-600"
                  />
                  <span className="text-gray-700">
                    {level === 0 ? '仅根节点' : `到 ${level} 级`}
                  </span>
                </label>
              ))}
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="radio"
                  name="level"
                  value="all"
                  checked={maxLevel === null}
                  onChange={() => setMaxLevel(null)}
                  className="w-4 h-4 text-indigo-600"
                />
                <span className="text-gray-700">全部层级</span>
              </label>
            </div>
          </div>
        </div>

        <div className="lg:col-span-6">
          <div className="bg-white/90 backdrop-blur-md rounded-xl shadow-lg p-4 h-[70vh]">
            {loading ? (
              <div className="flex items-center justify-center h-full">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
              </div>
            ) : (
              <GraphVisualization
                data={graphData}
                onNodeClick={handleNodeClick}
                selectedNodeId={selectedNode?.node?.id}
              />
            )}
          </div>
        </div>

        <div className="lg:col-span-3">
          <NodeDetails nodeData={selectedNode} onClose={() => setSelectedNode(null)} />
        </div>
      </div>
    </div>
  );
}

export default VisualGraphDashboard;
