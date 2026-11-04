import { fireEvent, render, screen } from "@testing-library/react";
import type { SettingsView, UpdateView } from "../api/client";
import { SettingsDrawer } from "./SettingsDrawer";

const settings: SettingsView = {
  version: "1.3.0",
  model: "OpenAI gpt-5.6-terra",
  api_key: "OPENAI_API_KEY",
  api_key_set: false,
  embeddings: "local:ibm-granite/granite-embedding-small-english-r2",
  shortlist_size: 10,
  screening_rounds: 3,
  interview_threshold: 75,
  data_home: "~/.resume-shortlister",
  reports_dir: "~/.resume-shortlister/reports",
  env_file: "~/.resume-shortlister/.env",
  stored_answers: { answers: 120, reused: 340, size_mb: 1.4 },
  update_check: true,
};
const noUpdate: UpdateView = { current: "1.3.0", latest: "1.3.0", available: false, checks: true, how: "curl … | sh" };

const drawer = (overrides: Partial<SettingsView> = {}, update: UpdateView | null = noUpdate, onChangeModel = () => {}) =>
  render(
    <SettingsDrawer
      load={() => Promise.resolve({ ...settings, ...overrides })}
      update={update}
      onChangeModel={onChangeModel}
      onClose={() => {}}
    />,
  );

test("settings in effect, a missing key, and where to change them", async () => {
  drawer();
  expect((await screen.findByText("OPENAI_API_KEY is not set")).className).toBe("bad");
  expect(screen.getByText("(computed on this computer)", { exact: false })).toBeTruthy();
  expect(screen.getByText(/120 stored, reused 340 times/)).toBeTruthy();
  expect(screen.getByText("~/.resume-shortlister/.env")).toBeTruthy();
});

test("a provider needing no key, and answers not stored", async () => {
  drawer({ api_key: null, stored_answers: null });
  expect(await screen.findByText("none needed")).toBeTruthy();
  expect(screen.getByText("not stored (LLM_CACHE=false)")).toBeTruthy();
});

test("the provider and key are changed in the app", async () => {
  const changed: boolean[] = [];
  drawer({}, noUpdate, () => changed.push(true));
  fireEvent.click(await screen.findByRole("button", { name: "Change AI provider or key" }));
  expect(changed).toEqual([true]);
});

test("updates: what is checked, and how to update when a version is out", async () => {
  const { unmount } = drawer();
  expect(await screen.findByText(/Version 1.3.0, the newest\. Once a day the app asks PyPI/)).toBeTruthy();
  unmount();

  drawer({}, { ...noUpdate, latest: "1.4.0", available: true });
  expect(await screen.findByText("Version 1.4.0 is available")).toBeTruthy();
  expect(screen.getByText("curl … | sh")).toBeTruthy();
});

test("the update check turned off", async () => {
  drawer({ update_check: false }, { ...noUpdate, latest: null, checks: false });
  expect(await screen.findByText(/Not checking for updates/)).toBeTruthy();
});
