import * as React from 'react';
import {
  Alert,
  Button,
  PageSection,
  Switch,
} from '@patternfly/react-core';
import { ArrowDownIcon } from '@patternfly/react-icons';
import {
  Chatbot,
  ChatbotContent,
  ChatbotDisplayMode,
  ChatbotFooter,
  ChatbotFootnote,
  ChatbotHeader,
  ChatbotHeaderMain,
  ChatbotHeaderTitle,
  ChatbotHeaderActions,
  Message,
  MessageBar,
  MessageBox,
} from '@patternfly/chatbot';
import { ChatAPI, StreamingEvent } from '@app/api/chat';
import aiLogo from '@app/images/ai-logo-transparent.svg';
import avatarImg from '@app/images/user-avatar.svg';
import { ImagePreview } from './ImagePreview';

export interface IChatProps {
  sampleProp?: string;
}

interface ChatMessage {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
  isStreaming?: boolean; // Track if this message is currently streaming
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
  const [streamingMode, setStreamingMode] = React.useState(true);
  const [autoScrollEnabled, setAutoScrollEnabled] = React.useState(false);
  const streamControllerRef = React.useRef<EventSource | null>(null);
  const [announcement, setAnnouncement] = React.useState<string | undefined>();
  const messageBoxRef = React.useRef<HTMLDivElement>(null);
  const [userScrolledUp, setUserScrolledUp] = React.useState(false);
  const scrollTimeoutRef = React.useRef<NodeJS.Timeout | null>(null);
  const scrollDetectionTimeoutRef = React.useRef<NodeJS.Timeout | null>(null);

  // Scroll utility functions
  const scrollToBottom = React.useCallback((smooth = true) => {
    if (messageBoxRef.current) {
      const container = messageBoxRef.current;
      const scrollOptions: ScrollToOptions = {
        top: container.scrollHeight,
        behavior: smooth ? 'smooth' : 'auto',
      };
      container.scrollTo(scrollOptions);
    }
  }, []);

  const isScrolledNearBottom = React.useCallback((threshold = 100) => {
    if (!messageBoxRef.current) return true;
    const container = messageBoxRef.current;
    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    return distanceFromBottom <= threshold;
  }, []);

  const handleScroll = React.useCallback(() => {
    // Throttle scroll detection for better performance
    if (scrollDetectionTimeoutRef.current) {
      clearTimeout(scrollDetectionTimeoutRef.current);
    }
    scrollDetectionTimeoutRef.current = setTimeout(() => {
      const nearBottom = isScrolledNearBottom();
      setUserScrolledUp(!nearBottom);
    }, 100);
  }, [isScrolledNearBottom]);

