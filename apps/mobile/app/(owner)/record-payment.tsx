import { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";

import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { Input } from "@/components/Input";
import { api } from "@/api/client";
import type { Invoice, Payment, Tenant } from "@/api/types";
import { useT, useTd } from "@/i18n";
import { colors, fontSize, fontWeight, radius, spacing } from "@/theme/tokens";
import { formatINR } from "@/utils/format";

const METHODS = ["upi", "bank_transfer", "cash", "other"] as const;
const OPEN_STATUSES = ["pending", "partial", "overdue"];

export default function RecordPayment() {
  const router = useRouter();
  const t = useT();
  const td = useTd();
  const queryClient = useQueryClient();

  const [tenantId, setTenantId] = useState<string | null>(null);
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState<(typeof METHODS)[number]>("upi");
  const [reference, setReference] = useState("");
  const [error, setError] = useState<string | null>(null);

  const tenants = useQuery<Tenant[]>({
    queryKey: ["tenants", "all"],
    queryFn: () => api<Tenant[]>("/api/v1/tenants"),
  });

  // Outstanding due for the chosen tenant, used to cap the payment amount.
  const invoices = useQuery<Invoice[]>({
    queryKey: ["invoices", "tenant", tenantId],
    queryFn: () => api<Invoice[]>(`/api/v1/invoices?tenant_id=${tenantId}`),
    enabled: !!tenantId,
  });
  const due = (invoices.data ?? [])
    .filter((inv: Invoice) => OPEN_STATUSES.includes(inv.status))
    .reduce((sum: number, inv: Invoice) => sum + (Number(inv.amount_due) - Number(inv.amount_paid)), 0);

  const mutation = useMutation({
    mutationFn: () =>
      api<{ payment: Payment }>("/api/v1/payments", {
        method: "POST",
        body: JSON.stringify({
          tenant_id: tenantId,
          amount,
          paid_on: new Date().toISOString().slice(0, 10),
          method,
          reference: reference || null,
        }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      void queryClient.invalidateQueries({ queryKey: ["payments"] });
      void queryClient.invalidateQueries({ queryKey: ["invoices"] });
      router.back();
    },
    onError: (err) => setError(err instanceof Error ? err.message : t("payment.error")),
  });

  const tenantList: Tenant[] = tenants.data ?? [];
  const selected = tenantList.find((t) => t.id === tenantId);

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={styles.flex}
      >
        <ScrollView contentContainerStyle={styles.scroll}>
          <Text style={styles.title}>{t("payment.title")}</Text>
          <Text style={styles.subtitle}>{t("payment.subtitle")}</Text>

          <View style={styles.field}>
            <Text style={styles.label}>{t("payment.tenant")}</Text>
            <View style={styles.tenantList}>
              {tenantList.map((tenant) => (
                <Pressable
                  key={tenant.id}
                  onPress={() => setTenantId(tenant.id)}
                  style={[styles.tenantChip, tenantId === tenant.id && styles.tenantChipSelected]}
                >
                  <Text
                    style={[
                      styles.tenantChipText,
                      tenantId === tenant.id && styles.tenantChipTextSelected,
                    ]}
                  >
                    {td(tenant.name)}
                  </Text>
                </Pressable>
              ))}
              {tenants.data && tenantList.length === 0 ? (
                <Text style={styles.empty}>{t("payment.addTenantFirst")}</Text>
              ) : null}
            </View>
          </View>

          <Input
            label={t("payment.amount")}
            value={amount}
            onChangeText={(v) => {
              setAmount(v.replace(/[^\d.]/g, ""));
              if (error) setError(null);
            }}
            keyboardType="decimal-pad"
            placeholder="20000"
            hint={selected && invoices.isSuccess ? t("payment.dueLabel") + ": " + formatINR(due) : undefined}
          />

          <View style={styles.field}>
            <Text style={styles.label}>{t("payment.method")}</Text>
            <View style={styles.methodRow}>
              {METHODS.map((m) => (
                <Pressable
                  key={m}
                  onPress={() => setMethod(m)}
                  style={[styles.methodPill, method === m && styles.methodPillSelected]}
                >
                  <Text
                    style={[styles.methodPillText, method === m && styles.methodPillTextSelected]}
                  >
                    {m.replace("_", " ").toUpperCase()}
                  </Text>
                </Pressable>
              ))}
            </View>
          </View>

          <Input
            label={t("payment.reference")}
            value={reference}
            onChangeText={setReference}
            placeholder={t("payment.referencePlaceholder")}
          />

          {selected && amount ? (
            <Card>
              <View style={styles.previewRow}>
                <Text style={styles.previewLabel}>{t("payment.recording")}</Text>
                <Badge label={method.replace("_", " ").toUpperCase()} tone="info" />
              </View>
              <Text style={styles.previewAmount}>{formatINR(amount)}</Text>
              <Text style={styles.previewMeta}>{t("payment.from", { name: td(selected.name) })}</Text>
            </Card>
          ) : null}

          {error ? <Text style={styles.error}>{error}</Text> : null}

          <Button
            label={t("payment.save")}
            size="lg"
            loading={mutation.isPending}
            onPress={() => {
              if (!tenantId || !amount || Number(amount) <= 0) {
                setError(t("payment.validation"));
                return;
              }
              // Block payments larger than what the tenant actually owes.
              if (invoices.isSuccess) {
                if (due <= 0) {
                  setError(t("payment.noDue"));
                  return;
                }
                if (Number(amount) > due) {
                  setError(t("payment.exceedsDue", { due: formatINR(due) }));
                  return;
                }
              }
              setError(null);
              mutation.mutate();
            }}
          />
          <Button label={t("common.cancel")} variant="ghost" onPress={() => router.back()} />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  flex: { flex: 1 },
  scroll: { padding: spacing.lg, gap: spacing.lg },
  title: { fontSize: fontSize.xxl, fontWeight: fontWeight.bold, color: colors.text },
  subtitle: { fontSize: fontSize.sm, color: colors.textMuted, marginTop: -spacing.sm },
  field: { gap: spacing.xs },
  label: { fontSize: fontSize.sm, fontWeight: fontWeight.medium, color: colors.textMuted },
  tenantList: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  tenantChip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radius.full,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  tenantChipSelected: { backgroundColor: colors.primary, borderColor: colors.primary },
  tenantChipText: { color: colors.text, fontWeight: fontWeight.semibold, fontSize: fontSize.sm },
  tenantChipTextSelected: { color: colors.primaryFg },
  methodRow: { flexDirection: "row", gap: spacing.sm, flexWrap: "wrap" },
  methodPill: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radius.full,
    borderWidth: 1,
    borderColor: colors.border,
  },
  methodPillSelected: { backgroundColor: colors.accentMuted, borderColor: colors.accent },
  methodPillText: { color: colors.textMuted, fontSize: fontSize.xs, fontWeight: fontWeight.semibold, letterSpacing: 0.4 },
  methodPillTextSelected: { color: colors.accent },
  previewRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  previewLabel: { fontSize: fontSize.xs, color: colors.textMuted, textTransform: "uppercase", letterSpacing: 0.6 },
  previewAmount: { fontSize: fontSize.display, fontWeight: fontWeight.bold, color: colors.text, marginTop: spacing.sm },
  previewMeta: { fontSize: fontSize.sm, color: colors.textMuted, marginTop: 2 },
  error: { color: colors.danger, fontSize: fontSize.sm },
  empty: { color: colors.textMuted, fontSize: fontSize.sm },
});
