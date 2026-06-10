import { Alert, Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";

import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { useAuthStore } from "@/state/auth.store";
import { useLocaleStore } from "@/state/locale.store";
import { LOCALES, useT } from "@/i18n";
import { API_BASE_URL } from "@/api/client";
import { colors, fontSize, fontWeight, radius, spacing } from "@/theme/tokens";
import { formatPhone } from "@/utils/format";

export default function SettingsScreen() {
  const router = useRouter();
  const t = useT();
  const user = useAuthStore((s) => s.user);
  const org = useAuthStore((s) => s.organization);
  const signOut = useAuthStore((s) => s.signOut);
  const locale = useLocaleStore((s) => s.locale);
  const setLocale = useLocaleStore((s) => s.setLocale);

  async function handleLogout() {
    const doLogout = async () => {
      await signOut();
      router.replace("/(auth)/login");
    };
    if (Platform.OS === "web") {
      await doLogout();
    } else {
      Alert.alert(t("settings.logoutConfirmTitle"), t("settings.logoutConfirmBody"), [
        { text: t("common.cancel"), style: "cancel" },
        { text: t("settings.logout"), style: "destructive", onPress: () => void doLogout() },
      ]);
    }
  }

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.title}>{t("settings.title")}</Text>

        <Card>
          <Text style={styles.sectionLabel}>{t("settings.appLanguage")}</Text>
          <View style={styles.langRow}>
            {LOCALES.map((opt) => {
              const selected = locale === opt.code;
              return (
                <Pressable
                  key={opt.code}
                  onPress={() => void setLocale(opt.code)}
                  style={[styles.langOption, selected && styles.langOptionSelected]}
                >
                  <Text style={[styles.langOptionText, selected && styles.langOptionTextSelected]}>
                    {opt.label}
                  </Text>
                </Pressable>
              );
            })}
          </View>
          <Text style={styles.langHint}>{t("settings.appLanguageHint")}</Text>
        </Card>

        <Card>
          <Text style={styles.sectionLabel}>{t("settings.signedInAs")}</Text>
          <Text style={styles.bigName}>{user?.name ?? "—"}</Text>
          <Text style={styles.metaLine}>{user ? formatPhone(user.phone_e164) : ""}</Text>
          {user?.email ? <Text style={styles.metaLine}>{user.email}</Text> : null}
        </Card>

        <Card>
          <Text style={styles.sectionLabel}>{t("settings.organization")}</Text>
          <View style={styles.orgRow}>
            <Text style={styles.bigName}>{org?.name ?? "—"}</Text>
            <Badge label={(org?.tier ?? "pilot").toUpperCase()} tone="info" />
          </View>
          <Text style={styles.metaLine}>
            {t("settings.defaultLanguage")} · {org?.default_language?.toUpperCase()}
          </Text>
        </Card>

        <Card>
          <Text style={styles.sectionLabel}>{t("settings.about")}</Text>
          <Row label={t("settings.appVersion")} value="0.1.0 (V1 prototype)" />
          <Row label={t("settings.apiEndpoint")} value={API_BASE_URL} />
          <Row label={t("settings.otp")} value={t("settings.otpValue")} />
          <Row label={t("settings.integrations")} value={t("settings.integrationsValue")} />
        </Card>

        <Button label={t("settings.logout")} variant="danger" onPress={handleLogout} />
      </ScrollView>
    </SafeAreaView>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue} numberOfLines={2}>
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  scroll: { padding: spacing.lg, gap: spacing.md },
  title: { fontSize: fontSize.xxl, fontWeight: fontWeight.bold, color: colors.text },
  sectionLabel: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
    textTransform: "uppercase",
    letterSpacing: 0.6,
    fontWeight: fontWeight.semibold,
    marginBottom: spacing.sm,
  },
  bigName: { fontSize: fontSize.lg, fontWeight: fontWeight.bold, color: colors.text },
  metaLine: { fontSize: fontSize.sm, color: colors.textMuted, marginTop: 4 },
  langRow: { flexDirection: "row", gap: spacing.sm },
  langOption: {
    flex: 1,
    paddingVertical: spacing.md,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
    alignItems: "center",
  },
  langOptionSelected: { backgroundColor: colors.primary, borderColor: colors.primary },
  langOptionText: { fontSize: fontSize.md, fontWeight: fontWeight.semibold, color: colors.text },
  langOptionTextSelected: { color: colors.primaryFg },
  langHint: { fontSize: fontSize.xs, color: colors.textSubtle, marginTop: spacing.sm },
  orgRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: spacing.sm,
    gap: spacing.md,
  },
  rowLabel: { fontSize: fontSize.sm, color: colors.textMuted },
  rowValue: { fontSize: fontSize.sm, color: colors.text, flexShrink: 1, textAlign: "right" },
});
