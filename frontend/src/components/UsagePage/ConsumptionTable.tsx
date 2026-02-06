
import React, { useState, useMemo } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { ToolId, SubToolId, MonthlyReport } from '../../types/types';
import { TOOL_CONFIG, METRIC_LABELS, formatEuro } from '../../constants/usage';

interface ConsumptionTableProps {
  report: MonthlyReport;
}

const ConsumptionTable: React.FC<ConsumptionTableProps> = ({ report }) => {
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  const toggleRow = (id: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedRows(newExpanded);
  };

  const getToolData = (id: ToolId | SubToolId) => {
    if (id === SubToolId.DOCUMENTI_AI || id === SubToolId.ASSISTENTE_LEGALE) {
      return report.toolUsage[ToolId.SEGRETERIA_SOCIETARIA]?.subItems?.[id];
    }
    return report.toolUsage[id as ToolId];
  };

  const sortedTools = useMemo(() => {
    const tools = [
      ToolId.RICERCA_DOCUMENTALE,
      ToolId.DRAFT_DOCUMENT,
      ToolId.CHECK_COMPLIANCE,
      ToolId.CHAT_ASSISTANT,
      SubToolId.DOCUMENTI_AI,
      SubToolId.ASSISTENTE_LEGALE
    ];
    
    return tools.sort((a, b) => {
      const costA = getToolData(a)?.cost || 0;
      const costB = getToolData(b)?.cost || 0;
      return costB - costA;
    });
  }, [report]);

  return (
    <div className="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden font-sans">
      <table className="w-full border-collapse table-fixed">
        <thead>
          <tr className="bg-gray-50/50 border-b border-gray-100">
            <th className="w-[40%] px-8 py-5 text-left text-sm font-normal text-gray-400">Strumento</th>
            <th className="w-[25%] px-8 py-5 text-left text-sm font-normal text-gray-400">Utilizzo</th>
            <th className="w-[20%] px-8 py-5 text-right text-sm font-normal text-gray-400">Costo mensile</th>
            <th className="w-[15%] px-8 py-5 text-center text-sm font-normal text-gray-400"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {sortedTools.map((id) => {
            const data = getToolData(id);
            const config = TOOL_CONFIG[id];
            const isExpanded = expandedRows.has(id);
            const isSubTool = id === SubToolId.DOCUMENTI_AI || id === SubToolId.ASSISTENTE_LEGALE;

            if (!data) return null;

            return (
              <React.Fragment key={id}>
                <tr 
                  className={`hover:bg-gray-50/30 transition-colors cursor-pointer ${isExpanded ? 'bg-gray-50/30' : ''}`}
                  onClick={() => toggleRow(id)}
                >
                  <td className="px-8 py-6">
                    <div className="flex items-center gap-4">
                      <div className="bg-[#EEF2FF] p-2.5 rounded-xl text-[#1F3A8B] shrink-0">
                        {config.icon}
                      </div>
                      <div className="truncate">
                        {isSubTool && (
                          <p className="text-xs font-normal text-[#1F3A8B] opacity-60 mb-0.5 truncate">
                            Segreteria societaria
                          </p>
                        )}
                        <p className="text-base font-bold text-[#172554] truncate">{config.name}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-8 py-6">
                    <div className="flex flex-col text-left">
                      <span className="text-base font-bold text-[#172554]">{data.count}</span>
                      <span className="text-xs font-normal text-gray-400 truncate">
                        {METRIC_LABELS[id] || 'Unità'}
                      </span>
                    </div>
                  </td>
                  <td className="px-8 py-6 text-right">
                    <p className="text-lg font-bold text-[#1F3A8B]">{formatEuro(data.cost)}</p>
                  </td>
                  <td className="px-8 py-6 text-center">
                    <button className="inline-flex items-center gap-2 text-base font-normal text-[#1F3A8B] hover:text-[#172554] transition-colors whitespace-nowrap">
                      {isExpanded ? 'Chiudi' : 'Dettagli'}
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                  </td>
                </tr>
                {isExpanded && (
                  <tr>
                    <td colSpan={4} className="bg-gray-50/50 p-0">
                      <div className="py-6 space-y-3 animate-in slide-in-from-top-2 duration-200">
                        <p className="text-sm font-normal text-gray-400 mb-4 px-8">Dettaglio per utente</p>
                        <div className="px-4 space-y-3">
                          {report.userBreakdown.map((user) => {
                            const toolKey = isSubTool ? ToolId.SEGRETERIA_SOCIETARIA : id;
                            const subToolKey = String(id);
                            const userCost = isSubTool
                              ? user.subToolCosts?.[toolKey]?.[subToolKey] ?? 0
                              : user.costs[toolKey] || 0;
                            const userCount = isSubTool
                              ? user.subToolCounts?.[toolKey]?.[subToolKey] ?? 0
                              : user.counts[toolKey] || 0;
                            return (
                              <div key={user.userId} className="bg-white rounded-xl border border-gray-100/50 shadow-sm overflow-hidden">
                                <div className="grid grid-cols-[40%_25%_20%_15%] items-center">
                                  {/* Info Utente - padding a sinistra calibrato per allineamento con cella 1 */}
                                  <div className="pl-4 pr-4 py-4 flex items-center gap-3">
                                    <div className="w-9 h-9 shrink-0 rounded-full bg-[#1F3A8B]/10 text-[#1F3A8B] flex items-center justify-center font-bold text-xs">
                                      {user.userName.charAt(0)}
                                    </div>
                                    <div className="truncate">
                                      <div className="flex items-center gap-2">
                                        <p className="text-base font-normal text-[#172554] truncate">{user.userName}</p>
                                        <span className={`text-[10px] font-normal px-1.5 py-0.5 rounded shrink-0 ${user.role === 'Admin' ? 'bg-[#1F3A8B] text-white' : 'bg-gray-100 text-gray-400'}`}>
                                          {user.role}
                                        </span>
                                      </div>
                                      <p className="text-[13px] text-gray-400 font-normal truncate">{user.userEmail}</p>
                                    </div>
                                  </div>

                                  {/* Utilizzo Utente - padding calibrato per allineamento con cella 2 */}
                                  <div className="px-4 py-4 text-left">
                                    <p className="text-base font-bold text-[#172554]">{userCount}</p>
                                    <p className="text-[11px] text-gray-400 font-normal leading-tight truncate">
                                      {METRIC_LABELS[id] || 'Unità'}
                                    </p>
                                  </div>

                                  {/* Costo Utente - padding calibrato per allineamento con cella 3 */}
                                  <div className="px-4 py-4 text-right">
                                    <p className="text-base font-bold text-[#1F3A8B]">
                                      {formatEuro(userCost)}
                                    </p>
                                  </div>

                                  {/* Spazio vuoto per allineamento con colonna Azioni */}
                                  <div className="px-4 py-4"></div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default ConsumptionTable;
