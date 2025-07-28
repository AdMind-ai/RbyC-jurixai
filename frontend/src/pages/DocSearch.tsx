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
import Layout from "../layouts/Layout";
import { useDocSearch } from "../hooks/useDocSearch";
import DocSearchMessageList from "../components/DocSearchPage/DocSearchMessageList";
import DocSearchInputArea from "../components/DocSearchPage/DocSearchInputArea";
import LinedDropdown from "../components/dropdowns/LinedDropdown";
import SaveCleanButtons from "../components/buttons/SaveCleanButtons";
import CloseIcon from "@mui/icons-material/Close";

const DocSearch: React.FC = () => {
  const navigate = useNavigate();
  const {
    selectedModel,
    messages,
    setMessages,
    isTyping,
    setIsTyping,
    isOverview,
    setIsOverview,
    searchWebEnabled,
    selectedChat,
    setSelectedChat,
    // selectedCategory,
    // setSelectedCategory,
    chats,
    openSaveModal,
    setOpenSaveModal,
    openDeleteModal,
    setOpenDeleteModal,
    newChatName,
    setNewChatName,
    handleSaveClick,
    handleDeleteClick,
    handleSaveChat,
    handleDeleteChat,
    handleDropdownSelect,
    handleChatSelect,
    handleSendMessage
  } = useDocSearch();

  return (
    <Layout>
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          padding: "2.2vh 3vh",
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
            marginBottom: "0.2vw",
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 3 }}>
            <Typography variant="h2" sx={{ marginLeft: "1vw" }}>
              Ricerca documentale
            </Typography>
          </Box>

          {/* Modal para salvar chat */}
          <Dialog open={openSaveModal} onClose={() => setOpenSaveModal(false)}>
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
                Salva Chat
              </Box>
              <IconButton
                onClick={() => setOpenSaveModal(false)}
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
                Scegli un nome per il chat:
              </DialogContentText>
              <Box sx={{ display: "flex", justifyContent: "center", mt: 2 }}>
                <input
                  type="text"
                  value={newChatName}
                  onChange={(e) => setNewChatName(e.target.value)}
                  style={{
                    width: "80%",
                    padding: "8px",
                    borderRadius: "4px",
                    border: "1px solid #ccc",
                  }}
                />
              </Box>
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
                onClick={handleSaveChat}
                sx={{ py: 2.6, borderRadius: "10px" }}
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

        <Divider />
        <Box
          sx={{
            display: "flex",
            flexDirection: "row",
            gap: 2,
            mt: 2,
            justifyContent: "flex-end",
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
                navigate("/doc-search");
              }}
            />
          ) : null}
          {/* <LinedDropdown
            isMultipleOptions
            title="Seleziona categoria"
            options={[
              "Categoria 1",
              "Categoria 2",
              "Categoria 3",
              "Categoria 4",
            ]}
            value={selectedCategory}
            onChange={setSelectedCategory}
            width={200}
          /> */}
          <LinedDropdown
            title="Ricerche salvate"
            options={chats.slice().reverse().map((chat) => chat.name)}
            value={selectedChat ? selectedChat.name : ""}
            onChange={handleDropdownSelect}
            width={200}
            isDeleteItems
            onDeleteItem={(name) => {
              const chat = chats.find((c) => c.name === name);
              if (chat) handleDeleteClick(chat);
            }}
          />
        </Box>

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
            isOverview={isOverview}
          />
          {/* Messages Container */}
          {(selectedChat || messages.length !== 0) ? (
            <DocSearchInputArea
              onSend={handleSendMessage}
              selectedModel={selectedModel}
              selectedChat={selectedChat}
              searchWebEnabled={searchWebEnabled}
              isEmptyMessages={false}
              setIsOverview={setIsOverview}
              setIsTyping={setIsTyping}
            />
          ) : (
            <DocSearchInputArea
              onSend={handleSendMessage}
              selectedModel={selectedModel}
              selectedChat={selectedChat}
              searchWebEnabled={searchWebEnabled}
              isEmptyMessages={true}
              setIsOverview={setIsOverview}
              setIsTyping={setIsTyping}
            />
          )}
        </Box>
      </Box>
    </Layout>
  );
};

export default DocSearch;