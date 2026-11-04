import { useEffect, useState } from "react";
import type { SettingsView, UpdateView } from "../api/client";
import { Drawer } from "./Drawer";

const message = (error: unknown) => (error instanceof Error ? error.message : String(error));
const ROUNDS = {
  1: "retrieval only",
  2: "retrieval and the deep review",
  3: "retrieval, the deep review and interview recommendations",
} as Record<number, string>;

interface Props {
  load: () => Promise<SettingsView>;
  update: UpdateView | null;
  onChangeModel: () => void; // the AI provider and key, changed in the setup screen
  onClose: () => void;
}

/** The settings in effect and where they come from. The AI provider and key are changed in
 * the app; everything else in the data home's .env file. */
export function SettingsDrawer({ load, update, onChangeModel, onClose }: Props) {
  const [settings, setSettings] = useState<SettingsView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    load().then(setSettings, (e) => setError(message(e)));
  }, [load]);

  return (
    <Drawer title="Settings" label="Settings" onClose={onClose}>
      {error && (
        <div className="banner problem" role="alert">
          {error}
        </div>
      )}
      {settings && <Details settings={settings} update={update} onChangeModel={onChangeModel} />}
    </Drawer>
  );
}

function Details({ settings, update, onChangeModel }: { settings: SettingsView; update: UpdateView | null; onChangeModel: () => void }) {
  const answers = settings.stored_answers;
  return (
    <>
      <section>
        <h3>Chat model</h3>
        <dl className="facts">
          <dt>Model</dt>
          <dd>{settings.model}</dd>
          <dt>API key</dt>
          <dd>
            {settings.api_key === null ? (
              "none needed"
            ) : settings.api_key_set ? (
              <span className="ok">{settings.api_key} is set</span>
            ) : (
              <span className="bad">{settings.api_key} is not set</span>
            )}
          </dd>
          <dt>Embeddings</dt>
          <dd>
            {settings.embeddings}
            {settings.embeddings.startsWith("local:") && <span className="muted"> (computed on this computer)</span>}
          </dd>
        </dl>
        <button type="button" className="secondary" onClick={onChangeModel}>
          Change AI provider or key
        </button>
      </section>

      <section>
        <h3>Screening</h3>
        <dl className="facts">
          <dt>Shortlist</dt>
          <dd>the top {settings.shortlist_size} after the first round</dd>
          <dt>Rounds</dt>
          <dd>
            {settings.screening_rounds}: {ROUNDS[settings.screening_rounds]}
          </dd>
          <dt>Interview</dt>
          <dd>recommended from a final score of {settings.interview_threshold}, with no must-have missing and no high risk</dd>
          <dt>Blind</dt>
          <dd>the model never sees names, contact details or personal fields</dd>
        </dl>
      </section>

      <section>
        <h3>Your data</h3>
        <dl className="facts">
          <dt>Data folder</dt>
          <dd>
            <code>{settings.data_home}</code> <span className="muted">indexes, uploads, sessions</span>
          </dd>
          <dt>Reports</dt>
          <dd>
            <code>{settings.reports_dir}</code>
          </dd>
          <dt>Model answers</dt>
          <dd>
            {answers
              ? `${answers.answers} stored, reused ${answers.reused} times (${answers.size_mb} MB): the same question gets the same answer`
              : "not stored (LLM_CACHE=false)"}
          </dd>
        </dl>
      </section>

      <section>
        <h3>Updates</h3>
        <Updates version={settings.version} checks={settings.update_check} update={update} />
      </section>

      <section>
        <h3>Other settings</h3>
        <p>
          Put them in <code>{settings.env_file}</code>, then quit and start Resume Shortlister again. For example:
        </p>
        <pre>{"SHORTLIST_SIZE=15\nSCREENING_ROUNDS=2"}</pre>
        <p className="muted">Every setting is described in docs/configuration.md.</p>
      </section>
    </>
  );
}

function Updates({ version, checks, update }: { version: string; checks: boolean; update: UpdateView | null }) {
  if (update?.available) {
    return (
      <>
        <p>
          <b>Version {update.latest} is available</b> (you have {version}). To update, click Quit, then paste this line into a
          terminal (PowerShell on Windows). It keeps your key, settings and screenings.
        </p>
        <pre className="command">{update.how}</pre>
      </>
    );
  }
  return (
    <p className="muted">
      Version {version}
      {update?.latest ? ", the newest." : "."}{" "}
      {checks
        ? "Once a day the app asks PyPI, where it is published, for the newest version number; nothing about you or your resumes is sent. RESUME_SHORTLISTER_UPDATE_CHECK=false turns this off."
        : "Not checking for updates (RESUME_SHORTLISTER_UPDATE_CHECK=false)."}
    </p>
  );
}
