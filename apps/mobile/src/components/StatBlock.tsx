import { StyleSheet, Text, View } from "react-native";
import { Card } from "./Card";
import { colors, fontSize, fontWeight, spacing } from "@/theme/tokens";

interface Props {
  label: string;
  value: string;
  tone?: "default" | "success" | "warning" | "danger";
  caption?: string;
}

export function StatBlock({ label, value, tone = "default", caption }: Props) {
  const toneColor = toneMap[tone];
  return (
    <Card style={styles.card}>
      <Text style={styles.label}>{label}</Text>
      <Text style={[styles.value, { color: toneColor }]} numberOfLines={1} adjustsFontSizeToFit>
        {value}
      </Text>
      {caption && <Text style={styles.caption}>{caption}</Text>}
    </Card>
  );
}

const toneMap = {
  default: colors.text,
  success: colors.success,
  warning: colors.warning,
  danger: colors.danger,
};

const styles = StyleSheet.create({
  card: { flex: 1, gap: spacing.xs, minWidth: 140 },
  label: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
    textTransform: "uppercase",
    letterSpacing: 0.6,
    fontWeight: fontWeight.semibold,
  },
  value: { fontSize: fontSize.xl, fontWeight: fontWeight.bold, marginTop: spacing.xs },
  caption: { fontSize: fontSize.xs, color: colors.textSubtle, marginTop: spacing.xs },
});
