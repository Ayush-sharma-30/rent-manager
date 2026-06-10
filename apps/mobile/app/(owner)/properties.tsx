import { useEffect, useState } from "react";
import { FlatList, Modal, Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { Icon } from "@/components/Icon";
import { Input } from "@/components/Input";
import { api } from "@/api/client";
import type { Property } from "@/api/types";
import { useT } from "@/i18n";
import { colors, fontSize, fontWeight, radius, spacing } from "@/theme/tokens";

export default function PropertiesScreen() {
  const t = useT();
  const [showAdd, setShowAdd] = useState(false);
  const [editing, setEditing] = useState<Property | null>(null);
  const properties = useQuery({
    queryKey: ["properties"],
    queryFn: () => api<Property[]>("/api/v1/properties"),
  });

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <View style={styles.headerRow}>
        <Text style={styles.title}>{t("properties.title")}</Text>
        <Button
          label={t("common.add")}
          onPress={() => setShowAdd(true)}
          leftIcon={<Icon name="plus" color={colors.primaryFg} size={14} />}
        />
      </View>

      <FlatList
        data={properties.data ?? []}
        keyExtractor={(p) => p.id}
        contentContainerStyle={styles.list}
        ItemSeparatorComponent={() => <View style={{ height: spacing.sm }} />}
        ListEmptyComponent={
          properties.isLoading ? (
            <Card><Text style={styles.empty}>{t("common.loading")}</Text></Card>
          ) : (
            <Card>
              <Text style={styles.empty}>{t("properties.empty")}</Text>
            </Card>
          )
        }
        renderItem={({ item }) => (
          <Pressable onPress={() => setEditing(item)}>
            <Card style={styles.row}>
              <View style={{ flex: 1 }}>
                <Text style={styles.rowName}>{item.name}</Text>
                <Text style={styles.rowMeta}>
                  {item.type === "pg" ? t("property.typePG") : t("property.typeApartment")}
                  {item.area ? ` · ${item.area}` : ""} · {item.city}
                </Text>
                {item.address_line ? (
                  <Text style={[styles.rowMeta, { marginTop: 2 }]}>{item.address_line}</Text>
                ) : null}
              </View>
              <Icon name="chevronRight" color={colors.textSubtle} size={20} />
            </Card>
          </Pressable>
        )}
      />

      <PropertyModal visible={showAdd} onClose={() => setShowAdd(false)} />
      <PropertyModal
        visible={editing !== null}
        property={editing}
        onClose={() => setEditing(null)}
      />
    </SafeAreaView>
  );
}

function PropertyModal({
  visible,
  property,
  onClose,
}: {
  visible: boolean;
  property?: Property | null;
  onClose: () => void;
}) {
  const t = useT();
  const queryClient = useQueryClient();
  const isEdit = !!property;
  const [name, setName] = useState("");
  const [type, setType] = useState<"apartment_building" | "pg">("apartment_building");
  const [area, setArea] = useState("");
  const [pincode, setPincode] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Pre-fill when opening in edit mode (or reset for the add sheet).
  useEffect(() => {
    if (!visible) return;
    setName(property?.name ?? "");
    setType((property?.type as "apartment_building" | "pg") ?? "apartment_building");
    setArea(property?.area ?? "");
    setPincode(property?.pincode ?? "");
    setError(null);
  }, [visible, property]);

  const mutation = useMutation({
    mutationFn: () => {
      const body = JSON.stringify({
        name,
        type,
        area: area || null,
        city: property?.city ?? "Bengaluru",
        pincode: pincode || null,
      });
      return isEdit
        ? api<Property>(`/api/v1/properties/${property!.id}`, { method: "PATCH", body })
        : api<Property>("/api/v1/properties", { method: "POST", body });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["properties"] });
      onClose();
    },
    onError: (err) => setError(err instanceof Error ? err.message : t("property.saveError")),
  });

  return (
    <Modal visible={visible} animationType="slide" transparent>
      <Pressable style={modal.backdrop} onPress={onClose}>
        <Pressable style={modal.sheet} onPress={(e) => e.stopPropagation()}>
          <Text style={modal.title}>{isEdit ? t("property.editTitle") : t("property.addTitle")}</Text>
          <Input
            label={t("property.field.name")}
            value={name}
            onChangeText={setName}
            placeholder="Saraswati Nilaya"
          />
          <View>
            <Text style={modal.label}>{t("property.field.type")}</Text>
            <View style={modal.segmented}>
              {[
                { v: "apartment_building" as const, l: t("property.typeApartmentShort") },
                { v: "pg" as const, l: t("property.typePG") },
              ].map((opt) => (
                <Text
                  key={opt.v}
                  onPress={() => setType(opt.v)}
                  style={[modal.segment, type === opt.v && modal.segmentSelected]}
                >
                  {opt.l}
                </Text>
              ))}
            </View>
          </View>
          <Input
            label={t("property.field.area")}
            value={area}
            onChangeText={setArea}
            placeholder="HSR Layout"
          />
          <Input
            label={t("property.field.pincode")}
            value={pincode}
            onChangeText={setPincode}
            keyboardType="number-pad"
            maxLength={6}
          />
          {error ? <Text style={{ color: colors.danger }}>{error}</Text> : null}
          <View style={{ flexDirection: "row", gap: spacing.md, marginTop: spacing.sm }}>
            <Button label={t("common.cancel")} variant="secondary" onPress={onClose} style={{ flex: 1 }} />
            <Button
              label={t("common.save")}
              onPress={() => {
                if (!name.trim()) {
                  setError(t("property.nameRequired"));
                  return;
                }
                mutation.mutate();
              }}
              loading={mutation.isPending}
              style={{ flex: 1 }}
            />
          </View>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  headerRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
  },
  title: { fontSize: fontSize.xxl, fontWeight: fontWeight.bold, color: colors.text },
  list: { padding: spacing.lg },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  rowName: { fontSize: fontSize.md, fontWeight: fontWeight.semibold, color: colors.text },
  rowMeta: { fontSize: fontSize.xs, color: colors.textMuted, marginTop: 4 },
  empty: { fontSize: fontSize.sm, color: colors.textMuted, textAlign: "center" },
});

const modal = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: "rgba(15, 23, 42, 0.4)", justifyContent: "flex-end" },
  sheet: {
    backgroundColor: colors.surface,
    padding: spacing.xl,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    gap: spacing.md,
  },
  title: { fontSize: fontSize.xl, fontWeight: fontWeight.bold, color: colors.text },
  label: {
    fontSize: fontSize.sm,
    fontWeight: fontWeight.medium,
    color: colors.textMuted,
    marginBottom: spacing.xs,
  },
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
});
