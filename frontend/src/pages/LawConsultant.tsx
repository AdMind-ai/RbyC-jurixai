import React from 'react'
import { Link } from 'react-router-dom'
import { Box, Typography } from '@mui/material'
import Layout from '../layouts/Layout'
import LawReferences from '../components/LawConsultantPage/LawReferences'
import ConsultantCard from '../components/cards/ConsultantCard'
import KeyboardArrowRightRoundedIcon from '@mui/icons-material/KeyboardArrowRightRounded';
import { useGlobal } from '../context/GlobalContext';

const cards = [
  {
    title: 'Law References',
    description:
    'Conduce ricerche e analisi sul mercato di riferimento dei principali competitors e sui peers quotati sui capital markets internazionali.',
  },
  {
    title: 'Answer Generation',
    description:
    'Traduce in molteplici lingue investor presentation, trascrive webcast, prepara investor speech e crea contenuti social rapidamente grazie all’AI.',
  },
  {
    title: 'Evaluator',
    description:
    'Monitora e analizza la percezione online del CEO e dei key manager aziendali attraverso la potenza dell’AI.',
  },
  {
    title: 'Rerank',
    description:
      'Assistente virtuale rapido, sicuro e totalmente privato per ottenere risposte immediatamente anche su informazioni price sensitive non ancora pubbliche.',
  },
  {
    title: 'Filter Prompt',
    description:
      'Offre una selezione delle notizie più rilevanti in ambito ESG, organizzate in diverse categorie, per garantire aggiornamenti costantei e puntuali.',
  },
]

const LawConsultant: React.FC = () => {
  const { selectedLawTab, setSelectedLawTab } = useGlobal();

  return (
    <Layout>
      <Box
        sx={{
        display: 'flex',
        flexDirection: 'column',
        padding: '2.2vh 3vh',
        overflow: 'auto',
        height: '100%',
        width: '100%',
        }}
      >   
        {/* Header */}
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            marginBottom: "0.2vw",
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 3 }}>
            {selectedLawTab ? (
              <Box sx={{ display:'flex', gap:1, alignItems:'center'}}>
                <Link 
                  to="/law-consultant" 
                  onClick={() => setSelectedLawTab('')}
                  style={{ textDecoration: 'underline', textDecorationColor: 'inherit' }} 
                >
                  <Typography 
                    variant="h4" 
                    sx={{ 
                      marginLeft: "1vw", 
                      color: 'text.secondary', 
                      fontWeight: 400,
                      textDecoration: 'underline',
                      textDecorationColor: 'inherit', 
                      '&:hover': {
                        textDecoration: 'underline',
                        textDecorationColor: theme => theme.palette.text.secondary,
                      }
                    }}
                  >
                    Law consultant
                  </Typography>
                </Link>
                <KeyboardArrowRightRoundedIcon fontSize="medium" />
                <Typography variant="h4" >
                  {selectedLawTab}
                </Typography>
              </Box>
            ) : (
              <Typography variant="h4" sx={{ marginLeft: "1vw" }}>
                Law consultant
              </Typography>
            )}
          </Box>
        </Box>   
        
        {/* Main Content */}
        {selectedLawTab === null ? (
          <Box 
            sx={{
              flex:1,
              overflow: 'auto',
              display: 'flex',
              justifyContent: 'center',
              marginTop: '1rem',
              height: '100%',
              width: '100%',
            }}
          >
            <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              height: '100%',
              width: '70%',
            }}
            >
              <Typography variant="body1" sx={{textAlign: 'center', padding:'0px 0px', paddingTop:'1vh'}}>
                Seleziona il tipo di chat che vuoi utilizzare
              </Typography>
              <Box
                sx={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  justifyContent: 'center',
                  padding: 'calc(2vh) calc(7vh) calc(4vh) calc(7vh)',
                  height: '75%',
                  width: '100%',
                }}
                >
                {cards.map((card, index) => (
                  <Box key={index} sx={{padding:'15px 15px'}}>
                    <ConsultantCard
                      title={card.title}
                      description={card.description}
                      onClick={() => setSelectedLawTab(card.title)}
                    />
                  </Box>
                ))}
              </Box>
            </Box>
          </Box>
        ):(
          selectedLawTab === "Law References" && <LawReferences/>
          // ou
          // selectedLawTab === "Answer Generation" && <AnswerGeneration />
        )}
      </Box>
    </Layout>
  )
}

export default LawConsultant