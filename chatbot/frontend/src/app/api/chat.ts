import axios from 'axios';

const API_BASE_URL = '/api/v1';

export interface ChatCompletionRequest {
  message: string;
  stream?: boolean;
  user_id?: string;
}

export interface ChatMessage {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: string;
}

export interface ChatCompletionResponse {
  message: ChatMessage;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

export interface StreamingEvent {
  id?: string;
  type: 'content' | 'done' | 'error';
  content?: string;
  timestamp?: string;
  error?: string;
}

export class ChatAPI {
  static async createChatCompletion(request: ChatCompletionRequest): Promise<ChatCompletionResponse> {
    try {
      const response = await axios.post<ChatCompletionResponse>(
        `${API_BASE_URL}/chat/completions`,
        request
      );
      return response.data;
    } catch (error) {
      console.error('Error creating chat completion:', error);
      throw error;
    }
  }

  static createStreamingChatCompletion(
    request: ChatCompletionRequest,
    onMessage: (event: StreamingEvent) => void,
    onError?: (error: Error) => void,
    onComplete?: () => void
  ): EventSource {
    // We need to use fetch for POST with EventSource, so let's use a different approach
    const controller = new AbortController();
    
    fetch(`${API_BASE_URL}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify({ ...request, stream: true }),
      signal: controller.signal,
    })
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        
        if (!reader) {
          throw new Error('No response body');
        }

        const processStream = async () => {
          try {
            while (true) {
              const { done, value } = await reader.read();
              if (done) {
                onComplete?.();
                break;
              }

              const chunk = decoder.decode(value, { stream: true });
              const lines = chunk.split('\n');

              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  try {
                    const data = JSON.parse(line.slice(6));
                    onMessage(data);
                  } catch (e) {
                    console.error('Error parsing SSE data:', e);
                  }
                }
              }
            }
          } catch (error) {
            if (error instanceof Error) {
              onError?.(error);
            }
          }
        };

        processStream();
      })
      .catch(error => {
        onError?.(error);
      });

    // Return a mock EventSource-like object with close method
    return {
      close: () => controller.abort(),
    } as EventSource;
  }
}