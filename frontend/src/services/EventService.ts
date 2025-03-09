// Serviço para gerenciar eventos em tempo real usando Server-Sent Events (SSE)
import { toast } from '@/components/ui/use-toast';

// Definição dos tipos de eventos
export interface RouletteNumberEvent {
  type: 'new_number';
  roleta_id: string;
  roleta_nome: string;
  numero: number;
  timestamp: string;
}

export interface ConnectedEvent {
  type: 'connected';
  message: string;
}

export type EventData = RouletteNumberEvent | ConnectedEvent;

// Tipo para callbacks de eventos
export type RouletteEventCallback = (event: RouletteNumberEvent) => void;

// Serviço de eventos
class EventService {
  private static instance: EventService;
  private eventSource: EventSource | null = null;
  private listeners: Map<string, Set<RouletteEventCallback>> = new Map();
  private isConnected: boolean = false;
  private connectionAttempts: number = 0;
  private reconnectTimeout: number | null = null;
  private backoffTime: number = 1000; // Tempo inicial de backoff em ms

  // URL do endpoint SSE com prioridade para variáveis de ambiente
  private getServerUrl(): string {
    // 1. Verificar se existe uma variável de ambiente configurada (prioridade máxima)
    const envServerUrl = import.meta.env.VITE_SSE_SERVER_URL;
    if (envServerUrl) {
      console.log(`Usando URL do servidor de eventos da variável de ambiente: ${envServerUrl}`);
      return envServerUrl;
    }
    
    // 2. Detecção automática baseada no ambiente
    const isProduction = window.location.hostname !== 'localhost' && 
                         window.location.hostname !== '127.0.0.1';
    
    if (isProduction) {
      // No ambiente de produção, tente primeiro usar a mesma origem que o frontend
      // Isso funciona se o backend estiver no mesmo domínio
      const protocol = window.location.protocol;
      const host = window.location.host;
      
      console.log(`Ambiente de produção detectado. Tentando usar ${protocol}//${host}/events`);
      console.log('IMPORTANTE: Se o frontend está na Vercel e o backend está em outro lugar, configure VITE_SSE_SERVER_URL nas variáveis de ambiente');
      
      return `${protocol}//${host}/events`;
    } else {
      // Em desenvolvimento, usar localhost na porta 5000
      console.log('Ambiente de desenvolvimento detectado, usando http://localhost:5000/events');
      return 'http://localhost:5000/events';
    }
  }

  private constructor() {
    this.connect();
    console.log('EventService inicializado');
  }

  public static getInstance(): EventService {
    if (!EventService.instance) {
      EventService.instance = new EventService();
    }
    return EventService.instance;
  }

  private connect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }

    try {
      const serverUrl = this.getServerUrl();
      console.log(`Conectando ao servidor de eventos: ${serverUrl}`);
      this.eventSource = new EventSource(serverUrl);

      this.eventSource.onopen = () => {
        console.log('Conexão SSE estabelecida');
        this.isConnected = true;
        this.connectionAttempts = 0;
        this.backoffTime = 1000; // Resetar o tempo de backoff
        
        toast({
          title: "Conexão em tempo real estabelecida",
          description: "Você receberá atualizações automáticas das roletas",
          variant: "default"
        });
      };

      this.eventSource.onerror = (error) => {
        console.error('Erro na conexão SSE:', error);
        this.isConnected = false;
        
        if (this.eventSource) {
          this.eventSource.close();
          this.eventSource = null;
        }

        // Tentar reconectar com backoff exponencial
        this.connectionAttempts++;
        const delay = Math.min(this.backoffTime * Math.pow(1.5, this.connectionAttempts - 1), 30000);
        
        console.log(`Tentando reconectar em ${delay}ms (tentativa ${this.connectionAttempts})`);
        
        if (this.reconnectTimeout) {
          clearTimeout(this.reconnectTimeout);
        }
        
        this.reconnectTimeout = window.setTimeout(() => {
          this.connect();
        }, delay);
        
        if (this.connectionAttempts > 3) {
          toast({
            title: "Problemas de conexão",
            description: "Tentando reconectar ao servidor de eventos...",
            variant: "destructive"
          });
        }
      };

      this.eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as EventData;
          
          if (data.type === 'new_number') {
            console.log(`Novo número recebido para ${data.roleta_nome}: ${data.numero}`);
            this.notifyListeners(data);
          } else if (data.type === 'connected') {
            console.log('Conexão confirmada pelo servidor:', data.message);
          }
        } catch (error) {
          console.error('Erro ao processar evento:', error);
        }
      };
    } catch (error) {
      console.error('Erro ao criar conexão SSE:', error);
      this.isConnected = false;
    }
  }

  // Adiciona um listener para eventos de uma roleta específica
  public subscribe(roletaNome: string, callback: RouletteEventCallback): void {
    if (!this.listeners.has(roletaNome)) {
      this.listeners.set(roletaNome, new Set());
    }

    this.listeners.get(roletaNome)?.add(callback);
    console.log(`Inscrito para eventos da roleta: ${roletaNome}`);
  }

  // Remove um listener
  public unsubscribe(roletaNome: string, callback: RouletteEventCallback): void {
    const callbacks = this.listeners.get(roletaNome);
    if (callbacks) {
      callbacks.delete(callback);
      if (callbacks.size === 0) {
        this.listeners.delete(roletaNome);
      }
    }
  }

  // Notifica os listeners sobre um novo evento
  private notifyListeners(event: RouletteNumberEvent): void {
    // Notificar listeners da roleta específica
    const roletaListeners = this.listeners.get(event.roleta_nome);
    if (roletaListeners) {
      roletaListeners.forEach(callback => {
        try {
          callback(event);
        } catch (error) {
          console.error(`Erro ao chamar callback para roleta ${event.roleta_nome}:`, error);
        }
      });
    }

    // Notificar listeners que escutam todas as roletas (usando "*" como chave)
    const globalListeners = this.listeners.get('*');
    if (globalListeners) {
      globalListeners.forEach(callback => {
        try {
          callback(event);
        } catch (error) {
          console.error('Erro ao chamar callback global:', error);
        }
      });
    }
  }

  // Fecha a conexão - chamar quando o aplicativo for encerrado
  public disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    this.isConnected = false;
    console.log('Desconectado do servidor de eventos');
  }
}

export default EventService; 