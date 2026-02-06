
import { MonthlyReport, ToolId, SubToolId } from '../types/types';

const users = [
  { id: '1', name: 'Marco Rossi', email: 'marco.rossi@studio.it', role: 'Admin' as const },
  { id: '2', name: 'Laura Bianchi', email: 'laura.bianchi@studio.it', role: 'Utente' as const },
  { id: '3', name: 'Giuseppe Verdi', email: 'giuseppe.verdi@studio.it', role: 'Utente' as const },
];

export const getReport = (month: string): MonthlyReport => {
  const toolUsage: MonthlyReport['toolUsage'] = {
    [ToolId.RICERCA_DOCUMENTALE]: { cost: 124.5, count: 142 },
    [ToolId.DRAFT_DOCUMENT]: { cost: 89.2, count: 65 },
    [ToolId.CHECK_COMPLIANCE]: { cost: 156, count: 28 },
    [ToolId.CHAT_ASSISTANT]: { cost: 45.3, count: 540 },
    [ToolId.SEGRETERIA_SOCIETARIA]: {
      cost: 70.6,
      count: 145,
      subItems: {
        [SubToolId.DOCUMENTI_AI]: { cost: 42.1, count: 85 },
        [SubToolId.ASSISTENTE_LEGALE]: { cost: 28.5, count: 60 },
      },
    },
  };

  const userBreakdown = users.map((u) => {
    const costs = {
      [ToolId.RICERCA_DOCUMENTALE]: +(Math.random() * 50).toFixed(2),
      [ToolId.DRAFT_DOCUMENT]: +(Math.random() * 30).toFixed(2),
      [ToolId.CHECK_COMPLIANCE]: +(Math.random() * 60).toFixed(2),
      [ToolId.CHAT_ASSISTANT]: +(Math.random() * 15).toFixed(2),
      [ToolId.SEGRETERIA_SOCIETARIA]: +(Math.random() * 40).toFixed(2),
    };
    const counts = {
      [ToolId.RICERCA_DOCUMENTALE]: Math.floor(Math.random() * 50),
      [ToolId.DRAFT_DOCUMENT]: Math.floor(Math.random() * 20),
      [ToolId.CHECK_COMPLIANCE]: Math.floor(Math.random() * 10),
      [ToolId.CHAT_ASSISTANT]: Math.floor(Math.random() * 200),
      [ToolId.SEGRETERIA_SOCIETARIA]: Math.floor(Math.random() * 50),
    };
    const totalCost = Object.values(costs).reduce((sum, value) => sum + value, 0);

    return {
      userId: u.id,
      userName: u.name,
      userEmail: u.email,
      role: u.role,
      isCompanyAdmin: u.role === 'Admin',
      costs,
      counts,
      totalCost,
    };
  });

  const totalCost = Object.values(toolUsage).reduce((sum, tool) => sum + (tool.cost || 0), 0);
  const totalRequests = Object.values(toolUsage).reduce((sum, tool) => sum + (tool.count || 0), 0);

  return {
    month,
    monthLabel: month,
    currency: 'EUR',
    totalCost,
    totalRequests,
    toolUsage,
    userBreakdown,
  };
};
