
import React from 'react';
import { UserConsumption, ToolId } from '../../types/types';
import { TOOL_CONFIG } from '../../constants/usage';

interface UserBreakdownTableProps {
  users: UserConsumption[];
}

const UserBreakdownTable: React.FC<UserBreakdownTableProps> = ({ users }) => {
  const toolIds = [
    ToolId.RICERCA_DOCUMENTALE,
    ToolId.DRAFT_DOCUMENT,
    ToolId.CHECK_COMPLIANCE,
    ToolId.CHAT_ASSISTANT,
    ToolId.NEWSLETTER_PILL,
    ToolId.SEGRETERIA_SOCIETARIA
  ];

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-[#F8FAFC] border-b border-gray-100">
              <th className="px-6 py-4 text-[10px] font-black text-gray-400 uppercase tracking-[0.2em]">Utente</th>
              {toolIds.map(id => (
                <th key={id} className="px-6 py-4 text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] text-right">
                  {TOOL_CONFIG[id]?.name.split(' ')[0]}
                </th>
              ))}
              <th className="px-6 py-4 text-[10px] font-black text-[#172554] uppercase tracking-[0.2em] text-right">Totale</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {users.map(user => {
              const total = (Object.values(user.counts) as number[]).reduce<number>((a, b) => a + (Number(b) || 0), 0);
              return (
                <tr key={user.userId} className="hover:bg-[#F1F5F9]/50 transition-colors group">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-[#172554] text-white flex items-center justify-center text-[10px] font-black">
                        {user.userName.charAt(0)}
                      </div>
                      <div>
                        <p className="text-sm font-black text-[#172554]">{user.userName}</p>
                        <p className="text-[10px] text-gray-400 font-medium">{user.userEmail}</p>
                      </div>
                    </div>
                  </td>
                  {toolIds.map(id => (
                    <td key={id} className="px-6 py-4 text-right text-sm text-gray-500 font-medium">
                      {Number(user.counts[id]) || 0}
                    </td>
                  ))}
                  <td className="px-6 py-4 text-right text-sm font-black text-[#1F3A8B]">
                    {total}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default UserBreakdownTable;
