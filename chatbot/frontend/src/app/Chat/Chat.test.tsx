import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { Chat } from './Chat';

describe('Chat Component Basic Tests', () => {
  it('should render initial welcome message', () => {
    render(<Chat />);
    expect(screen.getByText('Hello! How can I help you today?')).toBeInTheDocument();
  });

  it('should render chat input and attach button', () => {
    render(<Chat />);
    expect(screen.getByPlaceholderText('Type your message...')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /attach/i })).toBeInTheDocument();
  });

  it('should render streaming mode toggle', () => {
    render(<Chat />);
    expect(screen.getByLabelText('Streaming mode')).toBeInTheDocument();
  });

  it('should display user message when typed', async () => {
    const user = userEvent.setup();
    render(<Chat />);
    
    const input = screen.getByPlaceholderText('Type your message...');
    
    await user.type(input, 'Test message');
    expect(input).toHaveValue('Test message');
  });

  it('should have attach button available', () => {
    render(<Chat />);
    
    const attachButton = screen.getByRole('button', { name: /attach/i });
    
    // Attach button should be enabled
    expect(attachButton).toBeEnabled();
  });

  it('should toggle streaming mode', async () => {
    const user = userEvent.setup();
    render(<Chat />);
    
    const toggle = screen.getByLabelText('Streaming mode');
    
    // Initially on (default is true)
    expect(toggle).toBeChecked();
    
    // Toggle off
    await user.click(toggle);
    expect(toggle).not.toBeChecked();
    
    // Toggle on
    await user.click(toggle);
    expect(toggle).toBeChecked();
  });
});