
import React from 'react';
import { TOOL_CONFIG } from '../../constants/usage';
import { ToolId, SubToolId } from '../../types/types';
import { MoreHorizontal, ArrowUpRight } from 'lucide-react';

interface ToolCardProps {
  toolId: ToolId;
  usage: number;
  description: string;
  subTools?: { id: SubToolId; usage: number }[];
}

const ToolCard: React.FC<ToolCardProps> = ({ toolId, usage, description, subTools }) => {
  const config = TOOL_CONFIG[toolId];

  return (
    <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm hover:shadow-md transition-shadow flex flex-col group h-full">
      <div className="flex items-start justify-between mb-4">
        <div className="bg-[#F8FAFC] p-3 rounded-xl border border-gray-100 group-hover:bg-blue-50 group-hover:border-blue-100 transition-colors">
          {config.icon}
        </div>
        <button className="p-1 hover:bg-gray-100 rounded-lg transition-colors">
          <MoreHorizontal className="w-5 h-5 text-gray-400" />
        </button>
      </div>

      <h3 className="text-lg font-bold text-[#172554] mb-2">{config.name}</h3>
      <p className="text-sm text-gray-500 leading-relaxed mb-6 flex-grow">
        {description}
      </p>

      {subTools && subTools.length > 0 && (
        <div className="space-y-3 mb-6 bg-gray-50 p-3 rounded-xl">
          {subTools.map(sub => (
            <div key={sub.id} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-[#1F3A8B]"></div>
                <span className="text-xs font-medium text-gray-600">{TOOL_CONFIG[sub.id].name}</span>
              </div>
              <span className="text-xs font-bold text-[#172554]">{sub.usage} <span className="text-[10px] font-normal text-gray-400">usi</span></span>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between pt-6 border-t border-gray-50 mt-auto">
        <div>
          <p className="text-[10px] text-gray-400 uppercase font-semibold tracking-wider">Interazioni Mensili</p>
          <p className="text-2xl font-bold text-[#172554] flex items-baseline gap-1">
            {usage}
            <span className="text-sm font-normal text-gray-500">usi</span>
          </p>
        </div>
        <button className="flex items-center gap-1.5 text-xs font-bold text-[#1F3A8B] hover:text-[#172554] uppercase tracking-wider transition-colors">
          VAI ALLA FUNZIONE
          <ArrowUpRight className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
};

export default ToolCard;
