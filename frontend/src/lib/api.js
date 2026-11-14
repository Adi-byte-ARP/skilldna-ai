// In dev, Vite proxies /auth /users /resume etc. to localhost:8000 (see vite.config.js).
// In production, set VITE_API_URL to your deployed backend URL.
const BASE_URL = import.meta.env.VITE_API_URL || "";
const TOKEN_KEY = "skilldna_token";
const USER_KEY = "skilldna_user";

export function normalizeGithubInput(value) {
  const raw = (value || "").trim();
  if (!raw) return "";

  const withoutAt = raw.replace(/^@/, "");
  const withoutProtocol = withoutAt.replace(/^https?:\/\/(?:www\.)?github\.com\//i, "");
  const withoutDomain = withoutProtocol.replace(/^github\.com\//i, "");
  return withoutDomain.split(/[/?#]/)[0].trim();
}

// The roles list never changes during a visit, so every page shares one request for it.
let rolesRequest = null;
function cachedRoles() {
  if (!rolesRequest) {
    rolesRequest = request("/mock/roles").catch((e) => {
      rolesRequest = null; // try again next time if it failed
      throw e;
    });
  }
  return rolesRequest;
}

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = { ...(options.headers || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  // A 401 on a request that carried a token means the sign-in has expired. End the session cleanly
  // so the user is sent to sign in, rather than being left on pages that cannot load.
  if (res.status === 401 && token) {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem("skilldna_user");
    window.dispatchEvent(new Event("skilldna:session-expired"));
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // ignore
    }
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export const auth = {
  register: (name, email, password) =>
    request("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password }),
    }),

  login: (email, password) =>
    request("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    }),

  me: () => request("/auth/me"),

  saveSession: (token, user) => {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },

  clearSession: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },

  getStoredUser: () => {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  },

  getToken,
};

export const api = {
  createUser: (name, email) =>
    request("/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email }),
    }),

  getUser: (userId) => request(`/users/${userId}`),

  uploadResume: (userId, file) => {
    const form = new FormData();
    form.append("file", file);
    return request(`/resume/upload/${userId}`, { method: "POST", body: form });
  },

  analyzeGithub: (userId, username) => {
    const normalized = normalizeGithubInput(username);
    if (!normalized) {
      throw new Error("Enter a GitHub username or URL first.");
    }

    return request(`/github/analyze/${userId}?username=${encodeURIComponent(normalized)}`, {
      method: "POST",
    });
  },

  uploadLinkedin: (userId, file) => {
    const form = new FormData();
    form.append("file", file);
    return request(`/ocr/linkedin/${userId}`, { method: "POST", body: form });
  },

  uploadCertificates: (userId, files) => {
    const form = new FormData();
    for (const file of files) form.append("files", file);
    return request(`/ocr/certificate/${userId}`, { method: "POST", body: form });
  },

  getReport: (userId) => request(`/report/${userId}`),

  mockRoles: () => cachedRoles(),
  mockStart: (kind, role) =>
    request("/mock/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind, role }),
    }),
  mockGet: (id) => request(`/mock/sessions/${id}`),
  mockEvent: (id, type) =>
    request(`/mock/sessions/${id}/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type }),
    }),
  mockAnswer: (id, questionId, answer) =>
    request(`/mock/sessions/${id}/answers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question_id: questionId, answer }),
    }),
  mockSubmit: (id) => request(`/mock/sessions/${id}/submit`, { method: "POST" }),
  mockSessions: () => request("/mock/sessions"),

  planGet: (role, mode = "gap") => request(`/plan?role=${encodeURIComponent(role)}&mode=${mode}`),
  planToggleTask: (taskKey, done, role, mode = "gap") =>
    request(`/plan/tasks/${encodeURIComponent(taskKey)}?role=${encodeURIComponent(role)}&mode=${mode}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ done }),
    }),
  interviewStart: (role) =>
    request("/interview/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role }),
    }),
  interviewAnswer: (sessionId, answer, secondsSpent) =>
    request(`/interview/sessions/${sessionId}/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer, seconds_spent: secondsSpent ?? null }),
    }),
  interviewList: () => request("/interview/sessions"),
  assistantChat: (message, history) =>
    request("/assistant/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history }),
    }),
  profileGet: () => request("/profile"),
  profileSetTargetRole: (role) =>
    request("/profile/target-role", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role }),
    }),
  profileSettings: (assistantContext) =>
    request("/profile/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ assistant_context: assistantContext }),
    }),
  profileRecommendations: () => request("/profile/recommendations"),
  // A file download, so it is not parsed as JSON. Uses the same token and base URL as everything else.
  profileExport: async () => {
    const token = getToken();
    const res = await fetch(`${BASE_URL}/profile/export`, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
    if (!res.ok) throw new Error("Could not export your data.");
    return res.blob();
  },
  assistantAction: (action) =>
    request("/assistant/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    }),
  interviewEvent: (sessionId, type) =>
    request(`/interview/sessions/${sessionId}/event`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type }),
    }),
  planPhaseTest: (index, role, mode = "gap") => request(`/plan/phases/${index}/test?role=${encodeURIComponent(role)}&mode=${mode}`),
  planPhaseSubmit: (index, role, answers, mode = "gap") =>
    request(`/plan/phases/${index}/test?role=${encodeURIComponent(role)}&mode=${mode}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers }),
    }),
  dailyToday: (role, localHour) =>
    request(`/daily/today?role=${encodeURIComponent(role)}${localHour == null ? "" : `&local_hour=${localHour}`}`),
  planHistory: () => request("/plan/history"),
  dailyAnswer: (challengeId, answerIndex, role, answerText) =>
    request("/daily/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        challenge_id: challengeId,
        answer_index: answerIndex ?? null,
        answer_text: answerText ?? null,
        role,
      }),
    }),
  dailyHistory: () => request("/daily/history"),
  dailyStatus: (localHour) =>
    request(`/daily/status?local_hour=${encodeURIComponent(localHour)}`),
  remindersGet: () => request("/reminders/settings"),
  remindersSet: (emailOptIn) =>
    request("/reminders/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email_opt_in: emailOptIn }),
    }),
};

export { BASE_URL };
