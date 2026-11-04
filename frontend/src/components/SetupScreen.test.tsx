import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ApiError, type ProviderOption, type SetupOptions, type SetupRequest, type Status } from "../api/client";
import { SetupScreen } from "./SetupScreen";

const provider = (name: string, label: string, extra: Partial<ProviderOption> = {}): ProviderOption => ({
  name,
  label,
  key_var: `${name.toUpperCase()}_API_KEY`,
  key_set: false,
  default_model: "some-model",
  help_url: `https://${name}.example/keys`,
  installed: true,
  install_hint: `pip install 'resume-shortlister[${name}]'`,
  ...extra,
});

const options: SetupOptions = {
  providers: [
    provider("openai", "OpenAI"),
    provider("anthropic", "Anthropic", { key_set: true }),
    provider("google", "Google Gemini", { installed: false }),
    provider("ollama", "Ollama", { key_var: null, default_model: null, help_url: "https://ollama.com/download" }),
  ],
  current: "openai",
  env_file: "~/.resume-shortlister/.env",
};
const ready: Status = { version: "1.3.0", model: "OpenAI gpt-5.6-terra", embedder: "local", ready: true, problem: null, needs_setup: false };

function setup(save: (choice: SetupRequest) => Promise<Status>, onCancel?: () => void) {
  const done: Status[] = [];
  render(<SetupScreen load={() => Promise.resolve(options)} save={save} onDone={(s) => done.push(s)} onCancel={onCancel} />);
  return done;
}

test("a first start: choose the provider, paste the key, start", async () => {
  const saved: SetupRequest[] = [];
  const done = setup((choice) => {
    saved.push(choice);
    return Promise.resolve(ready);
  });
  expect(await screen.findByText("Set up Resume Shortlister")).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Cancel" })).toBeNull(); // there is nothing to go back to
  expect(screen.getByRole("link", { name: "Make one on OpenAI's website" }).getAttribute("href")).toBe("https://openai.example/keys");
  expect(screen.getByText(/Your key is sent only to OpenAI/)).toBeTruthy();

  const key = screen.getByLabelText("OpenAI API key") as HTMLInputElement;
  expect(key.type).toBe("password");
  fireEvent.change(key, { target: { value: "sk-proj-abc" } });
  fireEvent.click(screen.getByRole("button", { name: "Save and start" }));
  await waitFor(() => expect(done).toEqual([ready]));
  expect(saved).toEqual([{ provider: "openai", api_key: "sk-proj-abc", model: "" }]);
});

test("a provider not installed cannot be chosen; a saved key may be kept", async () => {
  setup(() => Promise.resolve(ready), () => {});
  expect(await screen.findByText("AI provider and key")).toBeTruthy();
  expect((screen.getByLabelText(/Google Gemini/) as HTMLInputElement).disabled).toBe(true);
  expect(screen.getByText(/not installed \(pip install/)).toBeTruthy();
  fireEvent.click(screen.getByLabelText(/Anthropic/));
  expect((screen.getByLabelText("Anthropic API key") as HTMLInputElement).placeholder).toBe("Saved already: leave empty to keep it");
});

test("Ollama: a model instead of a key, and nothing leaves the computer", async () => {
  setup(() => Promise.resolve(ready));
  fireEvent.click(await screen.findByLabelText(/Ollama/));
  expect(screen.queryByLabelText(/API key/)).toBeNull();
  expect(screen.getByLabelText("Model")).toBeTruthy();
  expect(screen.getByText(/Nothing leaves this computer: the model runs on it\./)).toBeTruthy();
});

test("what the server refused is shown, and nothing is done", async () => {
  const done = setup(() => Promise.reject(new ApiError("Paste your OpenAI API key.", 422)));
  fireEvent.click(await screen.findByRole("button", { name: "Save and start" }));
  expect((await screen.findByRole("alert")).textContent).toBe("Paste your OpenAI API key.");
  expect(done).toEqual([]);
});
