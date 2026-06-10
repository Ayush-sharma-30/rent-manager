// Localization for *seeded demo data* (names, addresses, the demo org/owner).
// Real user-entered data has no mapping and passes through unchanged, which is
// the correct behaviour — we only transliterate the fixed demo dataset so the
// shared link reads naturally in the selected language.

import type { Locale } from "@/i18n/translations";

// English seed value -> { hi, kn }. Keys must match the strings in
// apps/backend/scripts/seed_dev_data.py exactly.
const DATA: Record<string, { hi: string; kn: string }> = {
  // Owner & organization
  Ayush: { hi: "आयुष", kn: "ಆಯುಷ್" },
  "Sunrise Properties": { hi: "सनराइज़ प्रॉपर्टीज़", kn: "ಸನ್‌ರೈಸ್ ಪ್ರಾಪರ್ಟೀಸ್" },

  // Property
  "Saraswati Nilaya": { hi: "सरस्वती निलय", kn: "ಸರಸ್ವತಿ ನಿಲಯ" },
  "12, 5th Main": { hi: "12, 5वीं मेन", kn: "12, 5ನೇ ಮೇನ್" },
  "HSR Layout": { hi: "एचएसआर लेआउट", kn: "ಎಚ್‌ಎಸ್‌ಆರ್ ಲೇಔಟ್" },
  Bengaluru: { hi: "बेंगलुरु", kn: "ಬೆಂಗಳೂರು" },

  // Units
  "Flat 101": { hi: "फ्लैट 101", kn: "ಫ್ಲಾಟ್ 101" },
  "Flat 102": { hi: "फ्लैट 102", kn: "ಫ್ಲಾಟ್ 102" },
  "Flat 201": { hi: "फ्लैट 201", kn: "ಫ್ಲಾಟ್ 201" },
  "Flat 202": { hi: "फ्लैट 202", kn: "ಫ್ಲಾಟ್ 202" },
  "Flat 301": { hi: "फ्लैट 301", kn: "ಫ್ಲಾಟ್ 301" },

  // Tenants
  "Priya Sharma": { hi: "प्रिया शर्मा", kn: "ಪ್ರಿಯಾ ಶರ್ಮಾ" },
  "Rahul Iyer": { hi: "राहुल अय्यर", kn: "ರಾಹುಲ್ ಅಯ್ಯರ್" },
  "Ananya Rao": { hi: "अनन्या राव", kn: "ಅನನ್ಯಾ ರಾವ್" },
  "Karthik Menon": { hi: "कार्तिक मेनन", kn: "ಕಾರ್ತಿಕ್ ಮೆನನ್" },
  "Meera Joshi": { hi: "मीरा जोशी", kn: "ಮೀರಾ ಜೋಶಿ" },
};

/** Localize a known seed string; unknown (user-entered) values pass through. */
export function localizeData(locale: Locale, value: string | null | undefined): string {
  if (!value) return value ?? "";
  if (locale === "en") return value;
  return DATA[value]?.[locale] ?? value;
}

// Short month names per locale, so dates read in the chosen language without
// depending on Intl locale data (which is patchy in Hermes on-device).
export const MONTHS_SHORT: Record<Locale, string[]> = {
  en: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
  hi: ["जन", "फ़र", "मार्च", "अप्रैल", "मई", "जून", "जुल", "अग", "सित", "अक्तू", "नव", "दिस"],
  kn: ["ಜನ", "ಫೆಬ್ರ", "ಮಾರ್ಚ್", "ಏಪ್ರಿ", "ಮೇ", "ಜೂನ್", "ಜುಲೈ", "ಆಗ", "ಸೆಪ್", "ಅಕ್ಟೋ", "ನವೆಂ", "ಡಿಸೆಂ"],
};
