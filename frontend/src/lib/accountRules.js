// Sign-up rules, mirrored from backend/app/services/account_rules.py.
// The server is the authority; this copy only gives the user live feedback.

const GMAIL = "gmail.com";
const LOCAL_CHARS = /^[a-z0-9.]+$/;
const LOCAL_SHAPE = /^[a-z0-9]+(?:\.[a-z0-9]+)*$/;
const SYMBOLS = /[!@#$%^&*()_+\-=[\]{};:'",.<>/?\\|`~]/;
const COMMON = new Set([
  "password", "password1", "password123", "12345678", "123456789", "qwerty123", "qwertyuiop",
  "letmein123", "welcome123", "iloveyou1", "abc12345", "admin1234", "passw0rd", "p@ssw0rd",
]);

/** Returns { ok, value, message } for a Gmail address. */
export function checkGmail(input) {
  const address = (input || "").trim().toLowerCase();
  if (!address) return { ok: false, message: "Enter your Gmail address." };
  if (address.split("@").length !== 2) return { ok: false, message: "Enter a Gmail address, for example yourname@gmail.com." };
  const [local, domain] = address.split("@");
  if (domain !== GMAIL) return { ok: false, message: "Only Gmail addresses are accepted (name@gmail.com)." };
  if (local.length < 6 || local.length > 30) return { ok: false, message: "A Gmail name is 6 to 30 characters long." };
  if (!LOCAL_CHARS.test(local)) return { ok: false, message: "A Gmail name can only use letters, numbers and dots." };
  if (!LOCAL_SHAPE.test(local)) return { ok: false, message: "A Gmail name cannot start or end with a dot, and cannot have two dots in a row." };
  return { ok: true, value: `${local}@${GMAIL}` };
}

/** Each password rule with whether it is met. The form shows these as a checklist. */
export function passwordChecks(password, email = "") {
  const local = (email || "").split("@")[0].toLowerCase();
  return [
    { label: "At least 8 characters", ok: password.length >= 8 },
    { label: "An uppercase letter", ok: /[A-Z]/.test(password) },
    { label: "A lowercase letter", ok: /[a-z]/.test(password) },
    { label: "A number", ok: /\d/.test(password) },
    { label: "A symbol such as ! @ # $ %", ok: SYMBOLS.test(password) },
    { label: "No spaces", ok: !/\s/.test(password) },
    {
      label: "Does not contain your Gmail name",
      ok: local.length < 4 || !password.toLowerCase().includes(local),
    },
    { label: "Not a common password", ok: !COMMON.has(password.toLowerCase()) },
  ];
}

export function passwordIsStrong(password, email) {
  return passwordChecks(password, email).every((c) => c.ok);
}

/** Two or more words, each starting with a letter. Documents are matched against this name. */
export function checkFullName(input) {
  const name = (input || "").trim().replace(/\s+/g, " ");
  if (!name) return { ok: false, message: "Enter your full name." };
  if (name.length > 60) return { ok: false, message: "Name is too long (60 characters at most)." };
  if (!/^[A-Za-z][A-Za-z.'\- ]*$/.test(name)) return { ok: false, message: "Name can only use letters, spaces, dots, apostrophes and hyphens." };
  const parts = name.split(" ").filter((p) => p.replace(/[.'-]/g, "").length >= 2);
  if (parts.length < 2) return { ok: false, message: "Enter your first and last name, for example Aditya Pattar." };
  return { ok: true, value: name };
}
