import { useEffect, useRef, useState, useCallback } from "react";
import { getWebSocketUrl, clearToken } from "@/lib/api";
import { Stock, WebSocketMessage } from "@/types";

const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_INTERVAL = 5000;
const PING_INTERVAL = 30000;
const THROTTLE_MS = 200; // Max 5 UI updates per second

export function useWebSocket(enabled: boolean, refreshIntervalSeconds: number) {
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [shortlist, setShortlist] = useState<Stock[]>([]);
  const [connected, setConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<string>("");
  const [isFrozen, setIsFrozen] = useState(false);
  const [freezeMessage, setFreezeMessage] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCount = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();
  const pingTimer = useRef<ReturnType<typeof setInterval>>();

  // Throttle: buffer the latest message and flush at most every THROTTLE_MS
  const pendingMessage = useRef<WebSocketMessage | null>(null);
  const throttleTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const flushMessage = useCallback(() => {
    const message = pendingMessage.current;
    if (!message || !Array.isArray(message.data)) return;
    pendingMessage.current = null;

    setStocks(message.data);
    if (Array.isArray(message.shortlist)) {
      setShortlist(message.shortlist);
    } else {
      setShortlist(message.data.filter((s) => s.qualified));
    }
    setIsFrozen(Boolean(message.is_frozen));
    setFreezeMessage(message.freeze_message || null);
    setLastUpdate(message.timestamp || new Date().toISOString());
  }, []);

  const applyMessage = useCallback((message: WebSocketMessage) => {
    if (!Array.isArray(message.data)) return;
    pendingMessage.current = message;

    if (!throttleTimer.current) {
      // Flush immediately on first message, then throttle subsequent ones
      flushMessage();
      throttleTimer.current = setTimeout(() => {
        throttleTimer.current = null;
        if (pendingMessage.current) flushMessage();
      }, THROTTLE_MS);
    }
  }, [flushMessage]);

  const cleanup = useCallback(() => {
    if (pingTimer.current) clearInterval(pingTimer.current);
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    if (throttleTimer.current) {
      clearTimeout(throttleTimer.current);
      throttleTimer.current = null;
    }
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    cleanup();
    const url = getWebSocketUrl();
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      reconnectCount.current = 0;
      pingTimer.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, PING_INTERVAL);
    };

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        if (message.type === "update" && Array.isArray(message.data)) {
          applyMessage(message);
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = (event) => {
      setConnected(false);
      if (pingTimer.current) clearInterval(pingTimer.current);

      if (event.code === 4001 || event.reason?.includes("auth")) {
        clearToken();
        window.location.href = "/";
        return;
      }

      if (reconnectCount.current < MAX_RECONNECT_ATTEMPTS) {
        reconnectCount.current++;
        reconnectTimer.current = setTimeout(connect, RECONNECT_INTERVAL);
      }
    };

    ws.onerror = () => {
      setConnected(false);
    };
  }, [cleanup, applyMessage]);

  useEffect(() => {
    if (enabled) {
      connect();
    }
    return cleanup;
  }, [enabled, connect, cleanup]);

  return { stocks, shortlist, connected, lastUpdate, isFrozen, freezeMessage };
}
