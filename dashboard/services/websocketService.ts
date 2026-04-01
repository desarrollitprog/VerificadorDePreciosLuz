import { getToken } from './tokenUtils';

export interface NotificacionWebSocket {
  type: string;
  data: {
    id: number;
    tipo: string;
    descripcion: string;
    dispositivo_id: string | null;
    servidor_id: number | null;
    fecha_creacion: string | null;
  };
}

type NotificacionCallback = (notificacion: NotificacionWebSocket['data']) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;
  private callbacks: NotificacionCallback[] = [];
  private isConnecting = false;

  connect() {
    const token = getToken();
    if (!token) {
      console.warn('WebSocket: No hay token disponible');
      return;
    }

    if (this.ws?.readyState === WebSocket.OPEN || this.isConnecting) {
      return;
    }

    this.isConnecting = true;
    
    const wsUrl = import.meta.env.DEV 
      ? `/ws/notificaciones?token=${token}`
      : `${import.meta.env.VITE_WS_URL || 'ws://localhost:8001'}/ws/notificaciones?token=${token}`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('WebSocket conectado');
        this.isConnecting = false;
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        try {
          const message: NotificacionWebSocket = JSON.parse(event.data);
          if (message.type === 'nueva_notificacion') {
            this.callbacks.forEach((callback) => callback(message.data));
          }
        } catch (e) {
          console.error('Error al parsear mensaje WebSocket:', e);
        }
      };

      this.ws.onclose = (event) => {
        console.log('WebSocket cerrado:', event.code, event.reason);
        this.isConnecting = false;
        this.attemptReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('Error en WebSocket:', error);
        this.isConnecting = false;
      };
    } catch (error) {
      console.error('Error al crear WebSocket:', error);
      this.isConnecting = false;
      this.attemptReconnect();
    }
  }

  private attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('WebSocket: Máximo de intentos de reconexión alcanzado');
      return;
    }

    this.reconnectAttempts++;
    console.log(`WebSocket: Intentando reconectar (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);

    setTimeout(() => {
      this.connect();
    }, this.reconnectDelay);
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.callbacks = [];
    this.reconnectAttempts = this.maxReconnectAttempts;
  }

  subscribe(callback: NotificacionCallback) {
    this.callbacks.push(callback);
    return () => {
      this.callbacks = this.callbacks.filter((cb) => cb !== callback);
    };
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

export const websocketService = new WebSocketService();
