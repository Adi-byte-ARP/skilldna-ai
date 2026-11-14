import { useContext } from "react";
import { Link, NavLink } from "react-router-dom";
import { AuthContext } from "../context/authContextValue";
import { APP_NAV } from "./nav";

/*
 * The one header for every signed-in page. The current page is highlighted, so the user
 * always knows where they are and can move between the practice areas.
 */
export default function AppHeader({ width } = {}) {
  const auth = useContext(AuthContext);
  const user = auth?.user;
  const initial = (user?.name || user?.email || "A").trim().charAt(0).toUpperCase() || "A";

  return (
    <header className="sticky top-0 z-40 flex w-full items-center justify-between border-b border-line bg-paper/85 px-6 py-3.5 backdrop-blur-md md:px-10">
      {/* Logo Group (Left) */}
      <Link
        to="/app"
        aria-label="SkillDNA.AI"
        className="flex shrink-0 items-baseline gap-2 font-display text-lg font-semibold tracking-tight text-ink transition-colors hover:opacity-90"
      >
        <span
          className="inline-block h-2.5 w-2.5 rounded-full bg-helix-teal align-baseline"
          aria-hidden="true"
        />
        <span>
          SkillDNA<span className="text-helix-teal">.AI</span>
        </span>
      </Link>

      {/* Navigation Group (Center) */}
      <nav
        aria-label="Main"
        className="flex min-w-0 items-center justify-center gap-4 overflow-x-auto py-1 md:gap-8"
      >
        {APP_NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              `shrink-0 whitespace-nowrap rounded-full px-4 py-1.5 font-display text-sm font-medium transition-colors duration-200 ${
                isActive
                  ? "bg-ink text-paper"
                  : "text-ink-soft hover:bg-line/50 hover:text-ink"
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* Avatar (Right) */}
      <div className="flex shrink-0 items-center justify-end">
        {user && (
          <NavLink
            to="/app/profile"
            aria-label="Your profile"
            data-testid="user-avatar"
            title="Profile, appearance and log out"
            className="flex h-9 w-9 items-center justify-center rounded-full bg-ink font-display text-sm font-medium text-paper transition-colors duration-300 hover:bg-helix-teal"
          >
            {initial}
          </NavLink>
        )}
      </div>
    </header>
  );
}
