import React from 'react';
import { useChat } from '../contexts/ChatContext';
import { useProject } from '../contexts/ProjectContext';
import { useDashboard } from '../contexts/DashboardContext';
import { PanelHeader } from './PanelHeader';

interface Props {
  fullPage?: boolean;
}

export default function DispatchTerminal({ fullPage }: Props) {
  const { state, setMode, setAgent, sendMessage, confirmExec, cancelExec, clear } = useChat();
  const { projects, project, setProject } = useProject();
  const { cache } = useDashboard();
  const [text, setText] = React.useState('');
  const [lastErr, setLastErr] = React.useState('');
  const [queueNotice, setQueueNotice] = React.useState('');
  const scrollRef = React.useRef<HTMLDivElement>(null);
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);
  const stickyFocusRef = React.useRef(false);
  const queuedMessageRef = React.useRef('');

  const modes = [
    { key: 'standard', label: '⚒ Standard' },
    { key: 'grill', label: '🔥 Grill Mode' },
    { key: 'thinking', label: '🧠 Thinking' },
    { key: 'spike', label: '🧪 Spike' },
    { key: 'plan', label: '🗺 Plan' },
    { key: 'tdd', label: '✅ TDD' },
    { key: 'debug', label: '🐞 Debug' },
    { key: 'council', label: '⚖ Council' },
    { key: 'boss', label: '👁 Boss' },
    { key: 'codex', label: '⌨ Code' },
  ];

  // Auto-scroll to bottom on new messages
  React.useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [state.messages.length, state.sending]);

  const focusInput = (delay = 0) => {
    window.setTimeout(() => {
      const el = textareaRef.current;
      if (!el) return;
      el.focus({ preventScroll: true });
    }, delay);
  };

  React.useEffect(() => {
    if (fullPage) focusInput(0);
  }, [fullPage]);

  React.useEffect(() => {
    if (!state.sending && stickyFocusRef.current) {
      focusInput(0);
      focusInput(50);
    }
  }, [state.sending]);

  const shouldAllowBlur = (nextTarget: EventTarget | null) => {
    if (!nextTarget || !(nextTarget instanceof HTMLElement)) return false;
    return Boolean(nextTarget.closest('button, select, a, [role="button"], [data-allow-chat-blur="true"]'));
  };

  const handleBlur = (e: React.FocusEvent<HTMLTextAreaElement>) => {
    if (!stickyFocusRef.current) return;
    if (shouldAllowBlur(e.relatedTarget)) return;
    focusInput(0);
  };

  const sendNow = async (msg: string) => {
    setLastErr('');
    setQueueNotice('');
    stickyFocusRef.current = true;
    try {
      await sendMessage(msg, project?.slug, state.agent);
    } finally {
      focusInput(0);
      focusInput(50);
    }
  };

  React.useEffect(() => {
    if (state.sending) return;
    const queued = queuedMessageRef.current.trim();
    if (!queued) return;
    queuedMessageRef.current = '';
    setQueueNotice('Sending queued message…');
    window.setTimeout(() => {
      void sendNow(queued);
    }, 0);
  }, [state.sending]);

  const handleSend = async () => {
    const msg = text.trim();
    if (!msg) return;
    stickyFocusRef.current = true;
    setText('');
    focusInput(0);
    focusInput(25);

    if (state.sending) {
      queuedMessageRef.current = msg;
      setQueueNotice('Queued — will send after the current reply finishes.');
      return;
    }

    await sendNow(msg);
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      stickyFocusRef.current = true;
      handleSend();
      focusInput(0);
      focusInput(25);
    }
  };

  const handleConfirm = () => {
    if (state.pendingExec) confirmExec(state.pendingExec);
  };

  const handleCancel = () => {
    if (state.pendingExec) cancelExec(state.pendingExec);
  };

  const chatContent = (
    <>
      <div className="flex gap-2 mb-2">
        <select
          className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs"
          value={state.agent}
          onChange={(e) => setAgent(e.target.value)}
          aria-label="Agent"
          title="Select Jarvis agent"
        >
          {(cache?.agents?.length ? cache.agents : [{ name: 'jarvis', status: 'running', source: '', model: 'kimi-k2.6' }]).map((a) => (
            <option key={a.name} value={a.name}>
              🤖 {a.name}{a.model ? ` · ${a.model}` : ''}
            </option>
          ))}
        </select>
        <select
          className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs"
          value={state.mode}
          onChange={(e) => setMode(e.target.value)}
          aria-label="Mode"
        >
          {modes.map((m) => (
            <option key={m.key} value={m.key}>{m.label}</option>
          ))}
        </select>
        <select
          className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs"
          value={project?.slug || ''}
          onChange={(e) => {
            const p = projects.find((x) => x.slug === e.target.value);
            setProject(p || null);
          }}
          aria-label="Project"
        >
          <option value="">📦 No Project ({projects.length})</option>
          {projects.map((p) => (
            <option key={p.slug} value={p.slug}>{p.name}</option>
          ))}
        </select>
      </div>

      <div className="text-xs text-gray-400 mb-1">
        Agent: {state.agent} | Tier-{state.tier} {state.mode} routing | Cost: {state.cost} | Budget: $50.00
      </div>

      {project && (
        <div className="text-[11px] text-blue-200 bg-blue-950/30 border border-blue-900/60 rounded px-2 py-1 mb-2">
          Project context locked: <span className="font-semibold">{project.slug}</span>
          {project.repo_path ? <span> · repo: {project.repo_path}</span> : null}
          <span> · agents should treat this as the existing selected repo.</span>
        </div>
      )}

      <div
        ref={scrollRef}
        className={`overflow-y-auto rounded border border-gray-800 bg-gray-950 p-2 mb-2 space-y-1 ${fullPage ? 'flex-1' : 'h-48'}`}
      >
        {state.messages.length === 0 && (
          <div className="text-xs text-gray-500 italic">
            Select a project and mode, then start a conversation.
          </div>
        )}
        {state.messages.map((msg) => (
          <div
            key={msg.id || msg.ts}
            className={`text-xs rounded px-2 py-1 ${
              msg.role === 'user'
                ? 'bg-blue-900/30'
                : msg.role === 'assistant'
                ? 'bg-gray-800'
                : 'bg-gray-900/50 italic'
            }`}
          >
            <span className="font-bold">
              {msg.role === 'user' ? 'You' : msg.agent || msg.role}
            </span>{' '}
            {msg.role === 'assistant' && msg.mode && (
              <span className="text-gray-500">[{msg.mode}]</span>
            )}
            <span className="text-gray-400 ml-1">{msg.content}</span>
            {msg.exec && (
              <div className="mt-1 p-1 bg-yellow-900/30 border border-yellow-700/50 rounded">
                <span className="text-yellow-400">⚠ Pending execution</span>
                <div className="flex gap-2 mt-1">
                  <button
                    onClick={handleConfirm}
                    className="px-2 py-0.5 bg-green-700 hover:bg-green-600 rounded text-[10px]"
                  >
                    ✓ Confirm
                  </button>
                  <button
                    onClick={handleCancel}
                    className="px-2 py-0.5 bg-red-700 hover:bg-red-600 rounded text-[10px]"
                  >
                    ✗ Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
        {state.sending && (
          <div className="text-xs text-gray-500 italic">Thinking…</div>
        )}
      </div>

      {lastErr && (
        <div className="text-xs text-red-400 mb-1">{lastErr}</div>
      )}
      {queueNotice && (
        <div className="text-xs text-yellow-300 mb-1">{queueNotice}</div>
      )}

      <div className="flex gap-2">
        <textarea
          ref={textareaRef}
          className="flex-1 bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs focus:outline-none focus:border-blue-500"
          rows={2}
          placeholder={`[${state.mode}] Can execute — type your message`}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKey}
          onBlur={handleBlur}
          autoFocus={fullPage}
        />
        <button
          onClick={handleSend}
          disabled={!text.trim()}
          className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 px-3 py-1 rounded text-xs font-bold"
        >
          {state.sending ? 'Queue' : 'Send'}
        </button>
        <button
          onClick={clear}
          className="bg-gray-800 hover:bg-gray-700 px-2 py-1 rounded text-xs"
          title="Clear chat"
        >
          🗑
        </button>
      </div>
    </>
  );

  if (fullPage) {
    return (
      <div className="flex flex-col h-full px-4 py-2">
        {chatContent}
      </div>
    );
  }

  return (
    <div className="card md:col-span-2 lg:col-span-2">
      <PanelHeader title="Dispatch Terminal" />
      {chatContent}
    </div>
  );
}
