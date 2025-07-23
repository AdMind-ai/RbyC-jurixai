import { Box, Button, Dialog, DialogContent, DialogTitle, Typography } from "@mui/material"
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs'
import { Dispatch, SetStateAction } from "react";
import { Dayjs } from "dayjs";
interface DialogDateTimeInterface {
    open: boolean;
    onClose: () => void;
    onConfirm: () => void;
    onCancel: () => void;
    datetimeState: {
        value: Dayjs | null;
        set: Dispatch<SetStateAction<Dayjs | null>>;
    };
    textConfirmButton: string;
}
    

const DialogDateTime = ({open, onClose, onConfirm, onCancel, textConfirmButton, datetimeState}:DialogDateTimeInterface)=> {

    return (
        <Dialog open={open} onClose={onClose}>
            <DialogTitle>
                <Typography>
                    Schedule post
                </Typography>
            </DialogTitle>
            <DialogContent>
                <Box sx={{display: 'flex', flexDirection:'row',justifyContent:'center', alignItems: 'center', width: '100%'}}>
                    <LocalizationProvider dateAdapter={AdapterDayjs}>
                        <DateTimePicker 
                        value={datetimeState.value} 
                        onChange={datetimeState.set} 
                        format="DD/MM/YYYY HH:mm"
                        slotProps={{
                            textField: {
                              size: 'small',
                              sx: {
                                '& .MuiInputBase-input': {
                                  fontSize: '18px',
                                },
                                '& .MuiInputBase-input::placeholder': {
                                  color: '#aaa',     
                                  opacity: 1,
                                }
                              }
                            },
                            popper: {
                              placement: "right",
                            }
                          }}
                        />
                    </LocalizationProvider>
                </Box>
                <Box sx={{display: 'flex', flexDirection:'row',justifyContent:'space-between', alignItems: 'center', width: '100%', gap:2, mt:2}}>
                    <Button 
                        onClick={onCancel}
                        variant="contained"
                        color='secondary'
                        >
                        Cancellare
                    </Button>
                    <Button 
                        onClick={onConfirm}
                        variant="contained"
                        color='primary'
                        >
                        {textConfirmButton}
                    </Button>
                </Box>
            </DialogContent>
        </Dialog>
    )
}

export default DialogDateTime