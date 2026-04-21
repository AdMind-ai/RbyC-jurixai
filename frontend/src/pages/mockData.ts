
import { MonthlyReport, ToolId, SubToolId } from '../types/types';

const users = [
  { id: '1', name: 'Marco Rossi', email: 'marco.rossi@studio.it', role: 'Admin' as const },
  { id: '2', name: 'Laura Bianchi', email: 'laura.bianchi@studio.it', role: 'Utente' as const },
  { id: '3', name: 'Giuseppe Verdi', email: 'giuseppe.verdi@studio.it', role: 'Utente' as const },
];

export const getReport = (month: string): MonthlyReport => {
  const toolUsage: MonthlyReport['toolUsage'] = {
    [ToolId.RICERCA_DOCUMENTALE]: { count: 142 },
    [ToolId.DRAFT_DOCUMENT]: { count: 65 },
    [ToolId.CHECK_COMPLIANCE]: { count: 28 },
    [ToolId.CHAT_ASSISTANT]: { count: 540 },
    [ToolId.SEGRETERIA_SOCIETARIA]: {
      count: 145,
      subItems: {
        [SubToolId.DOCUMENTI_AI]: { count: 85 },
        [SubToolId.ASSISTENTE_LEGALE]: { count: 60 },
      },
    },
  };

  const userBreakdown = users.map((u) => {
    const counts = {
      [ToolId.RICERCA_DOCUMENTALE]: Math.floor(Math.random() * 50),
      [ToolId.DRAFT_DOCUMENT]: Math.floor(Math.random() * 20),
      [ToolId.CHECK_COMPLIANCE]: Math.floor(Math.random() * 10),
      [ToolId.CHAT_ASSISTANT]: Math.floor(Math.random() * 200),
      [ToolId.SEGRETERIA_SOCIETARIA]: Math.floor(Math.random() * 50),
    };

    return {
      userId: u.id,
      userName: u.name,
      userEmail: u.email,
      role: u.role,
      isCompanyAdmin: u.role === 'Admin',
      counts,
    };
  });

  const totalRequests = Object.values(toolUsage).reduce((sum, tool) => sum + (tool.count || 0), 0);

  return {
    month,
    monthLabel: month,
    currency: 'EUR',
    totalRequests,
    toolUsage,
    userBreakdown,
  };
};
