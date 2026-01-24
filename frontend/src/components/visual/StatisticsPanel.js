import { BarChart3, Layers, FileText, Hash } from 'lucide-react';

function StatisticsPanel({ stats }) {
  if (!stats) return null;

  const statCards = [
    {
      label: '总知识点',
      value: stats.total_nodes,
      icon: Hash,
      color: 'bg-blue-500',
    },
    {
      label: '一级节点',
      value: stats.level_0,
      icon: Layers,
      color: 'bg-green-500',
    },
    {
      label: '二级节点',
      value: stats.level_1,
      icon: Layers,
      color: 'bg-yellow-500',
    },
    {
      label: '三级节点',
      value: stats.level_2,
      icon: Layers,
      color: 'bg-orange-500',
    },
    {
      label: '四级及以上',
      value: stats.level_3 + stats.level_4_plus,
      icon: Layers,
      color: 'bg-red-500',
    },
    {
      label: '包含公式',
      value: stats.has_formulas,
      icon: FileText,
      color: 'bg-purple-500',
    },
    {
      label: '包含要点',
      value: stats.has_key_points,
      icon: FileText,
      color: 'bg-pink-500',
    },
    {
      label: '知识模块',
      value: stats.total_folders,
      icon: BarChart3,
      color: 'bg-indigo-500',
    },
  ];

  return (
    <div className="bg-white/90 backdrop-blur-md rounded-xl shadow-lg p-4">
      <div className="flex items-center space-x-2 mb-4">
        <BarChart3 className="w-5 h-5 text-indigo-600" />
        <h2 className="text-xl font-bold text-gray-800">统计信息</h2>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {statCards.map((card, index) => {
          const Icon = card.icon;
          return (
            <div
              key={index}
              className="bg-gradient-to-br from-white to-gray-50 rounded-lg p-3 shadow-md hover:shadow-lg transition-shadow"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-gray-600 mb-1">{card.label}</p>
                  <p className="text-2xl font-bold text-gray-800">{card.value}</p>
                </div>
                <div className={`${card.color} p-2 rounded-lg`}>
                  <Icon className="w-5 h-5 text-white" />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 pt-4 border-t border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">层级分布</h3>
        <div className="space-y-2">
          {[
            { label: '0级', value: stats.level_0, color: 'bg-blue-500' },
            { label: '1级', value: stats.level_1, color: 'bg-green-500' },
            { label: '2级', value: stats.level_2, color: 'bg-yellow-500' },
            { label: '3级', value: stats.level_3, color: 'bg-orange-500' },
            { label: '4+级', value: stats.level_4_plus, color: 'bg-red-500' },
          ].map((item, index) => {
            const percentage = stats.total_nodes > 0 ? (item.value / stats.total_nodes) * 100 : 0;
            return (
              <div key={index} className="space-y-1">
                <div className="flex justify-between text-xs text-gray-600">
                  <span>{item.label}</span>
                  <span>
                    {item.value} ({percentage.toFixed(1)}%)
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`${item.color} h-2 rounded-full transition-all duration-500`}
                    style={{ width: `${percentage}%` }}
                  ></div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default StatisticsPanel;
