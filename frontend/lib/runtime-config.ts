// Live is the default. The original prototype requires an explicit opt-in.
export const API_MODE: "mock" | "live" =
  process.env.NEXT_PUBLIC_API_MODE === "mock" ? "mock" : "live";
