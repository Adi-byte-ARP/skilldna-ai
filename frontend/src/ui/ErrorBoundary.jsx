import { Component } from "react";

/**
 * Catches an error in its children and shows a recoverable message instead of a blank page.
 * `resetKey` (for example the current path) clears the error when it changes.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null, resetKey: props.resetKey };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  // A new resetKey (say, another page) clears a previous error.
  static getDerivedStateFromProps(props, state) {
    if (props.resetKey !== state.resetKey) return { resetKey: props.resetKey, error: null };
    return null;
  }

  componentDidCatch(error, info) {
    console.error("Page error:", error, info?.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div role="alert" className="mx-auto max-w-lg px-6 py-24 text-center">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-signal-coral">Something went wrong</p>
        <h1 className="mt-3 font-display text-2xl font-medium">This page could not be shown.</h1>
        <p className="mt-3 text-sm text-ink-soft">Your data is safe. Try again, or go back to the dashboard.</p>
        <div className="mt-6 flex justify-center gap-3">
          <button
            type="button"
            onClick={() => this.setState({ error: null })}
            className="rounded-full bg-ink px-5 py-2.5 font-display text-sm text-paper"
          >
            Try again
          </button>
          <a href="#/app" className="rounded-full border border-line px-5 py-2.5 font-display text-sm">
            Dashboard
          </a>
        </div>
      </div>
    );
  }
}
