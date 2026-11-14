const VARIANTS = {
  primary: "bg-helix-teal text-paper hover:bg-ink",
  ink: "bg-ink text-paper hover:bg-helix-teal",
  ghost: "border border-line text-ink hover:border-helix-teal hover:text-helix-teal",
  danger: "bg-signal-coral text-paper hover:opacity-90",
};
const SIZES = {
  sm: "px-3.5 py-2 text-xs",
  md: "px-5 py-2.5 text-sm",
  lg: "px-7 py-3.5 text-base",
};

/** The one button style for the app. Use variant for meaning, size for emphasis. */
export default function Button({ variant = "ink", size = "md", className = "", as: Tag = "button", ...rest }) {
  return (
    <Tag
      type={Tag === "button" ? "button" : undefined}
      className={`inline-flex items-center justify-center gap-2 rounded-full font-display font-medium transition-colors duration-200 focus-visible:outline-helix-teal disabled:cursor-not-allowed disabled:opacity-40 ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...rest}
    />
  );
}
