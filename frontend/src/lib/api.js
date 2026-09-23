const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const TOKEN_KEY = "skilldna_token";
const USER_KEY = "skilldna_user";

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = { ...(options.headers || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
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

  analyzeGithub: (userId, username) =>
    request(`/github/analyze/${userId}?username=${encodeURIComponent(username)}`, {
      method: "POST",
    }),

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
};

export { BASE_URL };
