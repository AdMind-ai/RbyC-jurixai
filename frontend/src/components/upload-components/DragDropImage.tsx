
import React, { useState } from 'react';
import { Box, Typography } from '@mui/material';
import HighlightOffOutlinedIcon from '@mui/icons-material/HighlightOffOutlined';




const ACCEPTED_FILE_EXTENSIONS = [
  '.jpg', '.png', '.jpeg'
];

interface DragDropImageProps {
    onFileUpload: (file: File) => void;
    onFileDelete: () => void;
    image:  File | null;
   }
 

const DragDropImage: React.FC<DragDropImageProps> = ({ onFileUpload, onFileDelete, image}) => {
  const [dragOver, setDragOver] = useState<boolean>(false);
  const [url, setUrl] =  useState<string>('');
  const [img, setImg] = useState<File | null>(image);

  React.useEffect(() => {
    setImg(image);
    setUrl(image ? URL.createObjectURL(image) : '');
  }, [image]);
  
  const handleFileDelete = () => {
    setUrl('');
    setImg(null);
    onFileDelete();
  };

  const handleFileUpload = (file: File) => {
    const reader = new FileReader();
    reader.onload = () => {
      onFileUpload(file);
    };
    reader.readAsText(file);
  };
  
  const handleFilesUpload = (file: File) => {

    const fileExtension = `.${file.name.split('.').pop()?.toLowerCase()}`;
      
    if (ACCEPTED_FILE_EXTENSIONS.includes(fileExtension)) {
      setUrl(URL.createObjectURL(file));
      handleFileUpload(file);
    } else {
      alert(`Tipo di file non supportato (${fileExtension}): ${file.name}`);
    }
    
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
  
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleFilesUpload(files[0]);
    }
  };


  const openFileSelector = () => {
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = ACCEPTED_FILE_EXTENSIONS.join(',');
    fileInput.multiple = true;
    fileInput.style.display = 'none';
  
    fileInput.onchange = (event) => {
      const target = event.target as HTMLInputElement;
      const files = target.files;
      if (files && files.length > 0) {
        handleFilesUpload(files[0]);
      }
    };
  
    document.body.appendChild(fileInput);
    fileInput.click();
    document.body.removeChild(fileInput);
  };

  return (
    <Box
      sx={{
        position: 'relative',
        width: '100%',
        height: '44vh',
        marginTop: '12px',
        padding: '14px',
        textAlign: 'center',
        border: dragOver ? '2px dashed #0072E5' : '2px solid #F2F2F2',
        borderRadius: '2vh',
        backgroundColor: dragOver ? '#f0faff' : '#F2F2F2',
        cursor: !img ? 'pointer' : 'default',
        transition: 'background-color 0.3s, border 0.3s',
        overflow: 'auto',
        boxShadow: `0px 3px 10px rgba(0,0,0,0.1)`
      }}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={(e) => {
        e.preventDefault();
        setDragOver(false);
      }}
      onDrop={handleDrop}
    >
      {dragOver ? (
        <Box sx={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <Typography sx={{ fontSize: '20px', fontWeight: 'bold', color: '#0072E5' }}>
            Rilascia qui i file per caricarli
          </Typography>
          <Typography sx={{ fontSize: '14px', color: '#666', marginTop: '8px' }}>
            Tipi di file supportati: {ACCEPTED_FILE_EXTENSIONS.join(', ')}
          </Typography>
        </Box>
      ) : (
        <>
          {(img === null && !url) && (
            <>
              <Box onClick={openFileSelector} sx={{ height:'100%', display:'flex', flexDirection:'column', justifyContent:'center'}}>
                <Typography sx={{ fontSize: '16px', color: '#666' }}>
                  Vuoi aggiungere um´immagine?
                </Typography>
                <Typography
                  sx={{
                    fontSize: '14px',
                    marginTop: '8px',
                    marginBottom: '4px',
                    textDecoration: 'underline',
                    cursor: 'pointer',
                  }}
                >
                  Caricala o trascinala direttamente qui
                </Typography>
              </Box>
            </>
          )}

          {url && (
            <Box sx={{ position: 'relative', width: '100%', height: '100%' }}>
              <Box
                component="img"
                alt={'selected image'}
                src={url}
                sx={{ width: '100%', objectFit: 'cover', borderRadius: '2vh' }}
              />
              <HighlightOffOutlinedIcon
                onClick={handleFileDelete}
                sx={{
                  position: 'absolute',
                  top: 8,
                  right: 8,
                  color: 'red',
                  background: '#fff',
                  borderRadius: '50%',
                  fontSize: 32,
                  cursor: 'pointer',
                  boxShadow: '0 2px 6px rgba(0,0,0,0.15)'
                }}
                titleAccess="Delete"
              />
            </Box>
          )}
        </>

      )}

    </Box>

  );
};



export default DragDropImage;