import { useState } from 'react';
import { PanelHeader } from './PanelHeader';

export function GitHubWorkspace() {
  const [url, setUrl] = useState('');
  const [alias, setAlias] = useState('');

  return (
    <div className="card">
      <PanelHeader title="GitHub Workspace" collapsible />
      <div className="flex gap-2">
        <input
          type="text"
          placeholder="https://github.com/user/repo.git"
          value={url}
          onChange={e => setUrl(e.target.value)}
          className="flex-1 bg-gray-900 border border-gray-700 rounded px-3 py-2 text-xs"
        />
        <input
          type="text"
          placeholder="alias"
          value={alias}
          onChange={e => setAlias(e.target.value)}
          className="w-24 bg-gray-900 border border-gray-700 rounded px-3 py-2 text-xs"
        />
        <button className="bg-indigo-600 hover:bg-indigo-500 px-3 py-2 rounded text-xs font-semibold">Clone</button>
      </div>
    </div>
  );
}
