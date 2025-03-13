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

  private constructor() {
    // Adicionar listener global para logging de todos os eventos
    this.subscribe('*', (event: RouletteNumberEvent) => {
      console.log(`[EventService][GLOBAL] Evento recebido para roleta: ${event.roleta_nome}, número: ${event.numero}`);
    });
    
    // Iniciar com SSE para comunicação em tempo real verdadeiro
    console.log('[EventService] Iniciando com SSE para eventos em tempo real');
    this.connect();
  }

  public static getInstance(): EventService {
    if (!EventService.instance) {
      EventService.instance = new EventService();
    }
    return EventService.instance;
  }

  // Obtém a URL do servidor de eventos com proxy CORS, se necessário
  private getServerUrl(): string {
    // Usando um proxy CORS alternativo que pode ser melhor para SSE
    const originalUrl = 'https://short-mammals-help.loca.lt/api/events';
    const proxyUrl = `https://api.allorigins.win/raw?url=${encodeURIComponent(originalUrl)}`;
    
    // Usando o proxy na tentativa de resolver o CORS
    console.log(`[EventService] Usando URL via proxy CORS alternativo: ${proxyUrl}`);
    return proxyUrl;
  }

  private connect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }

    try {
      const serverUrl = this.getServerUrl();
      console.log(`[EventService] Tentando conexão SSE simplificada: ${serverUrl}`);
      
      // Usar EventSource com configuração mínima
      this.eventSource = new EventSource(serverUrl);

      this.eventSource.onopen = () => {
        console.log('[EventService] Conexão SSE estabelecida com sucesso!');
        this.isConnected = true;
        this.connectionAttempts = 0;
        this.backoffTime = 1000; // Resetar o tempo de backoff
        
        toast({
          title: "Conexão em tempo real estabelecida",
          description: "Você receberá atualizações instantâneas das roletas",
          variant: "default"
        });
      };

      this.eventSource.onerror = (error) => {
        console.error('[EventService] Erro na conexão SSE, tentando reconectar...');
        this.isConnected = false;
        
        if (this.eventSource) {
          this.eventSource.close();
          this.eventSource = null;
        }

        // Incrementar tentativas
        this.connectionAttempts++;
        
        // Limitar a 10 tentativas para não ficar eternamente
        if (this.connectionAttempts > 10) {
          console.error('[EventService] Máximo de tentativas atingido. Por favor, recarregue a página.');
          return;
        }
        
        // Backoff mais rápido, mas com intervalos crescentes
        const delay = Math.min(1000 * this.connectionAttempts, 8000);
        
        console.log(`[EventService] Tentando reconectar em ${Math.round(delay/1000)}s (tentativa ${this.connectionAttempts})`);
        
        if (this.reconnectTimeout) {
          clearTimeout(this.reconnectTimeout);
        }
        
        this.reconnectTimeout = window.setTimeout(() => {
          this.connect();
        }, delay);
      };

      this.eventSource.onmessage = (event) => {
        try {
          // Parsing inicial do JSON
          let parsedData;
          try {
            parsedData = JSON.parse(event.data);
          } catch (e) {
            console.error('[EventService] Erro ao fazer parse do JSON');
            return;
          }
          
          // Adaptar formato da nova API para o formato esperado
          let data: EventData;
          
          // Verificar formato e adaptar conforme necessário
          if (parsedData.type && parsedData.type === 'new_number') {
            // Já está no formato esperado
            data = parsedData as RouletteNumberEvent;
          } else if (parsedData.roleta_nome && parsedData.numero !== undefined) {
            // Formato da nova API: converter para o formato esperado
            data = {
              type: 'new_number',
              roleta_id: parsedData.roleta_id || parsedData.id || 'unknown-id',
              roleta_nome: parsedData.roleta_nome,
              numero: Number(parsedData.numero),
              timestamp: parsedData.timestamp || new Date().toISOString()
            };
          } else if (parsedData.message && typeof parsedData.message === 'string') {
            // Evento de conexão ou outro evento informativo
            data = {
              type: 'connected',
              message: parsedData.message
            };
          } else {
            return;
          }
          
          if (data.type === 'new_number') {
            console.log(`[EventService] Novo número em tempo real: ${data.roleta_nome} - ${data.numero}`);
            this.notifyListeners(data);
          }
        } catch (error) {
          console.error('[EventService] Erro ao processar evento SSE');
        }
      };
    } catch (error) {
      console.error('[EventService] Erro ao criar conexão SSE, tentando novamente...');
      
      // Tentar reconectar após um breve atraso
      setTimeout(() => {
        this.connect();
      }, 2000);
    }
  }

  // Adiciona um listener para eventos de uma roleta específica
  public subscribe(roletaNome: string, callback: RouletteEventCallback): void {
    console.log(`[EventService] Inscrevendo para eventos da roleta: ${roletaNome}`);
    
    if (!this.listeners.has(roletaNome)) {
      this.listeners.set(roletaNome, new Set());
    }

    const listeners = this.listeners.get(roletaNome);
    listeners?.add(callback);
    
    const count = listeners?.size || 0;
    console.log(`[EventService] Total de listeners para ${roletaNome}: ${count}`);
    
    // Sempre verificar a conexão SSE ao inscrever um novo listener
    if (!this.isConnected || !this.eventSource) {
      console.log(`[EventService] Conexão SSE não ativa, reconectando...`);
      this.connect();
    }
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
    // Log simplificado para melhor desempenho em modo tempo real
    console.log(`[EventService] Novo número: ${event.roleta_nome} - ${event.numero}`);
    
    // Notificar listeners da roleta específica
    const roletaListeners = this.listeners.get(event.roleta_nome);
    if (roletaListeners && roletaListeners.size > 0) {
      roletaListeners.forEach(callback => {
        try {
          callback(event);
        } catch (error) {
          console.error(`[EventService] Erro ao notificar listener para ${event.roleta_nome}`);
        }
      });
    }
    
    // Notificar listeners globais (*)
    const globalListeners = this.listeners.get('*');
    if (globalListeners && globalListeners.size > 0) {
      globalListeners.forEach(callback => {
        try {
          callback(event);
        } catch (error) {
          console.error('[EventService] Erro ao notificar listener global');
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
    console.log('[EventService] Desconectado do servidor de eventos');
  }
}

export default EventService; 