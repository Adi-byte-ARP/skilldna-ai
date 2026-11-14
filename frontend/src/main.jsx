import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.jsx";
import { initTheme } from "./lib/theme";

initTheme(); // set data-theme before the first render, so there is no flash of the wrong palette

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>
);
