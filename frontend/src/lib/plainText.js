/* Question text marks code with backticks. Strip the marks where text is read aloud or compared. */
export function plainText(text) {
  return String(text ?? "").replace(/`/g, "");
}
