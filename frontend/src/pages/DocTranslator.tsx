import React from 'react'
import {
  Box,
  Divider,
  Typography,
} from '@mui/material'
import Layout from '../layouts/Layout'

// import Traduttore from '../components/DocTranslatorPage/Traduttore'

const Earnings: React.FC = () => {

  return (
    <Layout>
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          padding: '3vh ',
          overflow: 'auto',
          height: '100%',
          width: '100%',
        }}
      >
        {/* Title */}
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            marginBottom: '0.2vw',
          }}
        >
          <Typography variant="h2" sx={{ marginLeft: '1vw' }}>
            Traduttore documenti
          </Typography>

        </Box>

        <Divider />

        {/* Main Content */}
        <Box sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'top', width: '100%', height: '100%', paddingTop: '1.5vw' }} >

          
          {/* Content */}
          {/* <Traduttore /> */}

        </Box>
      </Box>
    </Layout>
  );
};

export default Earnings;