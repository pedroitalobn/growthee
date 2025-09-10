'use client'

import React, { useState, useRef, useEffect } from 'react'
// Card components removed - using simple div structure
import { Button } from '@/components/ui/button'
import { ScrollArea } from '../ui/scroll-area'
import { Avatar, AvatarFallback } from '../ui/avatar'
import { Separator } from '../ui/separator'
import { PromptInput, PromptInputTextarea, PromptInputActions, PromptInputAction } from '../ui/prompt-input'
import { Send, Bot, User, Loader2, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: Date
}

const getAIResponse = (userMessage: string): string => {
  const responses: string[] = [
    'Ótima pergunta! Vou analisar isso para você.',
    'Entendi sua necessidade. Aqui está minha sugestão...',
    'Baseado nos dados disponíveis, posso recomendar...',
    'Essa é uma estratégia interessante. Vamos explorar as possibilidades.',
    'Vou ajudar você a otimizar essa abordagem.'
  ] as const
  const randomIndex = Math.floor(Math.random() * responses.length)
  return responses[randomIndex] as string
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const scrollAreaRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]') as HTMLElement | null
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight
      }
    }
  }, [messages])

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue,
      role: 'user',
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    const currentInput = inputValue
    setInputValue('')
    setIsLoading(true)

    setTimeout(() => {
      const aiResponse: Message = {
        id: (Date.now() + 1).toString(),
        content: getAIResponse(currentInput),
        role: 'assistant',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, aiResponse])
      setIsLoading(false)
    }, 1000 + Math.random() * 2000)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleSubmit = () => {
    handleSendMessage()
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 p-0">
        <ScrollArea ref={scrollAreaRef} className="h-full">
          <div className="p-6 space-y-4">
            {messages.length === 0 ? (
              <div className="text-center py-12">
                <div className="bg-primary text-primary-foreground p-4 mx-auto mb-4 w-fit">
                  <Sparkles className="h-8 w-8" />
                </div>
                <h3 className="text-xl font-semibold mb-2">
                  Bem-vindo ao Growthee AI
                </h3>
                <p className="text-muted-foreground mb-8">
                  Faça uma pergunta ou escolha uma das sugestões abaixo para começar.
                </p>
                
                <div className="grid gap-3 max-w-2xl mx-auto">
                  <h4 className="text-sm font-medium text-left mb-2">
                    💡 Perguntas de exemplo
                  </h4>
                  <div className="grid gap-2">
                    {[
                      'Como posso melhorar minha estratégia de marketing digital?',
                      'Quais são as melhores práticas para aumentar conversões?',
                      'Como analisar o comportamento dos usuários no meu site?'
                    ].map((question, index) => (
                      <button
                        key={index}
                        onClick={() => setInputValue(question)}
                        className="text-left p-3 bg-accent hover:bg-accent/80 transition-colors text-foreground w-full"
                      >
                        {question}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              messages.map((message) => (
                <div key={message.id} className={cn(
                  "flex gap-3 p-4 border",
                  message.role === 'user'
                    ? "bg-primary text-primary-foreground ml-8"
                    : "bg-accent mr-8"
                )}>
                  <Avatar className="h-8 w-8 flex-shrink-0">
                    <AvatarFallback className={cn(
                      "text-xs font-medium",
                      message.role === 'user'
                        ? "bg-primary-foreground text-primary"
                        : "bg-primary text-primary-foreground"
                    )}>
                      {message.role === 'user' ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">
                        {message.role === 'user' ? 'Você' : 'Growthee AI'}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {message.timestamp.toLocaleTimeString()}
                      </span>
                    </div>
                    <div className="text-sm leading-relaxed">
                      {message.content}
                    </div>
                  </div>
                </div>
              ))
            )}
            
            {isLoading && (
              <div className="flex gap-3 p-4 border bg-accent mr-8">
                <Avatar className="h-8 w-8 flex-shrink-0">
                  <AvatarFallback className="bg-primary text-primary-foreground">
                    <Bot className="h-4 w-4" />
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">Growthee AI</span>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    <div className="flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin text-primary" />
                      Digitando...
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>
      </div>
      
      <div className="p-4 border-t">
        <PromptInput
          value={inputValue}
          onValueChange={setInputValue}
          onSubmit={handleSubmit}
        >
          <PromptInputTextarea 
            placeholder="Digite sua mensagem..."
            className="min-h-[60px] resize-none"
            onKeyDown={handleKeyPress}
            disabled={isLoading}
          />
          <PromptInputActions>
            <PromptInputAction tooltip="Enviar mensagem">
              <Button
                onClick={handleSubmit}
                disabled={!inputValue.trim() || isLoading}
                size="sm"
              >
                <Send className="h-4 w-4" />
              </Button>
            </PromptInputAction>
          </PromptInputActions>
        </PromptInput>
        
        <div className="flex items-center justify-center mt-3 text-xs text-muted-foreground">
          Growthee AI pode cometer erros. Considere verificar informações importantes.
        </div>
      </div>
    </div>
  )
}