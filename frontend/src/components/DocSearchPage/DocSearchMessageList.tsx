import React, { useEffect, useRef } from 'react'
import { Box, Paper, Typography } from '@mui/material'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import { toast } from 'react-toastify'
import { DotTyping } from '../DotTyping'

interface Message {
  sender: 'user' | 'ai'
  content: string
}

interface DocSearchMessageListProps {
  messages: Message[]
  isTyping: boolean
}

function removeCitations(text: string): string {
  return text.replace(/【[^【†】]*†[^【†】]*】/g, '');
}

const DocSearchMessageList: React.FC<DocSearchMessageListProps> = ({ messages, isTyping }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])


  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success('Codice copiato!')
  }

  

  return (
    <Box 
      sx={{ 
        position: 'absolute', 
        top: 0, bottom: 0, left: 0, right: 0, 
        overflowY: 'auto', 
        px: '1.1vw', pb: '20vh'
      }}
    >

      <React.Fragment>

        {messages.map((msg, idx) => {
          // const { thinkText, content: originalContent  } = parseThinkTag(msg.content)
          // const content = fixExcessiveLineBreaks(originalContent);
          // const contentWithCitations = citeLinks(originalContent, citations);
          const content = removeCitations(msg.content);
          return (
            <Box key={idx} display="flex" justifyContent={msg.sender === 'user' ? 'flex-end' : 'flex-start'} mb={0.5}>
              <Paper 
                sx={{ 
                  maxWidth: '95%',
                  px: '1.5rem',
                  py: '1rem',
                  backgroundColor: msg.sender === 'user' ? '#F9F9FB' : 'white',
                  borderRadius: '8px',
                  boxShadow: 'none',
                  overflow: 'hidden',
                  mb: '1vw',
                }}
              >
                <Typography variant="subtitle1" sx={{ fontSize: '14px', fontWeight: 'bold', mb: 1 }}>
                  {msg.sender === 'user' ? 'TU' : 'AI'}
                </Typography>

                {/* Markdown Content */}
                <Typography component="div" sx={{ whiteSpace: 'pre-wrap', fontSize:'1rem', padding: 0 }}>
                  <ReactMarkdown 
                    remarkPlugins={[remarkGfm]} 
                    rehypePlugins={[rehypeHighlight]}
                    components={{
                      p: ({ children, ...props }) => (
                        <Typography component="p" sx={{ margin: '0px 0', lineHeight: '1.5', fontSize:'1rem' }} {...props}>
                          {children}
                        </Typography>
                      ),
                      ul: ({ children, ...props }) => (
                        <Box component="ul" sx={{ marginY: 0, py:0, pl:3, fontSize:'1rem', lineHeight: '1' }} {...props}>
                          {children}
                        </Box>
                      ),
                      ol: ({ children, ...props }) => (
                        <Box component="ol" sx={{ marginY: 0, py:0, pl:3, fontSize:'1rem', lineHeight: '1' }} {...props}>
                          {children}
                        </Box>
                      ),
                      li: ({ children, ...props }) => (
                        <Typography component="li" sx={{ margin: 0, py:0 , fontSize:'1rem', lineHeight: '1.2' }} {...props}>
                          {children}
                        </Typography>
                      ),
                      h1: ({ children, ...props }) => (
                        <Typography component="h1" sx={{ margin: '4px 0', fontSize:'1.6rem', lineHeight: '1.8' }} {...props}>
                          {children}
                        </Typography>
                      ),
                      h2: ({ children, ...props }) => (
                        <Typography component="h2" sx={{ margin: '4px 0', fontSize:'1.4rem', lineHeight: '1.6' }} {...props}>
                          {children}
                        </Typography>
                      ),
                      h3: ({ children, ...props }) => (
                        <Typography component="h3" sx={{ margin: '4px 0', fontSize:'1.2rem', lineHeight: '1.4' }} {...props}>
                          {children}
                        </Typography>
                      ), 
                      h4: ({ children, ...props }) => (
                        <Typography component="h4" sx={{ margin: '4px 0', fontSize:'1rem', lineHeight: '1' }} {...props}>
                          {children}
                        </Typography>
                      ),
                      table: ({ children, ...props }) => (
                        <Box sx={{ overflowX: 'auto', my: 1 }}>
                          <table
                            {...props}
                            style={{
                              width: '100%',
                              tableLayout: 'fixed', // Isso garante que as colunas sejam fixas e alinhadas
                              borderCollapse: 'collapse',
                              textAlign: 'left', // Ajuste o alinhamento se necessário
                            }}
                          >
                            {children}
                          </table>
                        </Box>
                      ),
                      // Ajustando outras tags de lista, como <thead>, <tbody>, <tr>, <th>, <td>
                      thead: ({ children, ...props }) => (
                        <thead {...props} style={{ backgroundColor: '#f4f4f4', fontWeight: 'bold' }}>
                          {children}
                        </thead>
                      ),
                      tbody: ({ children, ...props }) => (
                        <tbody {...props}>{children}</tbody>
                      ),
                      tr: ({ children, ...props }) => (
                        <tr {...props} style={{ borderBottom: '1px solid #ddd' }}>
                          {children}
                        </tr>
                      ),
                      th: ({ children, ...props }) => (
                        <th {...props} style={{ padding: '8px', border: '1px solid #ddd' }}>
                          {children}
                        </th>
                      ),
                      td: ({ children, ...props }) => (
                        <td {...props} style={{ padding: '8px', border: '1px solid #ddd' }}>
                          {children}
                        </td>
                      ),
                      a: ({ href, children, ...props }) => (
                        <a 
                          href={href} 
                          target="_blank" 
                          rel="noopener noreferrer" 
                          style={{ 
                            textDecoration: 'none', 
                            color: '#ED6008',     
                          }}
                          {...props}
                        >
                          {children}
                        </a>
                      ),
                      code({ className, children, ...props }) {
                        const match = /language-(\w+)/.exec(className || '');
                        const language = match ? match[1] : '';
                    
                        return (
                          <Box 
                            sx={{ 
                              bgcolor: '#282C34', 
                              color: '#FFFFFF', 
                              padding: 2, 
                              borderRadius: '8px',
                              position: 'relative',
                              cursor: 'pointer',
                              overflowY: 'auto', 
                              my: 1
                            }}
                            onClick={() => copyToClipboard(String(children).replace(/\n$/, ''))}
                          >
                            <Typography variant="subtitle2" sx={{ 
                              position: 'absolute', 
                              top: 4, 
                              right: 8, 
                              color: '#ffffff88'
                            }}>
                              {language || 'code'} – Click per copiare
                            </Typography>
                            <code {...props}>
                              {children}
                            </code>
                          </Box>
                        );
                      }
                    }}
                  >
                    {content}
                  </ReactMarkdown>
                </Typography>

              </Paper>
            </Box>

          )
        })}
        
        {isTyping && ( 
          <Box display="flex" justifyContent="flex-start" mb={0.5}>
            <Paper
              sx={{
                maxWidth: '95%',
                px: '1.5rem',
                py: '1rem',
                backgroundColor: 'white',
                borderRadius: '8px',
                boxShadow: 'none',
                mb: '1vw',
              }}
            >
              <Typography variant="subtitle1" sx={{ fontSize: '14px', fontWeight: 'bold', mb: 1 }}>
                AI
              </Typography>
              <DotTyping />
            </Paper>
          </Box>
        )}

      </React.Fragment>

      <div ref={messagesEndRef}></div>
    </Box>
  )
}

export default DocSearchMessageList