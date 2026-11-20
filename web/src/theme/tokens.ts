/**
 * Tokens for a search team's relevance console. The ground is a pale sage, like a judging sheet; ink is a dark
 * green-black; one deep green marks focus and the active view. Hidden relevance grades use a single green ramp
 * (light to dark = worse to better). Series use the validated categorical slots in fixed order: blue the routed
 * design, orange lexical only, aqua vector only, yellow fusing every query. Instrument Sans throughout.
 */
export const color = {
  ground: "#EEF2EF",
  sheet: "#FFFFFF",
  ink: "#15201B",
  copy: "#2B3631",
  muted: "#57625C",
  line: "#D2DAD5",
  focus: "#0B6E4F",
  focusWash: "#DCEDE4",
  bad: "#B42318",
  badWash: "#FBE4E1",
  grade0: "#E4E9E6",
  grade1: "#C3D6CB",
  grade2: "#6FAE8D",
  grade3: "#1F7A55",
  routed: "#2a78d6",
  lexical: "#eb6834",
  semantic: "#1baf7a",
  hybrid: "#eda100",
  fair: "#2a78d6",
  none: "#eb6834",
} as const;

export const font = { ui: ["Instrument Sans Variable", "Instrument Sans", "system-ui", "sans-serif"] } as const;

/** 1.25 ratio from a 15px base. [size, line-height] */
export const type = {
  small: ["0.8125rem", "1.45"],
  body: ["0.9375rem", "1.55"],
  lead: ["1.1875rem", "1.4"],
  title: ["1.75rem", "1.15"],
  hero: ["2.5rem", "1.08"],
} as const;

export const space = { 0: "0", 1: "0.25rem", 2: "0.5rem", 3: "0.75rem", 4: "1rem", 5: "1.5rem", 6: "2rem", 7: "3rem", 8: "4rem" } as const;
export const radius = { none: "0", soft: "3px", card: "6px", pill: "999px" } as const;
export const measure = { prose: "66ch", page: "76rem", column: "36rem" } as const;
export const line = { hair: "1px", rule: "2px" } as const;
export const size = { chip: "1.375rem", bar: "0.875rem", label: "11rem", swatch: "0.625rem" } as const;
