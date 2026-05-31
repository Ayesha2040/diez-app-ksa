// In local dev, Vite proxies /api → localhost:8000/api (see vite.config.js)
// In production, both frontend and backend are served from the same origin
export const API = "/api";

export const SEV = {
  critical: { label: "Critical", color: "#A32D2D", bg: "#FCEBEB", fg: "#791F1F" },
  high:     { label: "High",     color: "#D85A30", bg: "#FAECE7", fg: "#712B13" },
  medium:   { label: "Medium",   color: "#BA7517", bg: "#FAEEDA", fg: "#633806" },
  low:      { label: "Low",      color: "#639922", bg: "#EAF3DE", fg: "#27500A" },
  info:     { label: "Info",     color: "#888780", bg: "#F1EFE8", fg: "#5F5E5A" },
};
