import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
// import SaveIcon from '@mui/icons-material/Save';
import CleaningServicesOutlinedIcon from '@mui/icons-material/CleaningServicesOutlined';

interface SaveCleanButtonsProps {
  onSave?: () => void;
  onClean?: () => void;
  disguise_save?: boolean;
  disguise_clean?: boolean;
}

const SaveCleanButtons: React.FC<SaveCleanButtonsProps> = ({ onSave, onClean, disguise_save = false, disguise_clean = false }) => {
  return (
    <Stack direction="row" spacing={0}>
      {!disguise_save && (
        <Button
          variant="text"
          onClick={onSave}
          // startIcon={<SaveIcon sx={{ height: '2vh', width: '1.8vh' }} /> }
          sx={{ color: '#1DB102', height: '3vh', width: '5vw', fontSize: '1vw', fontWeight: 400 }}
        >
          Salva
        </Button>
      )}
      {!disguise_clean && (
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