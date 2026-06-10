import { useState } from "react";
import { Alert, KeyboardAvoidingView, Platform, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";

import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { api } from "@/api/client";
import { useT } from "@/i18n";
import { colors, fontSize, fontWeight, spacing } from "@/theme/tokens";

interface OtpSendOut {
  request_id: string;
  dev_otp_hint: string | null;
}

export default function LoginScreen() {
  const router = useRouter();
  const t = useT();
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    if (phone.length < 10) {
      setError(t("login.validation"));
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await api<OtpSendOut>("/api/v1/auth/otp/send", {
        method: "POST",
        body: JSON.stringify({ phone_e164: phone }),
        auth: false,
      });
      router.push({
        pathname: "/(auth)/verify-otp",
        params: {
          phone,
          requestId: result.request_id,
          devHint: result.dev_otp_hint ?? "",
        },
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : t("login.failed");
      setError(message);
      if (Platform.OS !== "web") Alert.alert(t("login.failedTitle"), message);
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
          <View style={styles.brand}>
            <View style={styles.logoBadge}>
              <Text style={styles.logoBadgeText}>RM</Text>
            </View>
            <Text style={styles.title}>{t("login.title")}</Text>
            <Text style={styles.subtitle}>{t("login.subtitle")}</Text>
          </View>

          <View style={styles.form}>
            <Input
              label={t("login.phone")}
              placeholder="9876543210"
              keyboardType="phone-pad"
              autoComplete="tel"
              maxLength={13}
              value={phone}
              onChangeText={(v) => {
                setPhone(v.replace(/[^\d+]/g, ""));
                if (error) setError(null);
              }}
              error={error ?? undefined}
              hint={t("login.phoneHint")}
            />
            <Button label={t("login.sendOtp")} onPress={handleSubmit} loading={loading} size="lg" />
            <Text style={styles.helper}>{t("login.devHelper")}</Text>
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
    justifyContent: "space-between",
    maxWidth: 480,
    width: "100%",
    alignSelf: "center",
  },
  brand: { gap: spacing.md, marginTop: spacing.xxl },
  logoBadge: {
    width: 56,
    height: 56,
    borderRadius: 14,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  logoBadgeText: {
    color: colors.primaryFg,
    fontWeight: fontWeight.bold,
    fontSize: fontSize.lg,
    letterSpacing: 1,
  },
  title: {
    fontSize: fontSize.display,
    fontWeight: fontWeight.bold,
    color: colors.text,
    marginTop: spacing.lg,
  },
  subtitle: {
    fontSize: fontSize.md,
    color: colors.textMuted,
    lineHeight: 22,
  },
  form: { gap: spacing.lg },
  helper: {
    fontSize: fontSize.xs,
    color: colors.textSubtle,
    textAlign: "center",
  },
});
