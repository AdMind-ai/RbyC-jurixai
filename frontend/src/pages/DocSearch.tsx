import React from 'react'
import { useDocSearch } from '../hooks/useDocSearch'
import DocSearchMessageList from '../components/DocSearchPage/DocSearchMessageList'
import DocSearchInputArea from '../components/DocSearchPage/DocSearchInputArea'
import { X } from 'lucide-react'

const DocSearch: React.FC = () => {
  const {
    messages,
    setMessages,
    isTyping,
    setIsTyping,
    selectedChat,
    setSelectedChat,
    chats,
    openSaveModal,
    setOpenSaveModal,
    openDeleteModal,
    setOpenDeleteModal,
    handleSaveClick,
    handleSaveChat,
    handleDeleteChat,
    handleChatSelect,
    handleSendMessage,
  } = useDocSearch()

  return (
    <div className="page-root flex flex-col h-full bg-slate-50">
      {/* Header */}
      <div className="page-header flex items-center justify-between px-6 py-4 bg-white border-b border-slate-100 shrink-0">
        <h2 className="page-title text-base font-semibold text-slate-800">Ricerca documentale</h2>

        <div className="flex items-center gap-4">
          <select
            className="apple-select text-sm py-1.5 px-3 h-auto"
            value={selectedChat ? selectedChat.name : ''}
            onChange={(e) => {
              const name = e.target.value;
              const chat = chats.find((c) => c.name === name);
              if (chat) {
                handleChatSelect(
                  chat.id,
                  chat.name,
                  chat.thread_id ?? undefined
                );
                setSelectedChat(chat);
              }
            }}
          >
            <option value="" disabled>Ricerche salvate...</option>
            {chats.slice().reverse().map((chat) => (
              <option key={chat.id} value={chat.name}>{chat.name}</option>
            ))}
          </select>

          {messages.length > 0 && (
            <div className="flex items-center gap-2">
              <button onClick={handleSaveClick} className="btn-secondary py-1.5 px-3 text-sm h-auto">
                Salva
              </button>
              <button 
                onClick={() => {
                  setSelectedChat(null);
                  handleChatSelect(null, null);
                  setMessages([]);
                }} 
                className="btn-secondary py-1.5 px-3 text-sm h-auto"
              >
                Nuova
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-hidden relative flex flex-col w-full">
        <DocSearchMessageList messages={messages} isTyping={isTyping} />
        <DocSearchInputArea
          onSendMessage={handleSendMessage}
          isEmptyMessages={messages.length === 0}
          isTyping={isTyping}
          setIsTyping={setIsTyping}
        />
      </div>

      {/* Save Modal */}
      {openSaveModal && (
        <div className="modal-overlay">
          <div className="modal-box relative">
            <button onClick={() => setOpenSaveModal(false)} className="absolute top-4 right-4 text-slate-400 hover:text-slate-600">
              <X size={20} />
            </button>
            <h3 className="text-xl font-semibold text-slate-800 mb-4 text-center">Salva Chat</h3>
            <p className="text-sm text-slate-500 text-center mb-6">Scegli un nome per la chat:</p>
            <div className="flex justify-center mb-6">
              <input
                type="text"
                id="save-chat-input"
                className="apple-input w-full"
                placeholder="Nome chat..."
                autoFocus
              />
            </div>
            <div className="flex justify-center">
              <button
                className="btn-primary"
                onClick={() => {
                  const input = document.getElementById('save-chat-input') as HTMLInputElement;
                  handleSaveChat(input?.value || '');
                }}
              >
                Salva
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Modal */}
      {openDeleteModal && (
        <div className="modal-overlay">
          <div className="modal-box relative">
            <button onClick={() => setOpenDeleteModal(false)} className="absolute top-4 right-4 text-slate-400 hover:text-slate-600">
              <X size={20} />
            </button>
            <h3 className="text-xl font-semibold text-slate-800 mb-4 text-center">Conferma Eliminazione</h3>
            <p className="text-sm text-slate-500 text-center mb-6">
              Vuoi davvero eliminare la chat <strong>{selectedChat?.name}</strong>?<br />
              Una volta eliminata, non sarà possibile recuperarla.
            </p>
            <div className="flex justify-center gap-3">
              <button className="btn-secondary" onClick={() => setOpenDeleteModal(false)}>Annulla</button>
              <button className="btn-danger" onClick={handleDeleteChat}>Elimina</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default DocSearch
