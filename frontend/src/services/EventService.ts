// Serviço para gerenciar eventos em tempo real usando Server-Sent Events (SSE)
import { toast } from '@/components/ui/use-toast';
import config from '@/config/env';

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
  private lastReconnectTime: number = 0;
  private reconnectMinInterval: number = 5000; // Mínimo de 5 segundos entre reconexões
  private manuallyDisconnected: boolean = false;

  // Cache de eventos para persistência durante reconexões
  private eventCache: RouletteNumberEvent[] = [];
  private maxCacheSize: number = 100;

  // Obtém a URL do servidor de eventos da configuração centralizada
  private getServerUrl(): string {
    console.log(`[EventService] Usando URL do servidor de eventos: ${config.sseServerUrl}`);
    return config.sseServerUrl;
  }

  private constructor() {
    this.connect();
    console.log('EventService inicializado');
    
    // Adicionar listener para eventos de visibilidade da página
    document.addEventListener('visibilitychange', this.handleVisibilityChange);
    
    // Adicionar listener para eventos de online/offline
    window.addEventListener('online', this.handleOnlineStatus);
    window.addEventListener('offline', this.handleOfflineStatus);
  }

  private handleVisibilityChange = () => {
    if (document.visibilityState === 'visible') {
      console.log('Página visível, verificando conexão SSE');
      if (!this.isConnected && !this.manuallyDisconnected) {
        this.reconnectWithThrottle();
      }
    }
  }

  private handleOnlineStatus = () => {
    console.log('Navegador está online, reconectando SSE se necessário');
    if (!this.isConnected && !this.manuallyDisconnected) {
      this.reconnectWithThrottle();
    }
  }

  private handleOfflineStatus = () => {
    console.log('Navegador está offline, marcando conexão como perdida');
    this.isConnected = false;
  }

  private reconnectWithThrottle() {
    const now = Date.now();
    // Evitar múltiplas reconexões muito próximas
    if (now - this.lastReconnectTime > this.reconnectMinInterval) {
      this.lastReconnectTime = now;
      this.connect();
    } else {
      console.log(`Reconexão ignorada: muito recente (última: ${now - this.lastReconnectTime}ms atrás)`);
    }
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

    if (this.manuallyDisconnected) {
      console.log('Conexão manualmente desconectada, não tentando reconectar');
      return;
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
        
        // Mostrar toast apenas na primeira conexão ou após várias tentativas
        if (this.connectionAttempts === 0 || this.connectionAttempts > 3) {
          toast({
            title: "Conexão em tempo real estabelecida",
            description: "Você receberá atualizações automáticas das roletas",
            variant: "default"
          });
        }
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
          if (!this.manuallyDisconnected) {
            this.connect();
          }
        }, delay);
        
        if (this.connectionAttempts > 3 && this.connectionAttempts % 3 === 0) {
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
            
            // Adicionar ao cache para persistência
            this.addToEventCache(data);
            
            // Notificar listeners
            this.notifyListeners(data);
          } else if (data.type === 'connected') {
            console.log('Conexão confirmada pelo servidor:', data.message);
          }
        } catch (error) {
          console.error('Erro ao processar evento:', error);
        }
      };
    } catch (error) {
      console.error('Erro ao criar EventSource:', error);
      this.scheduleReconnect();
    }
  }

  // Adicionar evento ao cache com limite de tamanho
  private addToEventCache(event: RouletteNumberEvent): void {
    this.eventCache.unshift(event); // Adiciona no início do array
    if (this.eventCache.length > this.maxCacheSize) {
      this.eventCache.pop(); // Remove o mais antigo se exceder o limite
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }
    
    const delay = Math.min(this.backoffTime * Math.pow(1.5, this.connectionAttempts), 30000);
    this.reconnectTimeout = window.setTimeout(() => {
      if (!this.manuallyDisconnected) {
        this.connect();
      }
    }, delay);
  }

  public disconnect(): void {
    this.manuallyDisconnected = true;
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    this.isConnected = false;
    console.log('Conexão SSE desconectada manualmente');
  }

  public reconnect(): void {
    this.manuallyDisconnected = false;
    this.connect();
  }

  public registerListener(rouletteId: string, callback: RouletteEventCallback): void {
    if (!this.listeners.has(rouletteId)) {
      this.listeners.set(rouletteId, new Set());
    }
    
    this.listeners.get(rouletteId)?.add(callback);
    console.log(`Listener registrado para roleta ${rouletteId}`);
    
    // Enviar eventos em cache para o novo listener
    this.sendCachedEvents(rouletteId, callback);
  }

  // Enviar eventos em cache para novos listeners
  private sendCachedEvents(rouletteId: string, callback: RouletteEventCallback): void {
    const relevantEvents = this.eventCache.filter(event => 
      event.roleta_id === rouletteId || rouletteId === '*'
    );
    
    if (relevantEvents.length > 0) {
      console.log(`Enviando ${relevantEvents.length} eventos em cache para novo listener de ${rouletteId}`);
      relevantEvents.forEach(event => {
        try {
          callback(event);
        } catch (error) {
          console.error('Erro ao enviar evento em cache para listener:', error);
        }
      });
    }
  }

  public unregisterListener(rouletteId: string, callback: RouletteEventCallback): void {
    const listeners = this.listeners.get(rouletteId);
    if (listeners) {
      listeners.delete(callback);
      if (listeners.size === 0) {
        this.listeners.delete(rouletteId);
      }
      console.log(`Listener removido para roleta ${rouletteId}`);
    }
  }

  private notifyListeners(event: RouletteNumberEvent): void {
    // Notificar listeners específicos da roleta
    const roletaId = event.roleta_id;
    const listeners = this.listeners.get(roletaId);
    
    if (listeners) {
      listeners.forEach(callback => {
        try {
          callback(event);
        } catch (error) {
          console.error(`Erro ao notificar listener para roleta ${roletaId}:`, error);
        }
      });
    }
    
    // Notificar listeners para todas as roletas (wildcard '*')
    const globalListeners = this.listeners.get('*');
    if (globalListeners) {
      globalListeners.forEach(callback => {
        try {
          callback(event);
        } catch (error) {
          console.error('Erro ao notificar listener global:', error);
        }
      });
    }
  }

  public getConnectionStatus(): boolean {
    return this.isConnected;
  }

  public getCachedEvents(): RouletteNumberEvent[] {
    return [...this.eventCache];
  }
}

export default EventService.getInstance(); 