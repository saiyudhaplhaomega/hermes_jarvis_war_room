/** WebSocket client with channel multiplexing, auto-reconnect, fallbacks. */
class WsClient {
  constructor(url) {
    this.url = url;
    this.ws = null;
    this.connected = false;
    this.reconnectDelay = 1000;
    this.subscriptions = new Set();
    this.handlers = {}; // channel -> [fn]
    this.pollInterval = null;
  }

  open() {
    try {
      this.ws = new WebSocket(this.url);
    } catch (e) {
      this.fallback();
      return;
    }
    this.ws.onopen = () => {
      this.connected = true;
      this.reconnectDelay = 1000;
      if (this.subscriptions.size) {
        this.send({subscribe: [...this.subscriptions]});
      }
      this._notify('system', {type:'connected'});
    };
    this.ws.onmessage = (ev) => {
      let msg; try { msg = JSON.parse(ev.data); } catch(e){ return; }
      const ch = msg.channel || 'all';
      this._notify(ch, msg);
    };
    this.ws.onclose = () => { this.connected=false; this._reconnect(); };
    this.ws.onerror = () => { this.connected=false; };
  }

  send(obj) { if(this.ws && this.connected) this.ws.send(JSON.stringify(obj)); }
  subscribe(channel) {
    this.subscriptions.add(channel);
    if(this.connected) this.send({subscribe: [...this.subscriptions]});
  }
  on(channel, fn) {
    if(!this.handlers[channel]) this.handlers[channel]=[];
    this.handlers[channel].push(fn);
  }
  _notify(ch, payload) {
    (this.handlers[ch] || []).forEach(fn => fn(payload));
    (this.handlers['all'] || []).forEach(fn => fn(payload));
  }

  _reconnect() {
    setTimeout(()=>{ this.open(); }, this.reconnectDelay);
    this.reconnectDelay = Math.min(this.reconnectDelay*2, 30000);
  }

  fallback() {
    // fallback: long-polling the cache endpoint
    this._notify('system', {type:'fallback', detail:'poll'});
    this.pollInterval = setInterval(async() => {
      try {
        const r = await fetch(API+'/dashboard/cache?token='+TOKEN);
        const d = await r.json();
        this._notify('snapshot', d);
      } catch(e){}
    }, 5000);
  }
  close() { if(this.ws){this.ws.close();} if(this.pollInterval){clearInterval(this.pollInterval);} }
}
