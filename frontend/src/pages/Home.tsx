import React from 'react'
import { Box, Typography } from '@mui/material'
import Layout from '../layouts/Layout'
import HomeCard from '../components/cards/HomeCard'

// Importação dos ícones
// import TranslatorIcon from '../assets/icons/sidebar/translator-icon.svg'
import ComplianceIcon from '../assets/icons/sidebar/compliance-icon.svg'
// import DraftIcon from '../assets/icons/sidebar/draft-icon.svg'
import SearchIcon from '../assets/icons/sidebar/search-icon.svg'
import ConsultantIcon from '../assets/icons/sidebar/consultant-icon.svg'

const cards = [
  // {
  //   title: 'Draft documenti',
  //   description:
  //   'Conduce ricerche e analisi sul mercato di riferimento dei principali competitors e sui peers quotati sui capital markets internazionali.',
  //   icon: DraftIcon,
  //   path: '/doc-draft',
  // },
  {
    title: 'Ricerca documentale',
    description:
    '',
    icon: SearchIcon,
    path: '/doc-search',
  },
  {
    title: 'Check compliance',
    description:
    '',
    icon: ComplianceIcon,
    path: '/',
  },
  // {
  //   title: 'Traduttore documenti',
  //   description:
  //     'Assistente virtuale rapido, sicuro e totalmente privato per ottenere risposte immediatamente anche su informazioni price sensitive non ancora pubbliche.',
  //   icon: TranslatorIcon,
  //   path: '/doc-translator',
  // },
  {
    title: 'Law consultant',
    description:
      '',
    icon: ConsultantIcon,
    path: '/law-consultant',
  },
]

const Home: React.FC = () => {
  return (
    <Layout>
      <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        overflow: 'auto',
        height: '100%',
        width: '100%',
      }}
      >
        <Typography variant="h3" sx={{textAlign: 'center', padding:'0px 0px', paddingTop:'4vh'}}>
          Cosa vuoi fare oggi?
        </Typography>
        <Box
          sx={{
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'center',
            padding: 'calc(2.5vh) calc(3vh) calc(4vh) calc(3vh)',
            // overflow: 'auto',
            height: '84%',
            width: '100%',
            // backgroundColor: 'blue',
            gap:0.5,
          }}
          >
          {cards.map((card, index) => (
            <Box key={index} sx={{padding:'15px 15px'}}>
              <HomeCard
                title={card.title}
                description={card.description}
                icon={card.icon}
                path={card.path}
                />
            </Box>
          ))}
        </Box>
      </Box>
    </Layout>
  )
}

export default Home
