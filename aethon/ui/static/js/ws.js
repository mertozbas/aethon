/**
 * AETHON Dashboard — Multiplexed WebSocket Manager
 *
 * Single WebSocket connection to /ws/dashboard.
 * Topic-based pub/sub with auto-reconnect (exponential backoff).
 *
 * Protocol:
 *   Client → Server: {"channel":"subscribe","topics":["messages","logs","telemetry","agents"]}
 *   Server → Client: {"channel":"<topic>","data":{...}}
 */

const INITIAL_DELAY = 500;
const MAX_DELAY = 15000;
const BACKOFF_FACTOR = 1.8;

export class DashboardWS {
  constructor() {
    /** @type {WebSocket|null} */
    this._ws = null;
    /** @type {Map<string, Set<Function>>} topic → callbacks */
    this._listeners = new Map();
    /** @type {Set<string>} topics to subscribe on (re)connect */
    this._topics = new Set();
    /** @type {number} current reconnect delay */
    this._delay = INITIAL_DELAY;
    /** @type {number|null} reconnect timer */
    this._timer = null;
    /** @type {boolean} */
    this._intentionalClose = false;
    /** @type {string} */
    this._state = 'disconnected'; // disconnected | connecting | connected

    // Multiple state change callbacks
    /** @type {Set<Function>} */
    this._stateCallbacks = new Set();
  }

  /**
   * Build WebSocket URL from current page location.
   * @returns {string}
   */
  _buildUrl() {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${proto}//${location.host}/ws/dashboard`;
  }

  /**
   * Connect to the WebSocket server.
   */
  connect() {
    if (this._ws && (this._ws.readyState === WebSocket.OPEN || this._ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this._intentionalClose = false;
    this._setState('connecting');

    try {
      this._ws = new WebSocket(this._buildUrl());
    } catch (e) {
      console.error('[WS] Failed to create WebSocket:', e);
      this._scheduleReconnect();
      return;
    }

    this._ws.onopen = () => {
      console.log('[WS] Connected');
      this._delay = INITIAL_DELAY;
      this._setState('connected');

      // Re-subscribe to all topics
      if (this._topics.size > 0) {
        this._sendSubscription();
      }
    };

    this._ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        const channel = msg.channel;
        const data = msg.data;

        if (!channel) return;

        const cbs = this._listeners.get(channel);
        if (cbs) {
          for (const cb of cbs) {
            try {
              cb(data, channel);
            } catch (e) {
              console.error(`[WS] Listener error on "${channel}":`, e);
            }
          }
        }
      } catch (e) {
        // Non-JSON message — ignore
      }
    };

    this._ws.onclose = (event) => {
      console.log(`[WS] Closed (code=${event.code})`);
      this._ws = null;

      if (!this._intentionalClose) {
        this._setState('disconnected');
        this._scheduleReconnect();
      } else {
        this._setState('disconnected');
      }
    };

    this._ws.onerror = (event) => {
      console.error('[WS] Error:', event);
      // onclose will fire after this — reconnect handled there
    };
  }

  /**
   * Disconnect and stop reconnecting.
   */
  disconnect() {
    this._intentionalClose = true;
    if (this._timer) {
      clearTimeout(this._timer);
      this._timer = null;
    }
    if (this._ws) {
      this._ws.close();
      this._ws = null;
    }
    this._setState('disconnected');
  }

  /**
   * Subscribe to a topic channel.
   * @param {string} topic
   * @param {Function} callback - Called with (data, channel) when event arrives
   * @returns {Function} unsubscribe function
   */
  subscribe(topic, callback) {
    if (!this._listeners.has(topic)) {
      this._listeners.set(topic, new Set());
    }
    this._listeners.get(topic).add(callback);

    // Track topic for (re)connection subscription messages
    const hadTopic = this._topics.has(topic);
    this._topics.add(topic);

    // If newly added topic and we're connected, send subscribe message
    if (!hadTopic && this._ws && this._ws.readyState === WebSocket.OPEN) {
      this._sendSubscription();
    }

    // Return unsubscribe function
    return () => {
      const cbs = this._listeners.get(topic);
      if (cbs) {
        cbs.delete(callback);
        if (cbs.size === 0) {
          this._listeners.delete(topic);
        }
      }
    };
  }

  /**
   * Send a JSON message to the server.
   * @param {Object} msg
   */
  send(msg) {
    if (this._ws && this._ws.readyState === WebSocket.OPEN) {
      this._ws.send(JSON.stringify(msg));
    }
  }

  /**
   * Register a state change callback. Returns unsubscribe function.
   * @param {Function} cb — Called with (newState)
   * @returns {Function} unsubscribe
   */
  onStateChange(cb) {
    this._stateCallbacks.add(cb);
    return () => this._stateCallbacks.delete(cb);
  }

  /**
   * Get current connection state.
   * @returns {string}
   */
  get state() {
    return this._state;
  }

  /**
   * Check if connected.
   * @returns {boolean}
   */
  get connected() {
    return this._state === 'connected';
  }

  // --- Private ---

  _setState(newState) {
    if (this._state !== newState) {
      this._state = newState;
      for (const cb of this._stateCallbacks) {
        try {
          cb(newState);
        } catch (e) {
          console.error('[WS] onStateChange error:', e);
        }
      }
    }
  }

  _sendSubscription() {
    this.send({
      channel: 'subscribe',
      topics: Array.from(this._topics)
    });
  }

  _scheduleReconnect() {
    if (this._timer) return;
    const delay = Math.min(this._delay, MAX_DELAY);
    console.log(`[WS] Reconnecting in ${delay}ms...`);
    this._timer = setTimeout(() => {
      this._timer = null;
      this._delay = Math.min(this._delay * BACKOFF_FACTOR, MAX_DELAY);
      this.connect();
    }, delay);
  }
}

/** Singleton instance */
export const ws = new DashboardWS();
