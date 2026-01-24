import { X, ChevronUp, ChevronDown, FileText, Tag, Hash } from 'lucide-react';

function NodeDetails({ nodeData, onClose }) {
  if (!nodeData || !nodeData.node) {
    return (
      <div className="bg-white/90 backdrop-blur-md rounded-xl shadow-lg p-6 h-[calc(100vh-200px)] flex items-center justify-center">
        <div className="text-center text-gray-500">
          <FileText className="w-12 h-12 mx-auto mb-3 text-gray-400" />
          <p>点击节点查看详细信息</p>
        </div>
      </div>
    );
  }

  const { node, parent, children } = nodeData;

  const renderFormulas = (formulas) => {
    if (!formulas || formulas.length === 0) return null;
    return (
      <div className="space-y-2">
        {formulas.map((formula, index) => (
          <div
            key={index}
            className="bg-gray-50 p-3 rounded-lg font-mono text-sm border border-gray-200"
          >
            {formula}
          </div>
        ))}
      </div>
    );
  };

  const renderKeyPoints = (keyPoints) => {
    if (!keyPoints || keyPoints.length === 0) return null;
    return (
      <ul className="space-y-2">
        {keyPoints.map((point, index) => (
          <li key={index} className="flex items-start space-x-2">
            <span className="text-indigo-500 mt-1">•</span>
            <span className="text-gray-700">{point}</span>
          </li>
        ))}
      </ul>
    );
  };

  return (
    <div className="bg-white/90 backdrop-blur-md rounded-xl shadow-lg p-6 h-[calc(100vh-200px)] overflow-y-auto">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-800">节点详情</h2>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <X className="w-5 h-5 text-gray-600" />
        </button>
      </div>

      <div className="mb-4">
        <h3 className="text-2xl font-bold text-indigo-600 mb-2">{node.title}</h3>
        <div className="flex items-center space-x-2 flex-wrap gap-2">
          <span className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-sm font-semibold">
            Level {node.level}
          </span>
          {node.type && (
            <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm">
              {node.type}
            </span>
          )}
          {node.source_folder && (
            <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm">
              {node.source_folder}
            </span>
          )}
        </div>
      </div>

      {node.description && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-gray-600 mb-2 flex items-center">
            <FileText className="w-4 h-4 mr-1" />
            描述
          </h4>
          <p className="text-gray-700 bg-gray-50 p-3 rounded-lg">{node.description}</p>
        </div>
      )}

      {node.formulas && node.formulas.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-gray-600 mb-2 flex items-center">
            <Hash className="w-4 h-4 mr-1" />
            公式
          </h4>
          {renderFormulas(node.formulas)}
        </div>
      )}

      {node.key_points && node.key_points.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-gray-600 mb-2 flex items-center">
            <Tag className="w-4 h-4 mr-1" />
            关键要点
          </h4>
          {renderKeyPoints(node.key_points)}
        </div>
      )}

      {node.tags && node.tags.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-gray-600 mb-2">标签</h4>
          <div className="flex flex-wrap gap-2">
            {node.tags.map((tag, index) => (
              <span
                key={index}
                className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-sm"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      )}

      {parent && (
        <div className="mb-4 border-t pt-4">
          <h4 className="text-sm font-semibold text-gray-600 mb-2 flex items-center">
            <ChevronUp className="w-4 h-4 mr-1" />
            父节点
          </h4>
          <div className="bg-blue-50 p-3 rounded-lg border border-blue-200">
            <p className="font-semibold text-blue-800">{parent.title}</p>
            {parent.description && (
              <p className="text-sm text-blue-600 mt-1 line-clamp-2">
                {parent.description}
              </p>
            )}
            <p className="text-xs text-blue-500 mt-2">Level {parent.level}</p>
          </div>
        </div>
      )}

      {children && children.length > 0 && (
        <div className="border-t pt-4">
          <h4 className="text-sm font-semibold text-gray-600 mb-2 flex items-center">
            <ChevronDown className="w-4 h-4 mr-1" />
            子节点 ({children.length})
          </h4>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {children.map((child) => (
              <div
                key={child.id}
                className="bg-green-50 p-3 rounded-lg border border-green-200 hover:bg-green-100 transition-colors"
              >
                <p className="font-semibold text-green-800">{child.title}</p>
                {child.description && (
                  <p className="text-sm text-green-600 mt-1 line-clamp-2">
                    {child.description}
                  </p>
                )}
                <div className="flex items-center space-x-2 mt-2">
                  <span className="text-xs px-2 py-0.5 bg-green-200 text-green-700 rounded">
                    Level {child.level}
                  </span>
                  {child.type && (
                    <span className="text-xs px-2 py-0.5 bg-gray-200 text-gray-700 rounded">
                      {child.type}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!parent && (!children || children.length === 0) && (
        <div className="text-center text-gray-400 py-4 border-t mt-4">
          <p className="text-sm">无父节点和子节点</p>
        </div>
      )}
    </div>
  );
}

export default NodeDetails;