  const handleSendMessage = async (message: string | number) => {
    const messageText = typeof message === 'string' ? message : message.toString();
    
    if (messageText.trim() && !isLoading) {
      const userMessage: ChatMessage = {
        id: Date.now().toString(),
        text: messageText,
        sender: 'user',
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setInputValue('');
      setIsLoading(true);
      setError(null);
      
      // Auto-scroll when user sends a message
      if (autoScrollEnabled) {
        setTimeout(() => scrollToBottom(), 50);
      }

      try {
        if (streamingMode) {
          // Streaming mode
          let accumulatedText = '';
          
          const botMessage: ChatMessage = {
            id: Date.now().toString() + '-bot',
            text: '',
            sender: 'bot',
            timestamp: new Date(),
            isStreaming: true, // Mark as streaming initially
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
                  return prev.map((msg) => 
                    msg.id === botMessage.id
                      ? { ...msg, text: accumulatedText, isStreaming: true }
                      : msg
                  );
                });
                
                // Auto-scroll during streaming if user hasn't scrolled up (throttled)
                if (autoScrollEnabled && !userScrolledUp) {
                  if (scrollTimeoutRef.current) {
                    clearTimeout(scrollTimeoutRef.current);
                  }
                  scrollTimeoutRef.current = setTimeout(() => scrollToBottom(), 200);
                }
              } else if (event.type === 'done') {
                // Mark streaming as complete
                setMessages((prev) => {
                  return prev.map((msg) => 
                    msg.id === botMessage.id
                      ? { ...msg, isStreaming: false }
                      : msg
                  );
                });
                setIsLoading(false);
                streamControllerRef.current = null;
                setAnnouncement('Message received');
                
                // Final scroll when streaming is complete
                if (autoScrollEnabled && !userScrolledUp) {
                  setTimeout(() => scrollToBottom(), 100);
                }
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
          setAnnouncement('Message received');
          
          // Auto-scroll when bot message is received (non-streaming)
          if (autoScrollEnabled && !userScrolledUp) {
            setTimeout(() => scrollToBottom(), 100);
          }
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
        
        // Auto-scroll when error message is added
        if (autoScrollEnabled && !userScrolledUp) {
          setTimeout(() => scrollToBottom(), 100);
        }
      } finally {
        if (!streamingMode) {
          setIsLoading(false);
        }
      }
    }
  };

  const handleStopStreaming = () => {
    if (streamControllerRef.current) {
      streamControllerRef.current.close();
      streamControllerRef.current = null;
      setIsLoading(false);
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

  // Initial scroll to bottom on component mount (only if auto-scroll is enabled)
  React.useEffect(() => {
    if (autoScrollEnabled) {
      setTimeout(() => scrollToBottom(false), 100);
    }
  }, [scrollToBottom, autoScrollEnabled]);

  // Cleanup scroll timeouts on unmount
  React.useEffect(() => {
    return () => {
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
      if (scrollDetectionTimeoutRef.current) {
        clearTimeout(scrollDetectionTimeoutRef.current);
      }
    };
  }, []);

  const displayMode = ChatbotDisplayMode.embedded;

  return (
    <PageSection isFilled hasBodyWrapper={false}>
      <Chatbot displayMode={displayMode} isVisible>
        <ChatbotHeader>
          <ChatbotHeaderMain>
            <ChatbotHeaderTitle>Chat</ChatbotHeaderTitle>
            <ChatbotHeaderActions>
              <Switch
                id="streaming-mode"
                label="Streaming mode"
                isChecked={streamingMode}
                onChange={(_event, checked) => setStreamingMode(checked)}
                isDisabled={isLoading}
              />
              <Switch
                id="auto-scroll"
                label="Auto-scroll"
                isChecked={autoScrollEnabled}
                onChange={(_event, checked) => setAutoScrollEnabled(checked)}
                isDisabled={isLoading}
              />
            </ChatbotHeaderActions>
          </ChatbotHeaderMain>
        </ChatbotHeader>
        <ChatbotContent>
          {userScrolledUp && autoScrollEnabled && (
            <div style={{ 
              position: 'absolute', 
              bottom: '80px', 
              right: '20px', 
              zIndex: 1000 
            }}>
              <Button
                variant="primary"
                onClick={() => {
                  scrollToBottom();
                  setUserScrolledUp(false);
                }}
                icon={<ArrowDownIcon />}
                aria-label="Scroll to bottom"
                size="sm"
              >
                New messages
              </Button>
            </div>
          )}
          <MessageBox 
            ref={messageBoxRef}
            announcement={announcement} 
            ariaLabel="Chat messages"
            onScroll={handleScroll}
          >
            {error && (
              <Alert 
                variant="danger" 
                title={error} 
                isInline 
                actionClose={<Button variant="plain" onClick={() => setError(null)} aria-label="Close alert" />}
                style={{ marginBottom: '16px' }} 
              />
            )}
            {messages.map((message) => {
              // Show loading indicator only when streaming hasn't started (no text yet)
              const showLoadingIndicator = message.isStreaming && message.text === '';

              return (
                <Message
                  key={message.id}
                  id={message.id}
                  role={message.sender === 'user' ? 'user' : 'bot'}
                  content={message.text}
                  timestamp={message.timestamp.toLocaleTimeString()}
                  avatar={message.sender === 'user' ? avatarImg : aiLogo}
                  name={message.sender === 'user' ? 'You' : 'AI Assistant'}
                  isLoading={showLoadingIndicator}
                  extraContent={message.sender === 'bot' ? {
                    afterMainContent: <ImagePreview content={message.text} />
                  } : undefined}
                />
              );
            })}
            {isLoading && !streamingMode && (
              <Message
                id="loading-message"
                role="bot"
                content=""
                avatar={aiLogo}
                name="AI Assistant"
                isLoading
              />
            )}
          </MessageBox>
        </ChatbotContent>
        <ChatbotFooter>
          <MessageBar
            onSendMessage={handleSendMessage}
            hasStopButton={isLoading && streamingMode}
            handleStopButton={handleStopStreaming}
            isSendButtonDisabled={!inputValue.trim() || isLoading}
            value={inputValue}
            onChange={(_event, value) => setInputValue(value as string)}
            placeholder="Type your message..."
          />
          <ChatbotFootnote label="AI-Powered Chat" />
        </ChatbotFooter>
      </Chatbot>
    </PageSection>
  );
};

export { Chat };