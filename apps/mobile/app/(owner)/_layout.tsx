import { StyleSheet, Text } from "react-native";
import { Tabs } from "expo-router";

import { Icon } from "@/components/Icon";
import { useT } from "@/i18n";
import { colors, fontWeight } from "@/theme/tokens";

// Render labels with numberOfLines={1} so long localized words (e.g. the
// Kannada "ಬಾಡಿಗೆದಾರರು") truncate within their tab cell instead of overflowing
// into the neighbouring tab.
function tabLabel(label: string) {
  return ({ color, focused }: { color: string; focused: boolean }) => (
    <Text
      numberOfLines={1}
      style={[styles.label, { color, fontWeight: focused ? fontWeight.bold : fontWeight.semibold }]}
    >
      {label}
    </Text>
  );
}

export default function OwnerLayout() {
  const t = useT();
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textSubtle,
        tabBarStyle: {
          backgroundColor: colors.surface,
          borderTopColor: colors.border,
          height: 64,
          paddingBottom: 8,
          paddingTop: 8,
        },
        tabBarItemStyle: { paddingHorizontal: 2 },
      }}
    >
      <Tabs.Screen
        name="dashboard"
        options={{
          title: t("tabs.home"),
          tabBarLabel: tabLabel(t("tabs.home")),
          tabBarIcon: ({ color }) => <Icon name="home" color={color} size={22} />,
        }}
      />
      <Tabs.Screen
        name="tenants"
        options={{
          title: t("tabs.tenants"),
          tabBarLabel: tabLabel(t("tabs.tenants")),
          tabBarIcon: ({ color }) => <Icon name="tenants" color={color} size={22} />,
        }}
      />
      <Tabs.Screen
        name="properties"
        options={{
          title: t("tabs.properties"),
          tabBarLabel: tabLabel(t("tabs.properties")),
          tabBarIcon: ({ color }) => <Icon name="properties" color={color} size={22} />,
        }}
      />
      <Tabs.Screen
        name="leases"
        options={{
          title: t("tabs.leases"),
          tabBarLabel: tabLabel(t("tabs.leases")),
          tabBarIcon: ({ color }) => <Icon name="leases" color={color} size={22} />,
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          title: t("tabs.settings"),
          tabBarLabel: tabLabel(t("tabs.settings")),
          tabBarIcon: ({ color }) => <Icon name="settings" color={color} size={22} />,
        }}
      />
      <Tabs.Screen name="record-payment" options={{ href: null }} />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  label: {
    fontSize: 10,
    textAlign: "center",
    width: "100%",
  },
});
