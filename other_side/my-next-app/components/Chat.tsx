"use client";

import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, X, MessageSquare, Loader2, User, Bot } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface ChatProps {
  tasks: any[];
  onAddTasks: (newTasks: any[]) => void;
}

export default function Chat({ tasks, onAddTasks }: ChatProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [...messages, userMessage],
          tasks
        }),
      });

      const data = await response.json();
      if (data.content) {
        let content = data.content;
        
        // Parse commands
        const commandRegex = /\[COMMAND:ADD_TASKS\]([\s\S]*?)\[\/COMMAND\]/;
        const match = content.match(commandRegex);
        
        if (match) {
          try {
            const suggestedTasks = JSON.parse(match[1]);
            onAddTasks(suggestedTasks);
            content = content.replace(commandRegex, '\n\n*I\'ve added some suggested tasks to your planner!*');
          } catch (e) {
            console.error("Failed to parse suggested tasks", e);
          }
        }

        setMessages(prev => [...prev, { role: 'assistant', content }]);
      }
    } catch (error) {
      console.error("Chat failed", error);
      setMessages(prev => [...prev, { role: 'assistant', content: "Sorry, I encountered an error. Please try again." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {/* Chat Toggle Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-8 right-8 w-14 h-14 bg-indigo-600 rounded-full flex items-center justify-center shadow-lg shadow-indigo-500/40 hover:bg-indigo-500 transition-all z-40 active:scale-95"
      >
        <MessageSquare className="text-white w-6 h-6" />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, x: 300 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 300 }}
            className="fixed top-0 right-0 h-full w-full md:w-96 bg-zinc-950 border-l border-zinc-800 z-50 flex flex-col shadow-2xl"
          >
            {/* Header */}
            <div className="p-4 border-b border-zinc-800 flex items-center justify-between bg-zinc-900/50">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
                  <Sparkles className="text-white w-4 h-4" />
                </div>
                <span className="font-bold text-white">Lumina AI</span>
              </div>
              <button onClick={() => setIsOpen(false)} className="p-2 hover:bg-zinc-800 rounded-full transition-colors">
                <X className="w-5 h-5 text-zinc-400" />
              </button>
            </div>

            {/* Messages */}
            <div ref={scrollRef} className="flex-grow overflow-y-auto p-4 space-y-6 scrollbar-thin scrollbar-thumb-zinc-800">
              {messages.length === 0 && (
                <div className="text-center py-10 px-6">
                  <Bot className="w-12 h-12 text-indigo-500/50 mx-auto mb-4" />
                  <h3 className="text-white font-bold mb-2">How can I help you today?</h3>
                  <p className="text-zinc-500 text-sm">Ask me to help you plan your day, suggest tasks, or just chat about productivity.</p>
                </div>
              )}
              {messages.map((m, i) => (
                <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`flex gap-3 max-w-[85%] ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
                    <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center ${m.role === 'user' ? 'bg-zinc-800' : 'bg-indigo-600/20'}`}>
                      {m.role === 'user' ? <User className="w-4 h-4 text-zinc-400" /> : <Bot className="w-4 h-4 text-indigo-500" />}
                    </div>
                    <div className={`p-3 rounded-2xl text-sm leading-relaxed ${
                      m.role === 'user' 
                        ? 'bg-indigo-600 text-white rounded-tr-none' 
                        : 'bg-zinc-900 text-zinc-200 rounded-tl-none border border-zinc-800'
                    }`}>
                      {m.content}
                    </div>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="flex gap-3">
                    <div className="w-8 h-8 rounded-full bg-indigo-600/20 flex items-center justify-center">
                      <Bot className="w-4 h-4 text-indigo-500" />
                    </div>
                    <div className="bg-zinc-900 border border-zinc-800 p-3 rounded-2xl rounded-tl-none">
                      <Loader2 className="w-4 h-4 text-indigo-500 animate-spin" />
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Input */}
            <div className="p-4 border-t border-zinc-800 bg-zinc-900/50">
              <div className="relative">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  placeholder="Type a message..."
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-xl py-3 pl-4 pr-12 text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors"
                />
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || isLoading}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-indigo-500 hover:text-indigo-400 disabled:opacity-50 transition-colors"
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
              <p className="text-[10px] text-center text-zinc-600 mt-3 uppercase tracking-widest font-bold">
                Lumina AI can help you plan
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
