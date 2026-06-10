import { useEffect, useState } from "react";
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";

import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { api } from "@/api/client";
import type { ReminderResult, Tenant } from "@/api/types";
import { LOCALES, useT } from "@/i18n";
import type { Locale } from "@/i18n";
import { colors, fontSize, fontWeight, radius, spacing } from "@/theme/tokens";

export default function EditTenant() {
  const router = useRouter();
  const t = useT();
  const queryClient = useQueryClient();
  const { id } = useLocalSearchParams<{ id: string }>();

  const tenantQuery = useQuery({
    queryKey: ["tenants", id],
    queryFn: () => api<Tenant>(`/api/v1/tenants/${id}`),
    enabled: !!id,
  });

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [language, setLanguage] = useState<Locale>("hi");
  const [whatsappOptIn, setWhatsappOptIn] = useState(true);
  const [emailOptIn, setEmailOptIn] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Populate the form once the tenant loads.
  useEffect(() => {
    const tt = tenantQuery.data;
    if (!tt) return;
    setName(tt.name);
    setPhone(tt.phone_e164);
    setEmail(tt.email ?? "");
    setLanguage((["en", "hi", "kn"].includes(tt.language) ? tt.language : "hi") as Locale);
    setWhatsappOptIn(tt.whatsapp_opt_in);
    setEmailOptIn(tt.email_opt_in);
  }, [tenantQuery.data]);

  const save = useMutation({
    mutationFn: () =>
      api<Tenant>(`/api/v1/tenants/${id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name,
          phone_e164: phone,
          email: email || null,
          language,
          whatsapp_opt_in: whatsappOptIn,
          email_opt_in: emailOptIn,
        }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tenants"] });
      router.back();
    },
    onError: (err) => setError(err instanceof Error ? err.message : t("tenant.createError")),
  });

  const remind = useMutation({
    mutationFn: () => api<ReminderResult>(`/api/v1/reminders/tenant/${id}`, { method: "POST" }),
    onSuccess: (res) => {
      const message = res.detail || t("reminder.success");
      if (Platform.OS === "web") {
        // eslint-disable-next-line no-alert
        alert(message);
      } else {
        Alert.alert(t("reminder.success"), message);
      }
    },
    onError: (err) => {
      const message = err instanceof Error ? err.message : t("reminder.failed");
      if (Platform.OS === "web") {
        // eslint-disable-next-line no-alert
        alert(message);
      } else {
        Alert.alert(t("reminder.failed"), message);
      }
    },
  });

  if (tenantQuery.isLoading) {
    return (
      <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
        <View style={styles.center}>
          <Text style={styles.subtitle}>{t("common.loading")}</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (tenantQuery.isError || !tenantQuery.data) {
    return (
      <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
        <View style={styles.center}>
          <Text style={styles.error}>{t("tenant.notFound")}</Text>
          <Button label={t("common.cancel")} variant="ghost" onPress={() => router.back()} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={styles.flex}
      >
        <ScrollView contentContainerStyle={styles.scroll}>
          <View style={styles.header}>
            <Text style={styles.title}>{t("tenant.editTitle")}</Text>
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
                {LOCALES.map((opt) => {
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

            <View style={styles.toggleRow}>
              <Text style={styles.toggleLabel}>{t("tenant.field.whatsapp")}</Text>
              <Switch value={whatsappOptIn} onValueChange={setWhatsappOptIn} />
            </View>
            <View style={styles.toggleRow}>
              <Text style={styles.toggleLabel}>{t("tenant.field.emailOptIn")}</Text>
              <Switch value={emailOptIn} onValueChange={setEmailOptIn} />
            </View>

            {error ? <Text style={styles.error}>{error}</Text> : null}

            <Button
              label={t("tenant.saveChanges")}
              size="lg"
              onPress={() => {
                if (!name.trim() || phone.length < 10) {
                  setError(t("tenant.validation"));
                  return;
                }
                setError(null);
                save.mutate();
              }}
              loading={save.isPending}
            />
            <Button
              label={t("tenant.sendReminderNow")}
              variant="secondary"
              onPress={() => remind.mutate()}
              loading={remind.isPending}
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
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: spacing.md, padding: spacing.xl },
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
  toggleRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: spacing.xs,
  },
  toggleLabel: { fontSize: fontSize.md, color: colors.text, flex: 1 },
  error: { color: colors.danger, fontSize: fontSize.sm },
});
