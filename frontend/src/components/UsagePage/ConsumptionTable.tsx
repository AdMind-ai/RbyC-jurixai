
import React, { useState, useMemo } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { ToolId, SubToolId, MonthlyReport } from '../../types/types';
import { TOOL_CONFIG, METRIC_LABELS } from '../../constants/usage';

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
      const countA = getToolData(a)?.count || 0;
      const countB = getToolData(b)?.count || 0;
      return countB - countA;
    });
  }, [report]);

  const integrationBreakdown = report.integrationBreakdown || [];

  const getUserCountForTool = (toolId: ToolId | SubToolId, user: MonthlyReport['userBreakdown'][number]) => {
    const isSubTool = toolId === SubToolId.DOCUMENTI_AI || toolId === SubToolId.ASSISTENTE_LEGALE;
    const toolKey = isSubTool ? ToolId.SEGRETERIA_SOCIETARIA : toolId;
    const subToolKey = String(toolId);
    return isSubTool
      ? user.subToolCounts?.[toolKey]?.[subToolKey] ?? 0
      : user.counts[toolKey] || 0;
  };

  return (
    <div className="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden font-sans">
      <table className="w-full border-collapse table-fixed">
        <thead>
          <tr className="bg-gray-50/50 border-b border-gray-100">
            <th className="w-[55%] px-8 py-5 text-left text-sm font-normal text-gray-400">Strumento</th>
            <th className="w-[30%] px-8 py-5 text-left text-sm font-normal text-gray-400">Interazioni</th>
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
                  <td className="px-8 py-6 text-center">
                    <button className="inline-flex items-center gap-2 text-base font-normal text-[#1F3A8B] hover:text-[#172554] transition-colors whitespace-nowrap">
                      {isExpanded ? 'Chiudi' : 'Dettagli'}
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                  </td>
                </tr>
                {isExpanded && (
                  <tr>
                    <td colSpan={3} className="bg-gray-50/50 p-0">
                      <div className="py-6 space-y-3 animate-in slide-in-from-top-2 duration-200">
                        <p className="text-sm font-normal text-gray-400 mb-4 px-8">Dettaglio per utente</p>
                        <div className="px-4 space-y-3">
                          {report.userBreakdown
                            .filter((user) => getUserCountForTool(id, user) > 0)
                            .map((user) => {
                            const userCount = getUserCountForTool(id, user);
                            return (
                              <div key={user.userId} className="bg-white rounded-xl border border-gray-100/50 shadow-sm overflow-hidden">
                                <div className="grid grid-cols-[55%_30%_15%] items-center">
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

                                  {/* Interazioni utente - padding calibrato per allineamento con cella 2 */}
                                  <div className="px-4 py-4 text-left">
                                    <p className="text-base font-bold text-[#172554]">{userCount}</p>
                                    <p className="text-[11px] text-gray-400 font-normal leading-tight truncate">
                                      {METRIC_LABELS[id] || 'Unità'}
                                    </p>
                                  </div>

                                  {/* Spazio vuoto per allineamento con colonna Azioni */}
                                  <div className="px-4 py-4"></div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                        {integrationBreakdown.length > 0 && (
                          <>
                            <p className="text-sm font-normal text-gray-400 mb-4 px-8 pt-2">Dettagli dell'API di integrazione</p>
                            <div className="px-4 space-y-3">
                              {integrationBreakdown.map((integration) => {
                                const toolKey = isSubTool ? ToolId.SEGRETERIA_SOCIETARIA : id;
                                const integrationCount = integration.counts[toolKey] || 0;

                                if (!integrationCount) return null;

                                return (
                                  <div key={`${id}-${integration.clientId ?? integration.clientName}`} className="bg-white rounded-xl border border-gray-100/50 shadow-sm overflow-hidden">
                                    <div className="grid grid-cols-[55%_30%_15%] items-center">
                                      <div className="pl-4 pr-4 py-4">
                                        <p className="text-base font-normal text-[#172554] truncate">{integration.clientName}</p>
                                        <p className="text-[13px] text-gray-400 font-normal truncate">
                                          {integration.customerCode || 'integrazione legacy'}
                                        </p>
                                      </div>
                                      <div className="px-4 py-4 text-left">
                                        <p className="text-base font-bold text-[#172554]">{integrationCount}</p>
                                        <p className="text-[11px] text-gray-400 font-normal leading-tight truncate">
                                          {METRIC_LABELS[id] || 'UnitÃ '}
                                        </p>
                                      </div>
                                      <div className="px-4 py-4"></div>
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </>
                        )}
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
