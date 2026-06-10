export const colors = {
  bg: "#F8FAFC",
  surface: "#FFFFFF",
  surfaceMuted: "#F1F5F9",
  border: "#E2E8F0",
  text: "#0F172A",
  textMuted: "#64748B",
  textSubtle: "#94A3B8",

  primary: "#0F172A",
  primaryFg: "#FFFFFF",

  accent: "#2563EB",
  accentMuted: "#DBEAFE",

  success: "#16A34A",
  successMuted: "#DCFCE7",
  warning: "#D97706",
  warningMuted: "#FEF3C7",
  danger: "#DC2626",
  dangerMuted: "#FEE2E2",
} as const;

export const radius = {
  sm: 6,
  md: 10,
  lg: 14,
  xl: 18,
  full: 999,
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const;

export const fontSize = {
  xs: 12,
  sm: 13,
  base: 15,
  md: 16,
  lg: 18,
  xl: 22,
  xxl: 28,
  display: 34,
} as const;

export const fontWeight = {
  regular: "400",
  medium: "500",
  semibold: "600",
  bold: "700",
} as const;

export const shadow = {
  card: {
    shadowColor: "#0F172A",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 6,
    elevation: 1,
  },
} as const;
