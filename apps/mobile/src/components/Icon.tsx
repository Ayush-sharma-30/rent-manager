import { StyleSheet, Text } from "react-native";

// Lightweight, dependency-free glyph map using common Unicode symbols.
// Good enough for a prototype; swap for @expo/vector-icons later.
const GLYPHS: Record<string, string> = {
  home: "◧",
  tenants: "◐",
  properties: "▤",
  leases: "▦",
  settings: "⚙",
  plus: "＋",
  chevronRight: "›",
  arrowRight: "→",
  warning: "!",
  check: "✓",
  search: "⌕",
};

export function Icon({
  name,
  size = 18,
  color = "#0F172A",
}: {
  name: keyof typeof GLYPHS;
  size?: number;
  color?: string;
}) {
  return (
    <Text style={[styles.base, { fontSize: size, color, lineHeight: size + 2 }]}>
      {GLYPHS[name] ?? "?"}
    </Text>
  );
}

const styles = StyleSheet.create({
  base: {
    fontWeight: "600",
    textAlign: "center",
  },
});
