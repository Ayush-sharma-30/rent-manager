import { ActivityIndicator, Pressable, StyleSheet, Text, View, ViewStyle } from "react-native";
import { colors, fontSize, fontWeight, radius, spacing } from "@/theme/tokens";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "md" | "lg";

interface Props {
  label: string;
  onPress?: () => void;
  variant?: Variant;
  size?: Size;
  disabled?: boolean;
  loading?: boolean;
  style?: ViewStyle;
  leftIcon?: React.ReactNode;
}

export function Button({
  label,
  onPress,
  variant = "primary",
  size = "md",
  disabled,
  loading,
  style,
  leftIcon,
}: Props) {
  const variantStyles = variantMap[variant];
  const sizeStyles = sizeMap[size];
  const isDisabled = disabled || loading;
  return (
    <Pressable
      onPress={onPress}
      disabled={isDisabled}
      style={({ pressed }) => [
        styles.base,
        variantStyles.container,
        sizeStyles.container,
        pressed && !isDisabled && { opacity: 0.85 },
        isDisabled && { opacity: 0.5 },
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={variantStyles.text.color as string} size="small" />
      ) : (
        <View style={styles.inner}>
          {leftIcon}
          <Text style={[styles.text, variantStyles.text, sizeStyles.text]} numberOfLines={1}>
            {label}
          </Text>
        </View>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    borderRadius: radius.md,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
  },
  inner: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  text: {
    fontWeight: fontWeight.semibold,
    letterSpacing: 0.1,
  },
});

const variantMap = {
  primary: {
    container: { backgroundColor: colors.primary },
    text: { color: colors.primaryFg },
  },
  secondary: {
    container: { backgroundColor: colors.surfaceMuted, borderWidth: 1, borderColor: colors.border },
    text: { color: colors.text },
  },
  ghost: {
    container: { backgroundColor: "transparent" },
    text: { color: colors.accent },
  },
  danger: {
    container: { backgroundColor: colors.danger },
    text: { color: colors.primaryFg },
  },
} as const;

const sizeMap = {
  md: {
    container: { paddingVertical: spacing.md, paddingHorizontal: spacing.lg, minHeight: 44 },
    text: { fontSize: fontSize.base },
  },
  lg: {
    container: { paddingVertical: spacing.lg, paddingHorizontal: spacing.xl, minHeight: 52 },
    text: { fontSize: fontSize.md },
  },
} as const;
