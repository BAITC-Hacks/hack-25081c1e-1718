// UI copy only. Report values, identifiers and conversation text stay unchanged.
const messages = new Map();
const listeners = new Set();
const textBindings = new WeakMap();
const attributeBindings = new WeakMap();
const staticAttributes = new WeakMap();
const STORAGE_KEY = "tariflow.language";
let language = "ru";
try {
  const saved = globalThis.localStorage?.getItem(STORAGE_KEY);
  if (saved === "kk") language = saved;
} catch { /* A blocked preference store does not block the interface. */ }

export function getLanguage() { return language; }
// Some browser ICU builds advertise kk but fall back to English numeric symbols.
// Both interface languages use a decimal comma and spaced thousands for consistency.
const kazakhLocale = Intl.NumberFormat.supportedLocalesOf("kk-KZ").length && new Intl.NumberFormat("kk-KZ").formatToParts(1.1).some(part => part.type === "decimal" && part.value === ",") ? "kk-KZ" : "ru-RU";
export function getLocale() { return language === "kk" ? kazakhLocale : "ru-RU"; }
export function registerMessages(entries) {
  for (const [source, translation] of Object.entries(entries)) messages.set(source, translation);
}
export function t(source, params = {}, selectedLanguage = language) {
  if (typeof source !== "string") return source;
  const template = selectedLanguage === "kk" ? (messages.get(source) ?? source) : source;
  return template.replace(/\{(\w+)\}/g, (match, key) => Object.hasOwn(params, key) ? String(typeof params[key] === "function" ? params[key]() : params[key]) : match);
}
export function localizedError(source, params = {}) {
  const error = new Error();
  Object.defineProperty(error, "message", {get: () => t(source, params), configurable:true});
  return error;
}
export function onLanguageChange(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
export function setLocalizedText(node, source, params = {}) {
  if (!node) return;
  node.removeAttribute("data-i18n");
  node.setAttribute("data-localized", "");
  textBindings.set(node, {source, params});
  node.textContent = t(typeof source === "function" ? source() : source, params);
}
export function setLocalizedAttribute(node, attribute, source, params = {}) {
  if (!node) return;
  node.removeAttribute(`data-kk-${attribute}`);
  node.setAttribute("data-localized-attributes", "");
  const bindings = attributeBindings.get(node) ?? new Map();
  bindings.set(attribute, {source, params});
  attributeBindings.set(node, bindings);
  node.setAttribute(attribute, t(source, params));
}
export function localizeStatic(root = globalThis.document) {
  if (!root) return;
  for (const node of root.querySelectorAll("[data-i18n][data-kk]")) {
    const source = node.getAttribute("data-i18n");
    registerMessages({[source]: node.getAttribute("data-kk")});
    node.textContent = t(source);
  }
  for (const node of root.querySelectorAll("*")) {
    for (const attribute of Array.from(node.attributes)) {
      if (!attribute.name.startsWith("data-kk-")) continue;
      const name = attribute.name.slice(8);
      const originals = staticAttributes.get(node) ?? new Map();
      if (!originals.has(name)) originals.set(name, node.getAttribute(name) ?? "");
      staticAttributes.set(node, originals);
      registerMessages({[originals.get(name)]: attribute.value});
      node.setAttribute(name, language === "kk" ? attribute.value : originals.get(name));
    }
  }
  for (const node of root.querySelectorAll("[data-localized]")) {
    const binding = textBindings.get(node);
    if (binding) node.textContent = t(typeof binding.source === "function" ? binding.source() : binding.source, binding.params);
  }
  for (const node of root.querySelectorAll("[data-localized-attributes]")) {
    for (const [name, binding] of attributeBindings.get(node) ?? []) node.setAttribute(name, t(binding.source, binding.params));
  }
  if (root.documentElement) root.documentElement.lang = language;
  const select = root.querySelector("#language-select");
  if (select) select.value = language;
}
export function setLanguage(value) {
  if (value !== "ru" && value !== "kk") return false;
  if (value === language) return false;
  language = value;
  try { globalThis.localStorage?.setItem(STORAGE_KEY, value); } catch { /* Preference is optional. */ }
  for (const listener of listeners) listener(value);
  localizeStatic();
  if (globalThis.document) document.dispatchEvent(new CustomEvent("tariflow:language-changed", {detail:{language}}));
  return true;
}
export function initializeLanguage() {
  localizeStatic();
  globalThis.document?.querySelector("#language-select")?.addEventListener("change", event => setLanguage(event.target.value));
}
