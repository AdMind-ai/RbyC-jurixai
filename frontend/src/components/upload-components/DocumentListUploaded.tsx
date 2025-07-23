import React from 'react';
import { Box, List, ListItem, ListItemIcon, ListItemText, Typography } from '@mui/material';
import InsertDriveFileOutlinedIcon from '@mui/icons-material/InsertDriveFileOutlined';
import PictureAsPdfOutlinedIcon from '@mui/icons-material/PictureAsPdfOutlined';
import ArticleOutlinedIcon from '@mui/icons-material/ArticleOutlined';
import ArchiveOutlinedIcon from '@mui/icons-material/ArchiveOutlined';
import CloseIcon from '@mui/icons-material/Close';
import { useTheme } from '@mui/material/styles';
import { saveAs } from 'file-saver';
import { toast } from 'react-toastify'
import { api } from '../../api/api';

interface Document {
  id: number;
  name: string;
  type: string; // pdf, txt, doc, docx, odt, rtf, xls, xlsx
  translatedUrl?: string; 
}

interface DocumentListProps {
  documents: Document[];
  onDelete: (id: number) => void;
  isResult?: boolean; 
  isTranslation?: boolean;
}

const DocumentList: React.FC<DocumentListProps> = ({ documents, onDelete, isResult = false, isTranslation = false }) => {
  const theme = useTheme()
  if (!documents || documents.length === 0) {
    return null; 
  }
  
  const handleOpenProtectedDoc = async (document: Document) => {
    if (!document.translatedUrl) {
      toast.error("Documento tradotto non disponibile.");
      return;
    }
  
    try {
      const response = await api.get(document.translatedUrl, { responseType: 'blob' });
  
      // Usa file-saver para baixar automaticamente:
      saveAs(response.data, document.name);
    } catch (error) {
      console.error("Errore durante il download del documento:", error);
      toast.error("Impossibile scaricare il documento.");
    }
  };

  const getIconForType = (type: string) => {
    switch (type) {
      case 'pdf':
        return <PictureAsPdfOutlinedIcon fontSize="small" />;
      case 'txt':
        return <InsertDriveFileOutlinedIcon fontSize="small" />;
      case 'doc':
      case 'docx':
      case 'odt':
      case 'rtf':
        return <ArticleOutlinedIcon fontSize="small" />;
      case 'xls':
      case 'xlsx':
        return <ArchiveOutlinedIcon fontSize="small" />;
      default:
        return <InsertDriveFileOutlinedIcon fontSize="small" />;
    }
    
  };

  return (
    <Box
      sx={{
        width: '100%',
        maxWidth: '50vw',
        maxHeight: isResult? '42vh':'32vh',
        overflow: 'auto',
        padding: '0px 10px',
        backgroundColor: 'inherit',
      }}
    >
      <List>
        {documents.map((document) => (
          <ListItem
            key={document.id}
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              border: '1px solid #ddd',
              borderRadius: '8px',
              backgroundColor: '#f5f5f5',
              marginBottom: '8px',
              padding: '8px 12px',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              {/* Ícone do Documento */}
              <ListItemIcon sx={{ color: '#666', minWidth: '32px' }}>{getIconForType(document.type)}</ListItemIcon>
              {/* Nome do Documento */}
              <ListItemText
                primary={document.name}
                slotProps={{
                  primary: {
                    sx: {
                      fontSize: '14px',
                      color: '#333',
                      fontWeight: 500,
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      maxWidth: isResult? 500:185, 
                    }
                  }
                }}
              />
            </Box>
            {/* Alternar entre exclusão e link de documento traduzido */}
            {isResult ? (
              isTranslation ? (
                <Typography
                  onClick={() => handleOpenProtectedDoc(document)} 
                  sx={{
                    fontSize: '12px',
                    color: theme.palette.secondary.main,
                    textDecoration: 'underline',
                    cursor: 'pointer',
                    '&:hover': { color: theme.palette.secondary.dark },
                  }}
                >
                  Vai al documento tradotto
                </Typography>
              ) : (
                <></>
              )
            ) : (
              <CloseIcon
                fontSize="small"
                sx={{
                  color: '#666',
                  cursor: 'pointer',
                  '&:hover': { color: '#333' },
                }}
                onClick={() => onDelete(document.id)} 
              />
            )}
          </ListItem>
        ))}
      </List>
    </Box>
  );
};

export default DocumentList;