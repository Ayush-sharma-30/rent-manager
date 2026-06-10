import { useState } from "react";
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";

import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { api } from "@/api/client";
import type { Tenant } from "@/api/types";
import { LOCALES, useT } from "@/i18n";
import { colors, fontSize, fontWeight, radius, spacing } from "@/theme/tokens";

const LANGUAGES = LOCALES;

export default function NewTenant() {
  const router = useRouter();
  const t = useT();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [language, setLanguage] = useState<"en" | "hi" | "kn">("hi");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      api<Tenant>("/api/v1/tenants", {
        method: "POST",
        body: JSON.stringify({
          name,
          phone_e164: phone,
          email: email || null,
          language,
        }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tenants"] });
      router.back();
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : t("tenant.createError"));
    },
  });

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={styles.flex}
      >
        <ScrollView contentContainerStyle={styles.scroll}>
          <View style={styles.header}>
            <Text style={styles.title}>{t("tenant.addTitle")}</Text>
            <Text style={styles.subtitle}>{t("tenant.subtitle")}</Text>
          </View>

          <View style={styles.form}>
            <Input
              label={t("tenant.field.name")}
              value={name}
              onChangeText={setName}
              autoCapitalize="words"
            />
            <Input
              label={t("tenant.field.phone")}
              value={phone}
              onChangeText={(v) => setPhone(v.replace(/[^\d+]/g, ""))}
              keyboardType="phone-pad"
              maxLength={13}
            />
            <Input
              label={t("tenant.field.email")}
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              keyboardType="email-address"
            />

            <View style={{ gap: spacing.xs }}>
              <Text style={styles.label}>{t("tenant.languageForReminders")}</Text>
              <View style={styles.segmented}>
                {LANGUAGES.map((opt) => {
                  const selected = language === opt.code;
                  return (
                    <Text
                      key={opt.code}
                      onPress={() => setLanguage(opt.code)}
                      style={[styles.segment, selected && styles.segmentSelected]}
                    >
                      {opt.label}
                    </Text>
                  );
                })}
              </View>
            </View>

            {error ? <Text style={styles.error}>{error}</Text> : null}

            <Button
              label={t("tenant.save")}
              size="lg"
              onPress={() => {
                if (!name.trim() || phone.length < 10) {
                  setError(t("tenant.validation"));
                  return;
                }
                setError(null);
                mutation.mutate();
              }}
              loading={mutation.isPending}
            />
            <Button label={t("common.cancel")} variant="ghost" onPress={() => router.back()} />
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  flex: { flex: 1 },
  scroll: { padding: spacing.lg, gap: spacing.xl },
  header: { gap: spacing.xs },
  title: { fontSize: fontSize.xxl, fontWeight: fontWeight.bold, color: colors.text },
  subtitle: { fontSize: fontSize.sm, color: colors.textMuted, lineHeight: 20 },
  form: { gap: spacing.lg },
  label: { fontSize: fontSize.sm, fontWeight: fontWeight.medium, color: colors.textMuted },
  segmented: {
    flexDirection: "row",
    borderRadius: radius.md,
    backgroundColor: colors.surfaceMuted,
    padding: 4,
    gap: 4,
  },
  segment: {
    flex: 1,
    paddingVertical: spacing.sm,
    textAlign: "center",
    color: colors.textMuted,
    fontWeight: fontWeight.semibold,
    fontSize: fontSize.sm,
    borderRadius: radius.sm,
  },
  segmentSelected: { backgroundColor: colors.surface, color: colors.text },
  error: { color: colors.danger, fontSize: fontSize.sm },
});
