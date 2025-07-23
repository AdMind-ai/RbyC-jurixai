import React, {useState} from 'react';
// import React, { useState, useEffect } from 'react';
import { Box, Typography, Divider, LinearProgress  } from '@mui/material'
// import { useTheme } from '@mui/material/styles'
import Layout from '../layouts/Layout'
import LinedDropdown from '../components/dropdowns/LinedDropdown';
// import { api } from '../api/api'


const cardsTitle: CardGroup[] = [
  { key: 'use', label: '' },
];

const cardsMock: Record<string, CardData[]> = {
  use: [
    { title: 'Draft documenti', usage: '40%' },
    { title: 'Ricerca documentale', usage: '1%' },
    { title: 'Check compliance', usage: '84%' },
    { title: 'Traduttore', usage: '12%' },
    { title: 'Law Assistant', usage: '120/240' },
  ],
};

function getUsageValue(usage: string) {
  if (usage.endsWith('%')) {
    const percent = parseFloat(usage.replace('%', ''));
    return { value: percent, isPercent: true, label: usage };
  } else if (usage.includes('/')) {
    const [current, total] = usage.split('/').map(Number);
    const percent = total ? (current / total) * 100 : 0;
    return { value: percent, isPercent: false, label: usage };
  }
  return { value: 0, isPercent: false, label: usage };
}

interface CardData {
  title: string;
  usage: string;
}

interface CardGroup {
  key: string;
  label: string;
}

// interface ApiResponse {
//   [groupKey: string]: CardData[];
// }


const Card: React.FC<CardData> = ({ title, usage }) => {
  const { value, label } = getUsageValue(usage);

  return (
    <Box
      sx={{
        width: '255px',
        border: '1px solid #ddd',
        borderRadius: 2,
        padding: 2,
        boxShadow: '0px 3px 10px rgba(0,0,0,0.1)',
        minHeight: '100px',
        mb: 1,
        background: '#fff',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
      }}
    >
      <Typography variant="subtitle2" mb={1}>
        {title}
      </Typography>
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'bottom', gap: 1 }}>
        <Typography
          variant="subtitle2" fontWeight='bold'
          sx={{ color: '#212121', textAlign: 'right' }}
        >
          {label}
        </Typography>
        <Box sx={{ flex: 1, mb:2 }}>
          <LinearProgress
            variant="determinate"
            value={value}
            sx={{
              height: 15,
              borderRadius: 1.3,
              background: '#eee',
              // '& .MuiLinearProgress-bar': { backgroundColor: '#ED6008' },
            }}
          />
        </Box>
      </Box>
    </Box>
  );
};

const Usage: React.FC = () => {
  // List of months in Italian
  const months = [
    "Gennaio 2025", "Febbraio 2025", "Marzo 2025", "Aprile 2025",
    "Maggio 2025", "Giugno 2025", "Luglio 2025", "Agosto 2025",
    "Settembre 2025", "Ottobre 2025", "Novembre 2025", "Dicembre 2025"
  ];
  const [selectValue, setSelectValue] = useState<string | string[]>('');

  // const theme = useTheme()

  // const [cardsData, setCardsData] = useState<ApiResponse>({});
  // const [loading, setLoading] = useState<boolean>(true);
  // const [error, setError] = useState<string | null>(null);

  // useEffect(() => {
  //   api.get('/usage/') 
  //     .then((response) => {
  //       setCardsData(response.data);
  //     })
  //     .catch((err) => {
  //       setError(err?.message || 'Erro ao carregar dados');
  //     })
  //     .finally(() => setLoading(false));
  // }, []);

  return (

    <Layout>
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          overflow: 'auto',
          height: '100%',
          width: '100%',
        }}
      >
        {/* Header */}
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            marginBottom: '0.2vw',
            padding: 'calc(3vh) calc(3vh) 0 calc(3vh)',
          }}
        >
          <Typography variant="h2" sx={{ marginLeft: '1vw' }}>
          Consumo AI
          </Typography>

        </Box>
        <Divider sx={{mx:'calc(3vh)'}}/>

        {/* Main Content */}
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            height: '100%',
            width: '100%',
            overflow: 'auto',
            px: '4vh',
            py: 1.5
          }}
        >
          
          {/* Cards Group */}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: '6vh', pt:2 }}>
            {cardsTitle.map((group) => (
              <Box key={group.key}>
                <Typography variant="h4" fontWeight="bold" marginLeft={1} marginBottom={1.5}>
                  {group.label}
                </Typography>
                <Box>
                  <Box
                    sx={{
                      display: 'flex',
                      flexDirection: 'row',
                      gap: 2,
                      flexWrap: 'wrap'
                    }}
                  >
                    {(cardsMock[group.key] || []).map((card, idx) => (
                      <Card key={idx} title={card.title} usage={card.usage} />
                    ))}
                  </Box>
                </Box>
              </Box>
            ))}
          </Box>
          
          {/* Selector */}
          <LinedDropdown
            title="Costo extra AI"
            options={months}
            value={selectValue}
            onChange={setSelectValue}
          />
        </Box>
      </Box>
    </Layout>
  )
}

export default Usage
