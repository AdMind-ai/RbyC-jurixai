import React, { useState, useEffect } from 'react'
import { Box } from '@mui/material'

import MessageList from './subcomponents/MessageList'
import InputArea from './subcomponents/InputArea'


interface Message {
  sender: 'user' | 'ai'
  content: string
  citations?: string[]
}


const LawReferences: React.FC = () => {
  const [selectedModel, setSelectedModel] = useState('GPT-4.1')
  const [messages, setMessages] = useState<Message[]>([])
  const [isTyping, setIsTyping] = useState(false);
  const [isOverview, setIsOverview] = useState(false);
  const [searchWebEnabled, setSearchWebEnabled] = useState(false)
  const [selectedChat, setSelectedChat] = useState<{ id: number | string ; name: string } | null>(null);


  useEffect(() => {
    if (searchWebEnabled) {
      setSelectedModel('GPT-4o');
    }
  }, [searchWebEnabled]);

  const handleSendMessage = (message: string, sender: 'user'|'ai', isStream: boolean = false) => {
    console.log('----------------------------')
    console.log('onsend:', message, '\n', sender, ' - ', isStream);
    if (!isStream) {
      setIsOverview(false);
      if (sender === 'user') 
        setMessages(messages => [...messages, { sender, content: message }]);
    } else {
      console.log('isOverview: ',isOverview, 'isTyping: ', isTyping)
      setMessages(messages => {
        const lastMessage = messages[messages.length - 1];
        if (sender === 'ai' && lastMessage?.sender === 'ai') {
          return [...messages.slice(0, -1), { sender: 'ai', content: lastMessage.content + message }];
        } else {
          return [...messages, { sender, content: message }];
        }
      });
    }
    console.log('----------------------------')
  };


  return (
      <Box
        sx={{
        display: 'flex',
        flexDirection: 'column',
        padding: '2.2vh 3vh',
        height: '100%',
        width: '100%',
        }}
      >      
        <Box 
          sx={{
            display: 'flex',
            flexDirection: 'column',
            marginTop: 1,
            height: '100%',
          }}
        >
          <MessageList 
            messages={messages} 
            setMessages={setMessages}
            isTyping={isTyping} 
            isOverview={isOverview}
          />
          {/* Messages Container */}
          { (selectedChat || messages.length === 0) && (
            <InputArea 
              onSend={handleSendMessage} 
              selectedModel={selectedModel} 
              selectedChat={selectedChat}
              setSelectedChat={setSelectedChat}
              searchWebEnabled={searchWebEnabled}
              setSearchWebEnabled={setSearchWebEnabled}
              isEmptyMessages={true}
              setIsOverview={setIsOverview}
              setIsTyping={setIsTyping}
            />
          )}
        </Box>
      </Box>
  )
}

export default LawReferences