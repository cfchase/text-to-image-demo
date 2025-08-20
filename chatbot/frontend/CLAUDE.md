# Frontend CLAUDE.md

This file provides frontend-specific guidance to Claude Code when working with the React frontend.

## Frontend Architecture

### React + Vite Frontend
- TypeScript for type safety
- Vite for fast development and building
- PatternFly for UI components and design system
- Axios for API communication
- React Router for navigation
- Modern React patterns with hooks
- Responsive design with mobile support
- PWA capabilities

## Frontend Development

### Local Development
```bash
make dev-frontend     # Run React dev server (port 8080)
cd frontend && npm run dev                # Direct command
cd frontend && npm run dev -- --port 3000 # Custom port
```

### Dependencies
```bash
cd frontend && npm install <package>      # Add runtime dependency
cd frontend && npm install -D <package>   # Add development dependency
cd frontend && npm update                 # Update dependencies
cd frontend && npm audit fix              # Fix security vulnerabilities
```

### Building
```bash
cd frontend && npm run build             # Build for production
cd frontend && npm run preview           # Preview production build
```

### Testing
```bash
make test-frontend    # Run frontend tests
cd frontend && npm test                  # Direct command
cd frontend && npm run test:coverage     # With coverage report
cd frontend && npm run test:watch        # Watch mode
```

### Linting and Formatting
```bash
cd frontend && npm run lint              # Run ESLint
cd frontend && npm run lint:fix          # Auto-fix linting issues
cd frontend && npm run format            # Format with Prettier
cd frontend && npm run typecheck        # TypeScript type checking
```

## UI Components and Design

### PatternFly Integration
The frontend uses Red Hat's PatternFly design system:
- Consistent UI components and patterns
- Responsive grid system
- Accessibility compliance
- Dark/light theme support
- Professional enterprise appearance

### Component Structure
```
frontend/src/
├── components/          # Reusable UI components
│   ├── common/         # Generic components
│   ├── chat/           # Chat-specific components
│   └── layout/         # Layout components
├── pages/              # Page components
├── hooks/              # Custom React hooks
├── services/           # API services
├── utils/              # Utility functions
├── types/              # TypeScript type definitions
├── styles/             # Global styles and themes
└── assets/             # Static assets
```

### Component Guidelines
When creating new components:
1. Use TypeScript with proper type definitions
2. Follow PatternFly component patterns
3. Implement proper error boundaries
4. Add accessibility attributes (ARIA)
5. Support both light and dark themes
6. Make components responsive
7. Write comprehensive tests
8. Document props with JSDoc

Example component:
```typescript
import React from 'react';
import { Button, ButtonProps } from '@patternfly/react-core';

interface CustomButtonProps extends ButtonProps {
  /** Custom label for the button */
  label: string;
  /** Loading state */
  isLoading?: boolean;
}

export const CustomButton: React.FC<CustomButtonProps> = ({
  label,
  isLoading = false,
  ...props
}) => {
  return (
    <Button
      {...props}
      isLoading={isLoading}
      aria-label={label}
    >
      {label}
    </Button>
  );
};
```

## API Integration

### Service Layer
Create service modules for API interactions:
```typescript
// services/chatService.ts
import axios from 'axios';

const API_BASE = '/api';

export interface ChatMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
}

export const chatService = {
  async sendMessage(message: string): Promise<ChatMessage> {
    const response = await axios.post(`${API_BASE}/chat`, { message });
    return response.data;
  },

  async getHistory(): Promise<ChatMessage[]> {
    const response = await axios.get(`${API_BASE}/chat/history`);
    return response.data;
  }
};
```

### Error Handling
Implement proper error handling for API calls:
```typescript
import { toast } from '@patternfly/react-core';

const handleApiError = (error: any) => {
  const message = error.response?.data?.detail || 'An unexpected error occurred';
  toast.danger('Error', message);
  console.error('API Error:', error);
};
```

## State Management

### React Context for Global State
Use React Context for application-wide state:
```typescript
// contexts/AppContext.tsx
import React, { createContext, useContext, useReducer } from 'react';

interface AppState {
  user: User | null;
  theme: 'light' | 'dark';
  isLoading: boolean;
}

interface AppContextType {
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const useAppContext = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext must be used within AppProvider');
  }
  return context;
};
```

### Custom Hooks
Create custom hooks for reusable logic:
```typescript
// hooks/useChat.ts
import { useState, useCallback } from 'react';
import { chatService, ChatMessage } from '../services/chatService';

export const useChat = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = useCallback(async (content: string) => {
    setIsLoading(true);
    try {
      const response = await chatService.sendMessage(content);
      setMessages(prev => [...prev, response]);
    } catch (error) {
      handleApiError(error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { messages, isLoading, sendMessage };
};
```

## Configuration

### Environment Variables
Frontend configuration through `.env` files:
- `VITE_API_BASE_URL` - Backend API base URL
- `VITE_APP_TITLE` - Application title
- `VITE_ENABLE_PWA` - Enable PWA features

### Vite Configuration
Key configurations in `vite.config.ts`:
- Proxy configuration for API calls
- Build optimization settings
- TypeScript integration
- PWA plugin configuration

## Testing

### Testing Strategy
- Unit tests for components and utilities
- Integration tests for API services
- E2E tests for critical user flows
- Accessibility testing
- Performance testing

### Test Utilities
```typescript
// utils/testUtils.tsx
import React from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';

const AllProviders: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <BrowserRouter>
      {children}
    </BrowserRouter>
  );
};

const customRender = (ui: React.ReactElement, options?: RenderOptions) =>
  render(ui, { wrapper: AllProviders, ...options });

export * from '@testing-library/react';
export { customRender as render };
```

## Performance Optimization

### Code Splitting
```typescript
import { lazy, Suspense } from 'react';

const ChatPage = lazy(() => import('./pages/ChatPage'));

const App = () => (
  <Suspense fallback={<div>Loading...</div>}>
    <ChatPage />
  </Suspense>
);
```

### Memoization
```typescript
import React, { memo, useMemo } from 'react';

const ExpensiveComponent = memo(({ data }: { data: any[] }) => {
  const processedData = useMemo(() => {
    return data.map(item => expensiveProcessing(item));
  }, [data]);

  return <div>{processedData}</div>;
});
```

## Accessibility

### ARIA Guidelines
- Use semantic HTML elements
- Add proper ARIA labels and roles
- Ensure keyboard navigation support
- Maintain proper focus management
- Test with screen readers
- Follow WCAG 2.1 AA standards

### PatternFly Accessibility
PatternFly components include built-in accessibility features:
- Keyboard navigation
- Screen reader support
- High contrast support
- Focus indicators

## Common Frontend Tasks

### Adding New Pages
1. Create page component in `src/pages/`
2. Add route to React Router configuration
3. Update navigation menu if needed
4. Add breadcrumb support
5. Implement error boundaries
6. Write tests for the page

### Integrating New UI Components
1. Install PatternFly component if available
2. Create custom wrapper if needed
3. Add TypeScript types
4. Implement responsive behavior
5. Add accessibility attributes
6. Test across different devices
7. Document usage examples

### Styling Guidelines
- Use PatternFly design tokens for consistency
- Implement CSS modules for component-specific styles
- Support both light and dark themes
- Ensure responsive design principles
- Follow mobile-first approach
- Use CSS custom properties for dynamic theming