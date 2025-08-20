import * as React from 'react';
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Form,
  FormGroup,
  PageSection,
  Spinner,
  Switch,
  TextArea,
  Stack,
  StackItem,
} from '@patternfly/react-core';
import { PaperPlaneIcon } from '@patternfly/react-icons';
import { ChatAPI, StreamingEvent } from '@app/api/chat';

export interface IChatProps {
  sampleProp?: string;
}

interface ChatMessage {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
}

const Chat: React.FunctionComponent<IChatProps> = () => {
  const [messages, setMessages] = React.useState<ChatMessage[]>([
    {
      id: '1',
      text: 'Hello! How can I help you today?',
      sender: 'bot',
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = React.useState('');
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [streamingMode, setStreamingMode] = React.useState(false);
  const streamControllerRef = React.useRef<EventSource | null>(null);

  const handleSendMessage = async () => {
    if (inputValue.trim() && !isLoading) {
      const userMessage: ChatMessage = {
        id: Date.now().toString(),
        text: inputValue,
        sender: 'user',
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setInputValue('');
      setIsLoading(true);
      setError(null);

      try {
        if (streamingMode) {
          // Streaming mode
          let accumulatedText = '';
          
          const botMessage: ChatMessage = {
            id: Date.now().toString() + '-bot',
            text: '',
            sender: 'bot',
            timestamp: new Date(),
          };
          
          setMessages((prev) => [...prev, botMessage]);
          
          streamControllerRef.current = ChatAPI.createStreamingChatCompletion(
            {
              message: userMessage.text,
              stream: true,
            },
            (event: StreamingEvent) => {
              if (event.type === 'content' && event.content) {
                accumulatedText += event.content;
                setMessages((prev) => {
                  const newMessages = [...prev];
                  const lastMessage = newMessages[newMessages.length - 1];
                  if (lastMessage && lastMessage.id === botMessage.id) {
                    lastMessage.text = accumulatedText;
                  }
                  return newMessages;
                });
              } else if (event.type === 'done') {
                setIsLoading(false);
                streamControllerRef.current = null;
              } else if (event.type === 'error') {
                setError(event.error || 'Streaming error occurred');
                setIsLoading(false);
                streamControllerRef.current = null;
              }
            },
            (error) => {
              console.error('Streaming error:', error);
              setError('Failed to stream message. Please try again.');
              setIsLoading(false);
              streamControllerRef.current = null;
            },
            () => {
              setIsLoading(false);
              streamControllerRef.current = null;
            }
          );
        } else {
          // Non-streaming mode
          const response = await ChatAPI.createChatCompletion({
            message: userMessage.text,
            stream: false,
          });

          const botMessage: ChatMessage = {
            ...response.message,
            timestamp: new Date(response.message.timestamp),
          };

          setMessages((prev) => [...prev, botMessage]);
        }
      } catch (err) {
        console.error('Error sending message:', err);
        setError('Failed to send message. Please try again.');
        
        // Add error message to chat
        const errorMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          text: 'Sorry, I encountered an error. Please try again.',
          sender: 'bot',
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMessage]);
      } finally {
        if (!streamingMode) {
          setIsLoading(false);
        }
      }
    }
  };

  const handleKeyPress = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey && !isLoading) {
      event.preventDefault();
      handleSendMessage();
    }
  };

  // Cleanup streaming on unmount
  React.useEffect(() => {
    return () => {
      if (streamControllerRef.current) {
        streamControllerRef.current.close();
      }
    };
  }, []);

  return (
    <PageSection hasBodyWrapper={false}>
      <Card style={{ height: '600px', display: 'flex', flexDirection: 'column' }}>
        <CardHeader>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <CardTitle>Chat</CardTitle>
            <Switch
              id="streaming-mode"
              label="Streaming mode"
              isChecked={streamingMode}
              onChange={(_event, checked) => setStreamingMode(checked)}
              isDisabled={isLoading}
            />
          </div>
        </CardHeader>
        <CardBody style={{ flex: 1, overflow: 'auto', padding: '16px' }}>
          {error && (
            <Alert 
              variant="danger" 
              title={error} 
              isInline 
              actionClose={<Button variant="plain" onClick={() => setError(null)} aria-label="Close alert" />}
              style={{ marginBottom: '16px' }} 
            />
          )}
          <Stack hasGutter>
            {messages.map((message) => (
              <StackItem key={message.id}>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: message.sender === 'user' ? 'flex-end' : 'flex-start',
                    marginBottom: '8px',
                  }}
                >
                  <div
                    style={{
                      maxWidth: '70%',
                      padding: '12px',
                      borderRadius: '8px',
                      backgroundColor: message.sender === 'user' ? '#0066cc' : '#f5f5f5',
                      color: message.sender === 'user' ? 'white' : 'black',
                    }}
                  >
                    <div>
                      <p style={{ margin: 0 }}>{message.text}</p>
                      <small
                        style={{
                          opacity: 0.7,
                          marginTop: '4px',
                          color: message.sender === 'user' ? 'rgba(255,255,255,0.8)' : '#666',
                          display: 'block',
                        }}
                      >
                        {message.timestamp.toLocaleTimeString()}
                      </small>
                    </div>
                  </div>
                </div>
              </StackItem>
            ))}
            {isLoading && !streamingMode && (
              <StackItem>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Spinner size="md" />
                  <span>Bot is typing...</span>
                </div>
              </StackItem>
            )}
          </Stack>
        </CardBody>
        <div style={{ padding: '16px', borderTop: '1px solid #d2d2d2' }}>
          <Form onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }}>
            <FormGroup fieldId="message-input">
              <div style={{ display: 'flex', gap: '8px' }}>
                <TextArea
                  id="message-input"
                  value={inputValue}
                  onChange={(_event, value) => setInputValue(value)}
                  onKeyDown={handleKeyPress}
                  placeholder="Type your message..."
                  rows={2}
                  style={{ flex: 1 }}
                />
                <Button
                  variant="primary"
                  onClick={handleSendMessage}
                  isDisabled={!inputValue.trim() || isLoading}
                  icon={<PaperPlaneIcon />}
                  isLoading={isLoading}
                >
                  Send
                </Button>
              </div>
            </FormGroup>
          </Form>
        </div>
      </Card>
    </PageSection>
  );
};

export { Chat };