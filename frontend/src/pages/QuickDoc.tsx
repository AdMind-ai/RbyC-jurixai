import React, { useState } from "react";
import {
  Box,
  Button,
  Divider,
  TextField,
  Typography,
  IconButton,
  Menu,
  MenuItem,
} from "@mui/material";
import Layout from "../layouts/Layout";
import CircularProgress from '@mui/material/CircularProgress';
import textIcon from '../assets/icons/word-icon.svg';
import LinedDropdown from "../components/dropdowns/LinedDropdown";
import SaveCleanButtons from "../components/buttons/SaveCleanButtons";
import downloadIcon from '../assets/icons/download-icon.svg';
import { api } from '../api/api';
import { toast } from 'react-toastify';


const QuickDoc: React.FC = () => {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);

  const [documentFormat, setDocumentFormat] = useState<string | string[]>("");
  const [targetLanguage, setTargetLanguage] = useState<string | string[]>("");

  const [text, setText] = useState<string>("");
  const [isGenerated, setIsGenerated] = useState(false);
  const isButtonEnabled = text.length > 0 && documentFormat && targetLanguage

  const [generatedDoc, setGeneratedDoc] = useState<
    | null
    | {
      name: string;
      date: string;
      type: string[];
      text: string;
      urls: { pdf?: string; word?: string };
    }
  >(null);

  const handleDownload = (type: 'pdf' | 'word') => {
    if (generatedDoc?.urls[type]) {
      window.open(generatedDoc.urls[type], "_blank");
    } else {
      toast.error("Formato não disponível.");
    }
    setAnchorEl(null);
  };

  const handleGenerate = async () => {
    setIsLoading(true);
    try {
      const res = await api.post('/quickdoc/generate/', {
        format: documentFormat,
        language: targetLanguage,
        instructions: text,
      });
      setGeneratedDoc(res.data);
      setIsGenerated(true);
      toast.success("Document Generated!");
    } catch (e) {
      toast.error("Error generating document. Please try again.");
      console.error("Error generating document:", e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewExtract = () => {
    setDocumentFormat("");
    setTargetLanguage("");
    setIsGenerated(false);
    setText("");
  };

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
            display: 'flex',
            justifyContent: 'space-between',
            marginBottom: '0.2vw',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <Typography variant="h2" sx={{ marginLeft: '1vw' }}>
              QuickDoc Creator
            </Typography>
          </Box>

          {isGenerated && <SaveCleanButtons onClean={() => handleNewExtract()} disguise_save={true}></SaveCleanButtons>}

        </Box>
        <Divider />

        {/* Boxes */}
        <Box
          sx={{ mt: 3, display: 'flex', flexDirection: 'column', width: '100%', height: '100%', gap: 1.5 }}
        >

          {/* Selects */}
          <Box
            sx={{ display: "flex", flexDirection: "row", gap: 2 }}
          >
            <LinedDropdown
              title="Format del documento"
              options={[
                "Report",
                "Memo"
              ]}
              value={documentFormat}
              onChange={setDocumentFormat}
              width={225}
            />
            <LinedDropdown
              title="Lingua del testo originale"
              options={[
                "Italiano",
                "Inglese",
                "Francese",
                "Spagnolo",
                "Tedesco",
                "Portoghese",
                "Russo",
                "Cinese",
              ]}
              value={targetLanguage}
              onChange={setTargetLanguage}
              width={225}
            />

          </Box>

          <TextField
            multiline
            rows={12}
            placeholder="Scrivi il tuo testo qui"
            value={text}
            onChange={e => setText(e.target.value)}
            sx={{ flex: 1 }}
          >
          </TextField>

          {isGenerated && generatedDoc && (
            <Box sx={{ position: 'relative', width: '100%' }}>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  bgcolor: "#F4F2F2",
                  borderRadius: "10px",
                  border: '1px solid #CBCBCB',
                  py: 1,
                  pl: 2,
                  pr: 1.2,
                  mb: 1,
                  fontSize: "1em",
                  width: '100%',
                  height: '50px',
                }}
              >
                <Typography sx={{ fontWeight: 500, mr: 0.4, display: 'flex', alignItems: 'center', gap: 0.5, fontSize: '16px' }}>
                  <img src={textIcon} alt="Word" style={{ width: 14, marginRight: 8 }} />
                  {generatedDoc.name}_{generatedDoc.date}
                </Typography>
                <IconButton
                  aria-label="download"
                  sx={{ ml: 'auto' }}
                  onClick={e => setAnchorEl(e.currentTarget)}
                >
                  <img src={downloadIcon} alt="Download" style={{ height: '20px' }} />
                </IconButton>
                <Menu
                  anchorEl={anchorEl}
                  open={open}
                  onClose={() => setAnchorEl(null)}
                  slotProps={{ paper: { sx: { borderRadius: "10px" } } }}
                  anchorOrigin={{
                    vertical: 'bottom',
                    horizontal: 'center',
                  }}
                >
                  <MenuItem onClick={() => handleDownload('word')} sx={{ fontSize: '14px' }}>Word</MenuItem>
                  <MenuItem onClick={() => handleDownload('pdf')} sx={{ fontSize: '14px' }}>PDF</MenuItem>
                </Menu>
              </Box>
            </Box>
          )}

          <Box
            sx={{
              display: "flex",
              justifyContent: "center",
              flex: 1,
              // bgcolor:'red'
            }}>
            <Button
              disabled={!isButtonEnabled || isLoading}
              variant="contained"
              onClick={handleGenerate}
              sx={{ width: '120px', mt: 1 }}
            >
              {isLoading ? <CircularProgress size={24} color="inherit" /> : 'Genera'}
            </Button>
          </Box>


        </Box>
      </Box>
    </Layout>
  );
};

export default QuickDoc;