import { Component, type ReactNode } from "react";
import { Glass, TerminalLabel } from "./ui";

interface Props {
  children: ReactNode;
  /** Human-readable name of the panel being guarded, shown in the fallback. */
  panelName: string;
}

interface State {
  error: Error | null;
}

/**
 * UI Polish Sprint — Bug #1's real, general fix. Investigating the
 * Treasury black-screen bug found the actual defect (backend/app/ws_
 * manager.py never broadcast `accounts`/`activeAccountId`, silently
 * wiping them to `undefined` on the first tick after load) and fixed it
 * there — but React's own warning on that crash ("Consider adding an
 * error boundary to your tree") was correct: with no boundary anywhere
 * in this codebase, ANY future undefined-access bug in ANY of the 35
 * Command Center panels blacks out the entire app, not just that one
 * tab. This is the first error boundary in the codebase, wrapping the
 * tab content area in FullCommandCenter.tsx (keyed by tab, so switching
 * away from and back to a crashed panel gets a fresh mount instead of
 * staying stuck) so a real UI bug degrades to one broken panel with an
 * honest error message — never a black screen.
 */
export class PanelErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: { componentStack?: string | null }) {
    console.error(`[PanelErrorBoundary] ${this.props.panelName} crashed:`, error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <Glass className="p-4">
          <TerminalLabel>{this.props.panelName} — Panel Error</TerminalLabel>
          <p className="mb-2 text-cmd-text">
            This panel hit an unexpected error and couldn&apos;t render. The rest of the Command Center is unaffected — switch tabs and come back to
            try again.
          </p>
          <p className="mb-3 font-cmdmono text-[9px] text-cmd-red">{this.state.error.message}</p>
          <button
            type="button"
            onClick={() => this.setState({ error: null })}
            className="rounded-sm border border-cmd-cyan/50 px-3 py-1.5 text-[10px] uppercase tracking-wider text-cmd-cyan transition-colors hover:bg-cmd-cyan/10"
          >
            Retry
          </button>
        </Glass>
      );
    }
    return this.props.children;
  }
}
