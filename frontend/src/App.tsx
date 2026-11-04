import { useEffect, useMemo, useState } from "react";
import { api, saveFile, type UpdateView } from "./api/client";
import { CandidateDrawer } from "./components/CandidateDrawer";
import { ConfirmCard } from "./components/ConfirmCard";
import { Conversation, suggestions } from "./components/Conversation";
import { Header } from "./components/Header";
import { ResumesPanel } from "./components/ResumesPanel";
import { Results } from "./components/Results";
import { RolePanel } from "./components/RolePanel";
import { SessionsDrawer } from "./components/SessionsDrawer";
import { SettingsDrawer } from "./components/SettingsDrawer";
import { SetupScreen } from "./components/SetupScreen";
import { useSession } from "./useSession";

function HowItWorks() {
  return (
    <section className="card how">
      <h2>How it works</h2>
      <ol>
        <li>
          <b>Every resume is scored</b>: semantic and keyword search, and the must-have checks.
        </li>
        <li>
          <b>The shortlist is reviewed in depth</b>: a verdict per requirement, backed by a quote from the resume.
        </li>
        <li>
          <b>A fixed rule recommends</b> whom to interview; the model only explains. You decide.
        </li>
      </ol>
    </section>
  );
}

/** After Quit: the app no longer runs, so this page has nothing to talk to. */
function Stopped() {
  return (
    <main className="setup">
      <section className="card">
        <h2>Resume Shortlister has stopped</h2>
        <p>You can close this tab. Your screenings are saved: start Resume Shortlister again to go on with them.</p>
        <p className="muted">
          In a terminal: <code>resume-shortlister web</code>
        </p>
      </section>
    </main>
  );
}

export function App() {
  const session = useSession();
  const { status, snapshot, activity, busy, pending, error } = session;
  const [selected, setSelected] = useState<string | null>(null);
  const [panel, setPanel] = useState<"sessions" | "settings" | null>(null);
  const [changingModel, setChangingModel] = useState(false);
  const [stopped, setStopped] = useState(false);
  const [update, setUpdate] = useState<UpdateView | null>(null);

  useEffect(() => {
    api.update().then(setUpdate, () => undefined); // no notice when it cannot be checked
  }, []);
  const sessionId = snapshot?.session_id ?? "";
  const openQuestions = snapshot?.open_questions ?? [];
  const messages = snapshot?.messages ?? [];

  // Made once per candidate: the drawer loads again when they change.
  const drawer = useMemo(
    () =>
      selected && {
        load: () => api.candidate(sessionId, selected),
        prepareQuestions: () => api.questions(sessionId, selected),
      },
    [sessionId, selected],
  );

  const quit = () => {
    if (!window.confirm("Quit Resume Shortlister? Your screenings are saved.")) return;
    api.quit().then(
      () => setStopped(true),
      (e) => window.alert(e instanceof Error ? e.message : String(e)),
    );
  };

  if (stopped) return <Stopped />;

  const header = (
    <Header
      status={status}
      busy={busy}
      settingUp={Boolean(status?.needs_setup)}
      update={update?.available ? update.latest : null}
      onNew={() => void session.open(null)}
      onSessions={() => setPanel("sessions")}
      onSettings={() => setPanel("settings")}
      onQuit={quit}
    />
  );
  const settingsDrawer = panel === "settings" && (
    <SettingsDrawer
      load={api.settings}
      update={update}
      onChangeModel={() => {
        setPanel(null);
        setChangingModel(true);
      }}
      onClose={() => setPanel(null)}
    />
  );

  if (status?.needs_setup || changingModel) {
    return (
      <>
        {header}
        <SetupScreen
          load={api.setupOptions}
          save={api.saveSetup}
          onDone={(saved) => {
            session.setStatus(saved);
            setChangingModel(false);
          }}
          onCancel={status?.needs_setup ? undefined : () => setChangingModel(false)}
        />
        {settingsDrawer}
      </>
    );
  }

  return (
    <>
      {header}
      {status && !status.ready && <div className="banner problem">{status.problem}</div>}
      {snapshot?.notice && <div className="banner">{snapshot.notice}</div>}
      {error && (
        <div className="banner problem" role="alert">
          {error}
        </div>
      )}
      <main className="layout">
        <aside>
          <ResumesPanel resumes={snapshot?.resumes ?? null} busy={busy || !snapshot} onFiles={session.upload} onFolder={session.loadFolder} />
          <RolePanel busy={busy || !snapshot} onSubmit={session.send} />
        </aside>
        <div className="main">
          {snapshot && <Results snapshot={snapshot} onDownload={session.downloadReport} onSelect={setSelected} />}
          {messages.length > 0 || busy ? (
            <Conversation
              messages={messages}
              activity={activity}
              busy={busy}
              pending={pending}
              suggestions={snapshot ? suggestions(snapshot) : []}
              lastReply={
                openQuestions.length > 0 && (
                  <ConfirmCard questions={openQuestions} busy={busy} onConfirm={() => session.send("yes")} onChange={session.send} />
                )
              }
              onSend={session.send}
            />
          ) : (
            <HowItWorks />
          )}
        </div>
      </main>
      {drawer && (
        <CandidateDrawer
          {...drawer}
          onDownload={(detail) => saveFile(new Blob([detail.report], { type: "text/markdown" }), `${detail.id}.md`)}
          onClose={() => setSelected(null)}
        />
      )}
      {panel === "sessions" && (
        <SessionsDrawer
          current={sessionId}
          load={api.sessions}
          onOpen={(id) => {
            setPanel(null);
            void session.open(id);
          }}
          onNew={() => {
            setPanel(null);
            void session.open(null);
          }}
          onDelete={session.remove}
          onClose={() => setPanel(null)}
        />
      )}
      {settingsDrawer}
      <footer>
        Resume Shortlister {status?.version} · runs on this computer · recommendations are a starting point; people make the
        hiring decisions
      </footer>
    </>
  );
}
