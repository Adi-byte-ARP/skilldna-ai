import { describe, it, expect } from "vitest";
import { checkGmail, passwordChecks, passwordIsStrong, checkFullName } from "../lib/accountRules";

describe("Gmail check", () => {
  it.each([
    ["adityapattar@gmail.com", true],
    ["ADITYA.PATTAR@Gmail.com", true],
    ["a.b@gmail.com", false],
    ["x@gmail.com", false],
    [".abc.def@gmail.com", false],
    ["ab..cdef@gmail.com", false],
    ["abc@yahoo.com", false],
    ["adityapattar@gmail.co", false],
    ["aditya_pattar@gmail.com", false],
    ["", false],
  ])("%s -> %s", (address, ok) => {
    expect(checkGmail(address).ok).toBe(ok);
  });

  it("returns the normalised address", () => {
    expect(checkGmail("  Aditya.Pattar@GMAIL.com ").value).toBe("aditya.pattar@gmail.com");
  });
});

describe("password checklist", () => {
  it("marks each rule as met or not", () => {
    const checks = passwordChecks("weak");
    expect(checks.find((c) => c.label.startsWith("At least 8")).ok).toBe(false);
    expect(checks.find((c) => c.label.startsWith("A symbol")).ok).toBe(false);
  });

  it("accepts a strong password", () => {
    expect(passwordIsStrong("TestPass123!", "someone@gmail.com")).toBe(true);
  });

  it("rejects a password that contains the Gmail name", () => {
    expect(passwordIsStrong("Pattar2026!Xy", "pattar2026@gmail.com")).toBe(false);
  });

  it("rejects common passwords", () => {
    expect(passwordIsStrong("Password1!", "someone@gmail.com")).toBe(true);
    expect(passwordIsStrong("password123", "someone@gmail.com")).toBe(false);
  });
});

describe("full name check", () => {
  it("needs a first and a last name", () => {
    expect(checkFullName("Aditya Pattar").ok).toBe(true);
    expect(checkFullName("Aditya").ok).toBe(false);
    expect(checkFullName("Aditya123 Pattar").ok).toBe(false);
  });
});
