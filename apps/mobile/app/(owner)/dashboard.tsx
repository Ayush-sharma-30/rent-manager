import { useState } from "react";
import { Alert, Platform, RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";

import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { Icon } from "@/components/Icon";
import { SectionHeader } from "@/components/SectionHeader";
import { StatBlock } from "@/components/StatBlock";
import { api } from "@/api/client";
import type { DashboardSummary, LeaseExpiringItem, ReminderResult } from "@/api/types";
import { useAuthStore } from "@/state/auth.store";
import { useT } from "@/i18n";
import { colors, fontSize, fontWeight, radius, spacing } from "@/theme/tokens";
import { formatINR, formatDate } from "@/utils/format";

export default function DashboardScreen() {
  const router = useRouter();
  const t = useT();
  const user = useAuthStore((s) => s.user);
  const org = useAuthStore((s) => s.organization);

  const summary = useQuery<DashboardSummary>({
    queryKey: ["dashboard", "summary"],
    queryFn: () => api<DashboardSummary>("/api/v1/dashboard/summary"),
  });

  const expiring = useQuery<{ leases: LeaseExpiringItem[] }>({
    queryKey: ["dashboard", "leases-expiring"],
    queryFn: () =>
      api<{ leases: LeaseExpiringItem[] }>("/api/v1/dashboard/leases-expiring?within_days=45"),
  });

  const data: DashboardSummary | undefined = summary.data;
  const expiringData: { leases: LeaseExpiringItem[] } | undefined = expiring.data;
  const greeting = t(greetingKeyForHour(new Date().getHours()));

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={
          <RefreshControl
            refreshing={summary.isFetching}
            onRefresh={() => {
              void summary.refetch();
              void expiring.refetch();
            }}
          />
        }
      >
        <View style={styles.header}>
          <Text style={styles.greeting}>{greeting},</Text>
          <Text style={styles.headerName}>{user?.name ?? t("dashboard.fallbackName")}</Text>
          <Text style={styles.headerOrg}>{org?.name ?? t("dashboard.fallbackOrg")}</Text>
        </View>

        {summary.isError ? (
          <Card>
            <Text style={styles.error}>
              {t("dashboard.loadError", {
                message: summary.error instanceof Error ? summary.error.message : "",
              })}
            </Text>
          </Card>
        ) : null}

        <View style={styles.statRow}>
          <StatBlock
            label={t("dashboard.stat.collected")}
            value={formatINR(data?.collected ?? 0)}
            tone="success"
            caption={data ? t("dashboard.stat.collectedCaption", { month: data.month }) : undefined}
          />
          <StatBlock
            label={t("dashboard.stat.pending")}
            value={formatINR(
              data
                ? Math.max(0, Number(data.target) - Number(data.collected))
                : 0
            )}
            tone="warning"
            caption={
              data
                ? t(
                    data.pending_count === 1
                      ? "dashboard.stat.pendingCaptionOne"
                      : "dashboard.stat.pendingCaption",
                    { count: data.pending_count }
                  )
                : undefined
            }
          />
        </View>
        <View style={styles.statRow}>
          <StatBlock
            label={t("dashboard.stat.overdue")}
            value={String(data?.overdue_count ?? 0)}
            tone="danger"
            caption={data?.overdue_count ? t("dashboard.stat.overdueFollowUp") : t("dashboard.stat.overdueClear")}
          />
          <StatBlock
            label={t("dashboard.stat.target")}
            value={formatINR(data?.target ?? 0)}
            caption={t("dashboard.stat.targetCaption")}
          />
        </View>

        <View style={styles.actionRow}>
          <Button
            label={t("dashboard.action.recordPayment")}
            onPress={() => router.push("/(owner)/record-payment")}
            leftIcon={<Icon name="plus" color={colors.primaryFg} size={16} />}
            style={styles.actionButton}
          />
          <Button
            label={t("dashboard.action.addTenant")}
            variant="secondary"
            onPress={() => router.push("/(owner)/tenants/new")}
            leftIcon={<Icon name="plus" color={colors.text} size={16} />}
            style={styles.actionButton}
          />
        </View>

        <View style={styles.section}>
          <SectionHeader
            title={t("dashboard.needsAttention")}
            action={
              data && data.needs_attention.length > 0
                ? { label: t("dashboard.viewAll"), onPress: () => router.push("/(owner)/tenants") }
                : undefined
            }
          />
          {data && data.needs_attention.length > 0 ? (
            <Card style={styles.listCard}>
              {data.needs_attention.slice(0, 5).map((item, idx) => (
                <View
                  key={item.tenant_id + item.due_date}
                  style={[styles.row, idx > 0 && styles.rowDivider]}
                >
                  <View style={{ flex: 1 }}>
                    <Text style={styles.rowTitle}>{item.tenant_name}</Text>
                    <Text style={styles.rowMeta}>
                      {item.unit_identifier} · {t("dashboard.due", { date: formatDate(item.due_date) })}
                    </Text>
                    <RemindButton tenantId={item.tenant_id} tenantName={item.tenant_name} />
                  </View>
                  <View style={styles.rowRight}>
                    <Text style={styles.amount}>{formatINR(item.amount_due)}</Text>
                    <Badge
                      label={
                        item.days_overdue > 0
                          ? t("dashboard.daysOverdue", { n: item.days_overdue })
                          : t("dashboard.dueToday")
                      }
                      tone={item.days_overdue > 0 ? "danger" : "warning"}
                    />
                  </View>
                </View>
              ))}
            </Card>
          ) : (
            <EmptyHint text={t("dashboard.allPaid")} />
          )}
        </View>

        <View style={styles.section}>
          <SectionHeader title={t("dashboard.recentlyPaid")} />
          {data && data.recently_paid.length > 0 ? (
            <Card style={styles.listCard}>
              {data.recently_paid.slice(0, 5).map((item, idx) => (
                <View key={item.payment_id} style={[styles.row, idx > 0 && styles.rowDivider]}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.rowTitle}>{item.tenant_name}</Text>
                    <Text style={styles.rowMeta}>{t("dashboard.paidOn", { date: formatDate(item.paid_on) })}</Text>
                  </View>
                  <Text style={[styles.amount, { color: colors.success }]}>
                    +{formatINR(item.amount)}
                  </Text>
                </View>
              ))}
            </Card>
          ) : (
            <EmptyHint text={t("dashboard.noPayments")} />
          )}
        </View>

        <View style={styles.section}>
          <SectionHeader
            title={t("dashboard.leasesExpiring")}
            action={
              (expiringData?.leases.length ?? 0) > 0
                ? { label: t("dashboard.openLeases"), onPress: () => router.push("/(owner)/leases") }
                : undefined
            }
          />
          {(expiringData?.leases ?? []).length > 0 ? (
            <Card style={styles.listCard}>
              {expiringData!.leases.slice(0, 4).map((l, idx) => (
                <View key={l.lease_id} style={[styles.row, idx > 0 && styles.rowDivider]}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.rowTitle}>{l.tenant_name}</Text>
                    <Text style={styles.rowMeta}>
                      {l.unit_identifier} · {t("dashboard.endsOn", { date: formatDate(l.end_date) })}
                    </Text>
                  </View>
                  <Badge
                    label={t("leases.daysLeft", { n: l.days_until_expiry })}
                    tone={l.days_until_expiry < 30 ? "danger" : "warning"}
                  />
                </View>
              ))}
            </Card>
          ) : (
            <EmptyHint text={t("dashboard.noLeasesExpiring")} />
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

function EmptyHint({ text }: { text: string }) {
  return (
    <Card>
      <Text style={styles.empty}>{text}</Text>
    </Card>
  );
}

function RemindButton({ tenantId, tenantName }: { tenantId: string; tenantName: string }) {
  const t = useT();
  const [done, setDone] = useState(false);
  const mutation = useMutation({
    mutationFn: () =>
      api<ReminderResult>(`/api/v1/reminders/tenant/${tenantId}`, { method: "POST" }),
    onSuccess: (res) => {
      setDone(true);
      setTimeout(() => setDone(false), 4000);
      const message = res.detail || t("reminder.success");
      if (Platform.OS !== "web") Alert.alert(t("reminder.success"), message);
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

  return (
    <Text
      onPress={() => {
        if (!mutation.isPending) mutation.mutate();
      }}
      style={[styles.remindPill, done && styles.remindPillDone]}
    >
      {mutation.isPending
        ? t("dashboard.reminding")
        : done
          ? `✓ ${t("reminder.success")}`
          : t("dashboard.remind")}
    </Text>
  );
}

function greetingKeyForHour(h: number): string {
  if (h < 5) return "dashboard.greeting.night";
  if (h < 12) return "dashboard.greeting.morning";
  if (h < 17) return "dashboard.greeting.afternoon";
  return "dashboard.greeting.evening";
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  scroll: { paddingHorizontal: spacing.lg, paddingTop: spacing.lg, paddingBottom: spacing.xxl, gap: spacing.lg },
  header: { gap: 2 },
  greeting: { fontSize: fontSize.sm, color: colors.textMuted },
  headerName: { fontSize: fontSize.xxl, fontWeight: fontWeight.bold, color: colors.text },
  headerOrg: { fontSize: fontSize.sm, color: colors.textSubtle },
  statRow: { flexDirection: "row", gap: spacing.md },
  actionRow: { flexDirection: "row", flexWrap: "wrap", gap: spacing.md },
  actionButton: { flexGrow: 1, flexBasis: 150 },
  section: { gap: spacing.sm },
  listCard: { padding: 0 },
  row: {
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
  },
  rowDivider: { borderTopWidth: 1, borderTopColor: colors.border },
  rowTitle: { fontSize: fontSize.md, fontWeight: fontWeight.semibold, color: colors.text },
  rowMeta: { fontSize: fontSize.xs, color: colors.textMuted, marginTop: 2 },
  rowRight: { alignItems: "flex-end", gap: 4 },
  amount: { fontSize: fontSize.md, fontWeight: fontWeight.semibold, color: colors.text },
  remindPill: {
    marginTop: spacing.sm,
    alignSelf: "flex-start",
    backgroundColor: colors.accentMuted,
    color: colors.accent,
    fontSize: fontSize.xs,
    fontWeight: fontWeight.semibold,
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
    borderRadius: radius.full,
    overflow: "hidden",
  },
  remindPillDone: { backgroundColor: colors.surfaceMuted, color: colors.success },
  empty: { fontSize: fontSize.sm, color: colors.textMuted, textAlign: "center" },
  error: { fontSize: fontSize.sm, color: colors.danger },
});
