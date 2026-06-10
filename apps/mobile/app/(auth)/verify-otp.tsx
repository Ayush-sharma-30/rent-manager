import { useState } from "react";
import { Alert, KeyboardAvoidingView, Platform, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useLocalSearchParams, useRouter } from "expo-router";

import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { api } from "@/api/client";
import { useAuthStore } from "@/state/auth.store";
import { useLocaleStore } from "@/state/locale.store";
import { useT } from "@/i18n";
import type { AuthSession } from "@/api/types";
import { colors, fontSize, fontWeight, radius, spacing } from "@/theme/tokens";

export default function VerifyOtpScreen() {
  const router = useRouter();
  const t = useT();
  const params = useLocalSearchParams<{ phone: string; requestId: string; devHint?: string }>();
  const signIn = useAuthStore((s) => s.signIn);
  const locale = useLocaleStore((s) => s.locale);

  const [otp, setOtp] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleVerify() {
    if (otp.length < 4) {
      setError(t("verify.validation"));
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const session = await api<AuthSession>("/api/v1/auth/otp/verify", {
        method: "POST",
        auth: false,
        body: JSON.stringify({
          phone_e164: params.phone,
          otp,
          request_id: params.requestId,
          name: name || undefined,
          organization_name: name ? `${name}'s Properties` : undefined,
          default_language: locale,
        }),
      });
      await signIn({
        accessToken: session.access_token,
        refreshToken: session.refresh_token,
        user: session.user,
        organization: session.organization,
      });
      router.replace("/(owner)/dashboard");
    } catch (err) {
      const message = err instanceof Error ? err.message : t("verify.failed");
      setError(message);
      if (Platform.OS !== "web") Alert.alert(t("verify.failedTitle"), message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={styles.flex}
      >
        <View style={styles.body}>
          <View style={styles.header}>
            <Text style={styles.title}>{t("verify.title")}</Text>
            <Text style={styles.subtitle}>{t("verify.subtitle", { phone: params.phone })}</Text>
            {params.devHint ? (
              <View style={styles.devHint}>
                <Text style={styles.devHintLabel}>{t("verify.devOtp")}</Text>
                <Text style={styles.devHintValue}>{params.devHint}</Text>
              </View>
            ) : null}
          </View>

          <View style={styles.form}>
            <Input
              label={t("verify.otp")}
              placeholder="123456"
              keyboardType="number-pad"
              maxLength={6}
              value={otp}
              onChangeText={(v) => {
                setOtp(v.replace(/\D/g, ""));
                if (error) setError(null);
              }}
              error={error ?? undefined}
            />
            <Input
              label={t("verify.name")}
              placeholder="e.g. Ayush Sharma"
              value={name}
              onChangeText={setName}
              hint={t("verify.nameHint")}
            />
            <Button label={t("verify.submit")} onPress={handleVerify} loading={loading} size="lg" />
            <Button
              label={t("verify.differentPhone")}
              variant="ghost"
              onPress={() => router.back()}
            />
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  flex: { flex: 1 },
  body: {
    flex: 1,
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.xxl,
    paddingBottom: spacing.xl,
    gap: spacing.xxl,
    maxWidth: 480,
    width: "100%",
    alignSelf: "center",
  },
  header: { gap: spacing.md, marginTop: spacing.xl },
  title: { fontSize: fontSize.xxl, fontWeight: fontWeight.bold, color: colors.text },
  subtitle: { fontSize: fontSize.md, color: colors.textMuted, lineHeight: 22 },
  devHint: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    backgroundColor: colors.accentMuted,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radius.md,
    alignSelf: "flex-start",
  },
  devHintLabel: { fontSize: fontSize.xs, color: colors.accent, fontWeight: fontWeight.semibold },
  devHintValue: {
    fontSize: fontSize.md,
    color: colors.accent,
    fontWeight: fontWeight.bold,
    letterSpacing: 4,
  },
  form: { gap: spacing.lg },
});
