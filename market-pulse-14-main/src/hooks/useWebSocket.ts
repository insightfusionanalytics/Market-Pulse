import { useEffect, useRef, useState, useCallback } from "react";
import { getWebSocketUrl, clearToken } from "@/lib/api";
import { Stock, WebSocketMessage } from "@/types";

const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_INTERVAL = 5000;
const PING_INTERVAL = 30000;

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
  const flushTimer = useRef<ReturnType<typeof setInterval>>();
  const latestMessageRef = useRef<WebSocketMessage | null>(null);
  const hasInitialAppliedRef = useRef(false);

  const applyMessage = useCallback((message: WebSocketMessage) => {
    if (!Array.isArray(message.data)) {
      return;
    }
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

  const cleanup = useCallback(() => {
    if (pingTimer.current) clearInterval(pingTimer.current);
    if (flushTimer.current) clearInterval(flushTimer.current);
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    if (wsRef.current) {
      wsRef.current.onclose = null; // prevent reconnect on intentional close
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
      // Start ping keepalive
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
          const shouldApplyImmediately = !hasInitialAppliedRef.current;
          latestMessageRef.current = message;
          if (shouldApplyImmediately) {
            applyMessage(message);
            hasInitialAppliedRef.current = true;
            latestMessageRef.current = null;
          }
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = (event) => {
      setConnected(false);
      if (pingTimer.current) clearInterval(pingTimer.current);

      // If 401/auth error, redirect to login
      if (event.code === 4001 || event.reason?.includes("auth")) {
        clearToken();
        window.location.href = "/";
        return;
      }

      // Auto-reconnect
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
    if (flushTimer.current) {
      clearInterval(flushTimer.current);
    }

    const ms = Math.max(1, refreshIntervalSeconds) * 1000;
    flushTimer.current = setInterval(() => {
      if (latestMessageRef.current) {
        applyMessage(latestMessageRef.current);
        latestMessageRef.current = null;
      }
    }, ms);

    return () => {
      if (flushTimer.current) {
        clearInterval(flushTimer.current);
      }
    };
  }, [refreshIntervalSeconds, applyMessage]);

  useEffect(() => {
    if (enabled) {
      connect();
    }
    return cleanup;
  }, [enabled, connect, cleanup]);

  return { stocks, shortlist, connected, lastUpdate, isFrozen, freezeMessage };
}
