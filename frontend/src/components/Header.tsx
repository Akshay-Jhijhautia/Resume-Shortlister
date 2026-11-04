import type { Status } from "../api/client";

interface Props {
  status: Status | null;
  busy: boolean; // a turn is running: the session cannot change
  settingUp: boolean; // the first start's setup: there are no screenings yet
  update: string | null; // a newer version, when there is one
  onNew: () => void;
  onSessions: () => void;
  onSettings: () => void;
  onQuit: () => void;
}

export function Header({ status, busy, settingUp, update, onNew, onSessions, onSettings, onQuit }: Props) {
  return (
    <header className="topbar">
      <div className="brand">
        Resume <span>Shortlister</span>
      </div>
      <div className="tagline">Explainable resume screening · it ranks and explains, the recruiter decides</div>
      <nav className="actions" aria-label="Sessions and settings">
        {update && (
          <button type="button" className="update" onClick={onSettings} title="How to update">
            Update available: {update}
          </button>
        )}
        {!settingUp && (
          <>
            <button type="button" onClick={onNew} disabled={busy}>
              New screening
            </button>
            <button type="button" onClick={onSessions} disabled={busy}>
              Sessions
            </button>
          </>
        )}
        <button
          type="button"
          className="status"
          onClick={onSettings}
          title={status?.problem ?? "Settings"}
          aria-label={status ? `Settings: ${status.model}, ${status.ready ? "ready" : "not ready"}` : "Settings"}
        >
          {status && <span className={`dot ${status.ready ? "ready" : "problem"}`} />}
          {status ? status.model : "Settings"} <span aria-hidden="true">⚙</span>
        </button>
        <button type="button" onClick={onQuit} disabled={busy} title="Stop Resume Shortlister on this computer">
          Quit
        </button>
      </nav>
    </header>
  );
}
