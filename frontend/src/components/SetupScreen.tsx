import { useEffect, useState, type FormEvent } from "react";
import type { SetupOptions, SetupRequest, Status } from "../api/client";

const message = (error: unknown) => (error instanceof Error ? error.message : String(error));

interface Props {
  load: () => Promise<SetupOptions>;
  save: (choice: SetupRequest) => Promise<Status>;
  onDone: (status: Status) => void;
  onCancel?: () => void; // opened from Settings, with a model already set up
}

/** The chat model's provider and key, chosen in the page and saved on this computer: what a
 * first start asks for, and what Settings changes. */
export function SetupScreen({ load, save, onDone, onCancel }: Props) {
  const [options, setOptions] = useState<SetupOptions | null>(null);
  const [provider, setProvider] = useState("openai");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    load().then(
      (loaded) => {
        setOptions(loaded);
        setProvider(loaded.current);
      },
      (e) => setError(message(e)),
    );
  }, [load]);

  const chosen = options?.providers.find((option) => option.name === provider);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    save({ provider, api_key: apiKey, model })
      .then(onDone, (e) => setError(message(e)))
      .finally(() => setSaving(false));
  };

  return (
    <main className="setup">
      <section className="card">
        <h2>{onCancel ? "AI provider and key" : "Set up Resume Shortlister"}</h2>
        <p>
          Resume Shortlister reads resumes against your job description with an AI model. Choose the provider you have an
          account with, and paste its API key (a password for programs, made on the provider's website).
        </p>
        <p className="muted">
          An API key is not part of a ChatGPT or Claude subscription: the provider bills its use separately.
        </p>
        {options && chosen && (
          <form onSubmit={submit}>
            <fieldset className="choices">
              <legend>AI provider</legend>
              {options.providers.map((option) => (
                <label key={option.name} className="choice">
                  <input
                    type="radio"
                    name="provider"
                    value={option.name}
                    checked={provider === option.name}
                    disabled={!option.installed}
                    onChange={() => {
                      setProvider(option.name);
                      setError(null);
                    }}
                  />
                  <span>
                    {option.label}
                    {option.key_var === null && <span className="muted"> · runs on this computer, no key</span>}
                    {!option.installed && <span className="muted"> · not installed ({option.install_hint})</span>}
                  </span>
                </label>
              ))}
            </fieldset>

            {chosen.key_var !== null && (
              <div className="field">
                <label htmlFor="api-key">{chosen.label} API key</label>
                <input
                  id="api-key"
                  aria-describedby="api-key-help"
                  type="password"
                  autoComplete="off"
                  spellCheck={false}
                  value={apiKey}
                  onChange={(event) => setApiKey(event.target.value)}
                  placeholder={chosen.key_set ? "Saved already: leave empty to keep it" : "Paste your key"}
                />
                <span id="api-key-help" className="muted">
                  No key yet?{" "}
                  <a href={chosen.help_url} target="_blank" rel="noreferrer">
                    Make one on {chosen.label}'s website
                  </a>
                  .
                </span>
              </div>
            )}

            {chosen.default_model === null && (
              <div className="field">
                <label htmlFor="model">Model</label>
                <input
                  id="model"
                  aria-describedby="model-help"
                  spellCheck={false}
                  value={model}
                  onChange={(event) => setModel(event.target.value)}
                  placeholder="e.g. llama3.3"
                />
                <span id="model-help" className="muted">
                  <a href={chosen.help_url} target="_blank" rel="noreferrer">
                    Install {chosen.label}
                  </a>
                  , download a model (<code>ollama pull llama3.3</code>), and keep {chosen.label} running.
                </span>
              </div>
            )}

            {error && (
              <div className="banner problem" role="alert">
                {error}
              </div>
            )}
            <div className="row">
              <button type="submit" className="primary" disabled={saving}>
                {saving ? "Saving…" : onCancel ? "Save" : "Save and start"}
              </button>
              {onCancel && (
                <button type="button" className="secondary" onClick={onCancel}>
                  Cancel
                </button>
              )}
            </div>
          </form>
        )}
        {error && !options && (
          <div className="banner problem" role="alert">
            {error}
          </div>
        )}
        {options && chosen && (
          <p className="muted">
            Saved only on this computer, in <code>{options.env_file}</code>.{" "}
            {chosen.key_var === null
              ? "Nothing leaves this computer: the model runs on it."
              : `Your key is sent only to ${chosen.label}, and so is resume text, without names or contact details, when it reviews candidates.`}
          </p>
        )}
      </section>
    </main>
  );
}
