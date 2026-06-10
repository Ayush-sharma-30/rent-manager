import { FlatList, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useQuery } from "@tanstack/react-query";

import { Badge } from "@/components/Badge";
import { Card } from "@/components/Card";
import { api } from "@/api/client";
import type { Lease, Tenant } from "@/api/types";
import { formatDateLocalized, useLocale, useT, useTd } from "@/i18n";
import { colors, fontSize, fontWeight, spacing } from "@/theme/tokens";
import { formatINR } from "@/utils/format";

export default function LeasesScreen() {
  const t = useT();
  const td = useTd();
  const locale = useLocale();
  const leases = useQuery({
    queryKey: ["leases"],
    queryFn: () => api<Lease[]>("/api/v1/leases?status_filter=active"),
  });
  const tenants = useQuery({
    queryKey: ["tenants", "by-id-map"],
    queryFn: () => api<Tenant[]>("/api/v1/tenants"),
  });

  const tenantById = new Map<string, Tenant>();
  for (const t of tenants.data ?? []) tenantById.set(t.id, t);

  const today = new Date();

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <View style={styles.headerRow}>
        <Text style={styles.title}>{t("leases.title")}</Text>
        <Text style={styles.subtitle}>
          {leases.data ? t("leases.activeCount", { count: leases.data.length }) : t("common.loading")}
        </Text>
      </View>
      <FlatList
        data={leases.data ?? []}
        keyExtractor={(l) => l.id}
        contentContainerStyle={styles.list}
        ItemSeparatorComponent={() => <View style={{ height: spacing.sm }} />}
        ListEmptyComponent={
          <Card><Text style={styles.empty}>{t("leases.empty")}</Text></Card>
        }
        renderItem={({ item }) => {
          const tenant = tenantById.get(item.tenant_id);
          const end = new Date(item.end_date);
          const daysLeft = Math.round((end.getTime() - today.getTime()) / 86400000);
          return (
            <Card>
              <View style={styles.cardHeader}>
                <Text style={styles.cardTitle}>{tenant?.name ? td(tenant.name) : t("leases.tenantFallback")}</Text>
                {daysLeft < 45 ? (
                  <Badge
                    label={t("leases.daysLeft", { n: daysLeft })}
                    tone={daysLeft < 30 ? "danger" : "warning"}
                  />
                ) : (
                  <Badge label={t("leases.activeBadge")} tone="success" />
                )}
              </View>
              <View style={styles.metaGrid}>
                <Meta label={t("leases.rent")} value={formatINR(item.monthly_rent)} />
                <Meta label={t("leases.deposit")} value={formatINR(item.security_deposit)} />
                <Meta label={t("leases.billingDay")} value={String(item.billing_day)} />
              </View>
              <Text style={styles.range}>
                {formatDateLocalized(item.start_date, locale)} → {formatDateLocalized(item.end_date, locale)}
              </Text>
            </Card>
          );
        }}
      />
    </SafeAreaView>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <View>
      <Text style={styles.metaLabel}>{label}</Text>
      <Text style={styles.metaValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  headerRow: {
    flexDirection: "row",
    alignItems: "flex-end",
    justifyContent: "space-between",
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
  },
  title: { fontSize: fontSize.xxl, fontWeight: fontWeight.bold, color: colors.text },
  subtitle: { fontSize: fontSize.sm, color: colors.textMuted, marginBottom: 4 },
  list: { padding: spacing.lg },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  cardTitle: { fontSize: fontSize.md, fontWeight: fontWeight.semibold, color: colors.text },
  metaGrid: { flexDirection: "row", gap: spacing.xl, marginTop: spacing.md },
  metaLabel: { fontSize: fontSize.xs, color: colors.textMuted, textTransform: "uppercase", letterSpacing: 0.5 },
  metaValue: { fontSize: fontSize.md, fontWeight: fontWeight.semibold, color: colors.text, marginTop: 2 },
  range: { fontSize: fontSize.xs, color: colors.textSubtle, marginTop: spacing.md },
  empty: { fontSize: fontSize.sm, color: colors.textMuted, textAlign: "center" },
});
