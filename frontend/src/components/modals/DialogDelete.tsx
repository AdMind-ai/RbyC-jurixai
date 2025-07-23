import { Box, Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Typography } from "@mui/material";
import ClearIcon from '@mui/icons-material/Clear';

interface DialogDeleteInterface {
    open: boolean;
    onClose: () => void;
    onConfirm: () => void;
    title: string;
    text: string;
    subText: string;
    textButton: string;
}

const DialogDelete = ({open, onClose, onConfirm, title, text, subText, textButton}:DialogDeleteInterface)=> {

    return (
        <Dialog  open={open} onClose={onClose} aria-labelledby="alert-dialog-title" aria-describedby="alert-dialog-description">
            <Box sx={{padding: '15px', position: 'relative'}}>
                <ClearIcon sx={{position: 'absolute', top: '15px', right: '15px', cursor: 'pointer', color:'#707070'}} onClick={onClose} />
                <DialogTitle id="alert-dialog-title" sx={{display: 'flex', flexDirection: 'row', justifyContent: 'center', alignItems: 'center', fontWeight:'bold'}}>
                    {title}
                </DialogTitle>
                <DialogContent>
                <DialogContentText id="alert-dialog-description" sx={{display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center'}}>
                    <Typography  sx={{fontSize:'13pt', color:'#000'}} >
                        {text}
                    </Typography>
                    <Typography  sx={{fontSize:'13pt', color:'#000'}} >
                        {subText}
                    </Typography>
                </DialogContentText>
                </DialogContent>
                <DialogActions sx={{display: 'flex', flexDirection: 'row', justifyContent: 'center', alignItems: 'center'}}>
                    <Button 
                            autoFocus
                            onClick={onConfirm}
                            variant="contained"
                            sx={{
                                alignSelf: 'flex-end',
                                mt: '15px',
                                flexDirection: 'column',
                                marginRight: '10px',
                                backgroundColor: '#de0606',
                                '&:hover': {
                                    backgroundColor: '#a30404',
                                }
                            }}
                            >
                            {textButton}
                    </Button>
                </DialogActions>
            </Box>
      </Dialog>
    )
}


export default DialogDelete