
import React from 'react';
import { ToolId, SubToolId, ConsumptionStats } from '../../types/types';
import { TOOL_CONFIG, METRIC_LABELS } from '../../constants/usage';

interface ConsumptionCardProps {
  id: ToolId | SubToolId;
  data: ConsumptionStats;
  onOpenDetail?: () => void;
}

const ConsumptionCard: React.FC<ConsumptionCardProps> = ({ id, data, onOpenDetail }) => {
  const config = TOOL_CONFIG[id];
  if (!config || !data) return null;

  // Verifica se è un sotto-strumento della Segreteria Societaria
  const isSubTool = id === SubToolId.DOCUMENTI_AI || id === SubToolId.ASSISTENTE_LEGALE;
  const subtitle = isSubTool ? "Segreteria Societaria" : null;

  return (
    <div className="bg-white border border-gray-100 rounded-2xl p-8 shadow-sm hover:shadow-md transition-all flex flex-col h-full group relative border-opacity-60 font-sans">
      {/* Header: Icona e interazioni in alto a destra */}
      <div className="flex justify-between items-start mb-6">
        <div className="bg-[#EEF2FF] p-4 rounded-2xl text-[#1F3A8B]">
          {config.icon}
        </div>
        <div className="text-right pt-1">
          <p className="text-[10px] font-bold text-gray-400 mb-0.5 lowercase">interazioni</p>
          <p className="text-xl font-black text-[#172554] tracking-tight">
            {data.count}
          </p>
        </div>
      </div>

      {/* Titolo e eventuale Sottotitolo */}
      <div className="mb-8">
        {subtitle && (
          <p className="text-[10px] font-black text-[#1F3A8B] uppercase tracking-[0.15em] mb-1 opacity-70">
            {subtitle}
          </p>
        )}
        <h3 className="text-xl font-extrabold text-[#172554] leading-tight">
          {config.name}
        </h3>
      </div>
      
      {/* Spazio flessibile per mantenere l'allineamento dei tasti in fondo */}
      <div className="flex-grow"></div>

      {/* Fascia Blu in fondo */}
      <div className="flex flex-col gap-4 mt-4">
        <div className="flex items-center justify-between pt-4 border-t border-gray-50">
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 bg-[#187F3D] rounded-full"></div>
            <span className="text-[10px] font-black text-gray-400 uppercase tracking-widest">
              {METRIC_LABELS[id]?.split(' ')[0] || 'Interazioni'}
            </span>
          </div>
          <span className="text-xs font-black text-[#172554]">{data.count} usi</span>
        </div>

        <button 
          onClick={onOpenDetail}
          className="bg-[#1F3A8B] group-hover:bg-[#172554] py-3.5 rounded-xl transition-all duration-300 shadow-sm flex items-center justify-center cursor-pointer border-none w-full"
        >
          <span className="text-white text-[13px] font-normal">
            Consumo per utente
          </span>
        </button>
      </div>
    </div>
  );
};

export default ConsumptionCard;
