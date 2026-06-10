import { useState } from "react";
import { FlatList, Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { Icon } from "@/components/Icon";
import { Input } from "@/components/Input";
import { api } from "@/api/client";
import type { Tenant } from "@/api/types";
import { useT, useTd } from "@/i18n";
import { colors, fontSize, fontWeight, spacing } from "@/theme/tokens";
import { formatPhone } from "@/utils/format";

export default function TenantsList() {
  const router = useRouter();
  const t = useT();
  const td = useTd();
  const [q, setQ] = useState("");
  const tenants = useQuery({
    queryKey: ["tenants", { q }],
    queryFn: () => {
      const params = new URLSearchParams();
      if (q) params.set("q", q);
      return api<Tenant[]>(`/api/v1/tenants${params.toString() ? `?${params}` : ""}`);
    },
  });

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <View style={styles.headerRow}>
        <Text style={styles.title}>{t("tenants.title")}</Text>
        <Button
          label={t("common.add")}
          size="md"
          onPress={() => router.push("/(owner)/tenants/new")}
          leftIcon={<Icon name="plus" color={colors.primaryFg} size={14} />}
        />
      </View>

      <View style={styles.searchWrap}>
        <Input placeholder={t("tenants.search")} value={q} onChangeText={setQ} />
      </View>

      <FlatList
        data={tenants.data ?? []}
        keyExtractor={(t) => t.id}
        contentContainerStyle={styles.list}
        ItemSeparatorComponent={() => <View style={{ height: spacing.sm }} />}
        ListEmptyComponent={
          tenants.isLoading ? (
            <Card><Text style={styles.empty}>{t("common.loading")}</Text></Card>
          ) : (
            <Card><Text style={styles.empty}>{t("tenants.empty")}</Text></Card>
          )
        }
        renderItem={({ item }) => (
          <Pressable onPress={() => router.push(`/(owner)/tenants/${item.id}`)}>
            <Card style={styles.row}>
              <View style={styles.avatar}>
                <Text style={styles.avatarText}>{initials(item.name)}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.rowName}>{td(item.name)}</Text>
                <Text style={styles.rowMeta}>{formatPhone(item.phone_e164)}</Text>
                {item.email ? <Text style={styles.rowMeta}>{item.email}</Text> : null}
              </View>
              <View style={styles.langPill}>
                <Text style={styles.langPillText}>{item.language.toUpperCase()}</Text>
              </View>
              <Icon name="chevronRight" color={colors.textSubtle} size={20} />
            </Card>
          </Pressable>
        )}
      />
    </SafeAreaView>
  );
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || "?";
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
  },
  title: { fontSize: fontSize.xxl, fontWeight: fontWeight.bold, color: colors.text },
  searchWrap: { paddingHorizontal: spacing.lg, paddingTop: spacing.md },
  list: { paddingHorizontal: spacing.lg, paddingTop: spacing.md, paddingBottom: spacing.xxl },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  avatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.surfaceMuted,
    alignItems: "center",
    justifyContent: "center",
  },
  avatarText: { fontWeight: fontWeight.bold, color: colors.text },
  rowName: { fontSize: fontSize.md, fontWeight: fontWeight.semibold, color: colors.text },
  rowMeta: { fontSize: fontSize.xs, color: colors.textMuted, marginTop: 2 },
  langPill: {
    backgroundColor: colors.surfaceMuted,
    borderRadius: 999,
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
  },
  langPillText: {
    fontSize: 10,
    fontWeight: fontWeight.bold,
    color: colors.textMuted,
    letterSpacing: 1,
  },
  empty: { fontSize: fontSize.sm, color: colors.textMuted, textAlign: "center" },
});
