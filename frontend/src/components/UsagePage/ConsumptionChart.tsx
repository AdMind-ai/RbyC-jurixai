
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { MonthlyReport, ToolId } from '../../types/types';
import { TOOL_CONFIG } from '../../constants/usage';

interface ConsumptionChartProps {
  report: MonthlyReport;
}

interface ChartTooltipPayload {
  value: number;
  payload: {
    fullName: string;
  };
}

interface ChartTooltipProps {
  active?: boolean;
  payload?: ChartTooltipPayload[];
}

const ConsumptionChart: React.FC<ConsumptionChartProps> = ({ report }) => {
  // Use report.toolUsage[id].count which correctly exists in the MonthlyReport interface
  const data = Object.values(ToolId).map(id => ({
    name: TOOL_CONFIG[id]?.name.split(' ')[0] || id, // Short name
    fullName: TOOL_CONFIG[id]?.name || id,
    value: report.toolUsage[id]?.count || 0,
    color: TOOL_CONFIG[id]?.color || '#CBD5E1'
  }));

  const CustomTooltip: React.FC<ChartTooltipProps> = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-4 border border-gray-100 shadow-lg rounded-xl">
          <p className="text-xs font-bold text-[#172554] uppercase tracking-wider mb-1">{payload[0].payload.fullName}</p>
          <p className="text-xl font-black text-[#1F3A8B]">{payload[0].value} <span className="text-sm font-normal text-gray-400">interazioni</span></p>
        </div>
      );
    }
    return null;
  };

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        data={data}
        margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
        barGap={8}
      >
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
        <XAxis 
          dataKey="name" 
          axisLine={false} 
          tickLine={false} 
          tick={{ fontSize: 10, fontWeight: 600, fill: '#94A3B8' }}
          dy={10}
        />
        <YAxis 
          axisLine={false} 
          tickLine={false} 
          tick={{ fontSize: 10, fontWeight: 600, fill: '#94A3B8' }}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: '#F8FAFC' }} />
        <Bar 
          dataKey="value" 
          radius={[6, 6, 0, 0]} 
          barSize={40}
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
};

export default ConsumptionChart;
