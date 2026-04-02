import React, { useEffect } from 'react';
import { ChatWindow } from './components/ChatWindow';
import { useConversationStore } from './store';
import './App.css';

const App: React.FC = () => {
  const { setConnected, setConversationId } = useConversationStore();

  useEffect(() => {
    // Initialize WebSocket connection
    const conversationId = `conv-${Date.now()}`;
    setConversationId(conversationId);

    const ws = new WebSocket(`ws://localhost:8000/ws`);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setConnected(true);
    };

    ws.onmessage = (event) => {
      console.log('WebSocket message:', event.data);
      const message = JSON.parse(event.data);
      // Handle incoming messages
    };

    ws.onerror = (event) => {
      console.error('WebSocket error:', event);
      setConnected(false);
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
      setConnected(false);
    };

    return () => {
      ws.close();
    };
  }, [setConnected, setConversationId]);

  return (
    <div className="App">
      <ChatWindow />
    </div>
  );
};

export default App;
