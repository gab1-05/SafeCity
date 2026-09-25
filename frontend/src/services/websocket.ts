type WebSocketMessage = {
  type: string;
  payload: unknown;
};

type MessageHandler<T = unknown> = (payload: T) => void;

/** Console helper — `warn` is allowed by the project's no-console lint rule. */
const log = (...args: unknown[]) => console.warn("[WS]", ...args);

class WebSocketService {
  private ws: WebSocket | null = null;
  private url: string = "";
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private reconnectDelay: number = 1000;
  private handlers: Map<string, Set<MessageHandler<never>>> = new Map();
  private isConnecting: boolean = false;
  private shouldReconnect: boolean = true;

  connect(token?: string) {
    if (this.ws?.readyState === WebSocket.OPEN || this.isConnecting) return;

    const wsUrl = import.meta.env.VITE_WS_URL ?? "ws://localhost:18081/ws/";
    this.url = token ? `${wsUrl}?token=${token}` : wsUrl;
    this.isConnecting = true;
    this.shouldReconnect = true;

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        log("Connected");
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.emit("connected", {});
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data as string);
          this.emit(message.type, message.payload);
        } catch (e) {
          console.warn("[WS] Failed to parse message:", e);
        }
      };

      this.ws.onclose = (event) => {
        log("Disconnected:", event.code, event.reason);
        this.isConnecting = false;
        this.emit("disconnected", { code: event.code, reason: event.reason });

        if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
          log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
          setTimeout(() => this.connect(), delay);
        }
      };

      this.ws.onerror = (error) => {
        console.error("[WS] Error:", error);
        this.emit("error", error);
      };
    } catch (e) {
      console.error("[WS] Failed to create connection:", e);
      this.isConnecting = false;
    }
  }

  disconnect() {
    this.shouldReconnect = false;
    if (this.ws) {
      this.ws.close(1000, "Client disconnect");
      this.ws = null;
    }
  }

  send(type: string, payload: unknown) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, payload }));
    } else {
      console.warn("[WS] Cannot send, not connected");
    }
  }

  on<T = unknown>(type: string, handler: MessageHandler<T>) {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set());
    }
    this.handlers.get(type)!.add(handler as MessageHandler<never>);

    return () => this.off(type, handler);
  }

  off<T = unknown>(type: string, handler: MessageHandler<T>) {
    this.handlers.get(type)?.delete(handler as MessageHandler<never>);
  }

  private emit(type: string, payload: unknown) {
    this.handlers.get(type)?.forEach((handler) => {
      try {
        (handler as MessageHandler)(payload);
      } catch (e) {
        console.error(`[WS] Handler error for ${type}:`, e);
      }
    });
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

export const wsService = new WebSocketService();

export function useWebSocket() {
  const subscribe = <T = unknown>(type: string, handler: MessageHandler<T>) => {
    return wsService.on(type, handler);
  };

  const unsubscribe = <T = unknown>(type: string, handler: MessageHandler<T>) => {
    wsService.off(type, handler);
  };

  const send = (type: string, payload: unknown) => {
    wsService.send(type, payload);
  };

  return { subscribe, unsubscribe, send, isConnected: wsService.isConnected };
}

export function initializeWebSocket() {
  const token = localStorage.getItem("safecity.access");
  if (token) {
    wsService.connect(token);
  }
}
