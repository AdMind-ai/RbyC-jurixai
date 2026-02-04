import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
// import SaveIcon from '@mui/icons-material/Save';
import CleaningServicesOutlinedIcon from '@mui/icons-material/CleaningServicesOutlined';

interface SaveCleanButtonsProps {
  onSave?: () => void | Promise<void>;
  onClean?: () => void | Promise<void>;
  showSave?: boolean;
}

const SaveCleanButtons: React.FC<SaveCleanButtonsProps> = ({ onSave, onClean, showSave }) => {
  return (
    <Stack direction="row" spacing={0}>
      {onSave && (showSave !== false) && (
        <Button
          variant="text"
          onClick={onSave}
          sx={{ color: '#1DB102', height: '3vh', width: '5vw', fontSize: '1vw', fontWeight: 400 }}
        >
          Salva
        </Button>
      )}
      {onClean && (
        <Button
          variant="text"
          onClick={onClean}
          startIcon={<CleaningServicesOutlinedIcon sx={{ height: '2vh', width: '1.8vh' }} />}
          sx={{ color: '#B91F26', height: '3vh', width: '5vw', fontSize: '1vw', fontWeight: 400 }}
        >
          Pulisci
        </Button>
      )}
    </Stack>
  );
};

export default SaveCleanButtons;