import React from "react";
import { useNavigate } from "react-router-dom";
import {
    Box,
    Divider,
    Typography,
    Button,
    Dialog,
    DialogContent,
    DialogActions,
    DialogContentText,
    DialogTitle,
    IconButton,
} from "@mui/material";
import { useDocSearch } from "../../hooks/useDocSearch";
import DocSearchMessageList from "../../components/DocSearchPage/DocSearchMessageList";
import DocSearchInputArea from "../../components/DocSearchPage/DocSearchInputArea";
import LinedDropdown from "../../components/dropdowns/LinedDropdown";
import SaveCleanButtons from "../../components/buttons/SaveCleanButtons";
import CloseIcon from "@mui/icons-material/Close";

const SearchView: React.FC = () => {
    const navigate = useNavigate();
    const {
        messages,
        setMessages,
        isTyping,
        setIsTyping,
        selectedChat,
        setSelectedChat,
        // selectedCategory,
        // setSelectedCategory,
        chats,
        openSaveModal,
        setOpenSaveModal,
        openDeleteModal,
        setOpenDeleteModal,
        handleSaveClick,
        handleDeleteClick,
        handleSaveChat,
        handleDeleteChat,
        handleChatSelect,
        handleSendMessage,
        // createThread
    } = useDocSearch();

    return (
        <Box
            sx={{
                display: "flex",
                flexDirection: "column",
                padding: "5vh 2vh",
                overflow: "auto",
                height: "100%",
                width: "100%",
            }}
        >
            {/* Header */}
            <Box
                sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: "2vh",
                }}
            >
                <Typography variant="h3" sx={{ marginLeft: "1vw" }}>
                    Ricerca documentale
                </Typography>
                <Box
                    sx={{
                        display: "flex",
                        flexDirection: "row",
                        alignItems: "center",
                    }}
                >
                    {messages.length > 0 ? (
                        <SaveCleanButtons
                            onSave={handleSaveClick}
                            onClean={() => {
                                setSelectedChat(null);
                                handleChatSelect(null, null);
                                setMessages([]);
                                navigate("/search");
                            }}
                        />
                    ) : null}
                    <LinedDropdown
                        title="Ricerche salvate"
                        options={chats.slice().reverse().map((chat) => chat.name)}
                        value={selectedChat ? selectedChat.name : ""}
                        onChange={(value: string | string[]) => {
                            const name = Array.isArray(value) ? value[0] : value;
                            const chat = chats.find((c) => c.name === name);
                            if (chat) {
                                handleChatSelect(chat.id, chat.name, chat.thread_id ?? undefined);
                                setSelectedChat(chat);
                            }
                        }}
                        width={200}
                        isDeleteItems
                        onDeleteItem={(name) => {
                            const chat = chats.find((c) => c.name === name);
                            if (chat) handleDeleteClick(chat);
                        }}
                    />
                </Box>

                {/* Modal para salvar chat */}
                <Dialog open={openSaveModal} onClose={() => setOpenSaveModal(false)}>
                    <DialogTitle>Salva Chat</DialogTitle>
                    <DialogContent>
                        <DialogContentText>
                            Scegli un nome per il chat:
                        </DialogContentText>
                        <Box sx={{ display: "flex", justifyContent: "center", mt: 2 }}>
                            <input
                                type="text"
                                id="save-chat-input"
                                // value={newChatName}
                                // onChange={(e) => setNewChatName(e.target.value)}
                                style={{
                                    width: "80%",
                                    padding: "8px",
                                    borderRadius: "4px",
                                    border: "1px solid #ccc",
                                }}
                            />
                        </Box>
                    </DialogContent>
                    <DialogActions>
                        <Button
                            variant="contained"
                            onClick={() => {
                                const chatName = (document.getElementById("save-chat-input") as HTMLInputElement)?.value || "";
                                handleSaveChat(chatName);
                            }}
                        >
                            Salva
                        </Button>
                    </DialogActions>
                </Dialog>

                {/* Modal para deletar chat */}
                <Dialog open={openDeleteModal} onClose={() => setOpenDeleteModal(false)}>
                    <DialogTitle
                        sx={{
                            display: "flex",
                            alignItems: "center",
                            fontWeight: "bold",
                            justifyContent: "center",
                            mt: 2,
                            fontSize: "26px",
                            borderRadius: "16px",
                        }}
                    >
                        <Box sx={{ display: "flex", alignItems: "center" }}>
                            Conferma Eliminazione
                        </Box>
                        <IconButton
                            onClick={() => setOpenDeleteModal(false)}
                            sx={{ position: "absolute", top: 10, right: 10 }}
                        >
                            <CloseIcon sx={{ color: "#000" }} />
                        </IconButton>
                    </DialogTitle>
                    <DialogContent sx={{ borderRadius: "16px" }}>
                        <DialogContentText
                            sx={{
                                color: "black",
                                textAlign: "center",
                                fontSize: "20px",
                                my: 0.5,
                                mx: 1,
                            }}
                        >
                            Vuoi davvero eliminare il chat {selectedChat?.name}?<br />
                            Una volta eliminato, non sarà possibile recuperarlo.
                        </DialogContentText>
                    </DialogContent>
                    <DialogActions
                        sx={{
                            justifyContent: "center",
                            pb: 2.5,
                            mb: 2,
                            borderRadius: "16px",
                        }}
                    >
                        <Button
                            variant="contained"
                            onClick={handleDeleteChat}
                            sx={{
                                bgcolor: "#d32f2f",
                                color: "#fff",
                                py: 2.6,
                                borderRadius: "10px",
                                "&:hover": { bgcolor: "#c62828" },
                            }}
                        >
                            Elimina
                        </Button>
                    </DialogActions>
                </Dialog>
            </Box>

            <Divider sx={{ mx: 2 }} />

            <Box
                sx={{
                    flex: 1,
                    position: "relative",
                    overflow: "hidden",
                    display: "flex",
                    flexDirection: "column",
                    marginTop: "1rem",
                    height: "100%",
                }}
            >
                <DocSearchMessageList
                    messages={messages}
                    isTyping={isTyping}
                />
                {/* Messages Container */}
                {(selectedChat || messages.length !== 0) ? (
                    <DocSearchInputArea
                        onSendMessage={handleSendMessage}
                        isEmptyMessages={messages.length === 0}
                        isTyping={isTyping}
                        setIsTyping={setIsTyping}
                    />
                ) : (
                    <DocSearchInputArea
                        onSendMessage={handleSendMessage}
                        isEmptyMessages={messages.length === 0}
                        isTyping={isTyping}
                        setIsTyping={setIsTyping}
                    />
                )}
            </Box>
        </Box>
    );
};

export default SearchView;