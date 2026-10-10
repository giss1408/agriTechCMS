const nf = new Intl.NumberFormat("fr-FR");
const nf1 = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 });

export const fcfa = (n: number | null | undefined) => `${nf.format(n ?? 0)} F`;
export const num = (n: number | string | null | undefined) => nf1.format(Number(n ?? 0));

export function kg(n: number | string | null | undefined) {
  const v = Number(n ?? 0);
  return v >= 1000 ? `${nf1.format(v / 1000)} t` : `${nf1.format(v)} kg`;
}

/** Côte d'Ivoire is on GMT all year: displaying in UTC is displaying local time. */
const TZ = "Africa/Abidjan";
export const date = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleDateString("fr-FR", { timeZone: TZ, day: "2-digit", month: "2-digit", year: "numeric" }) : "—";
export const dateTime = (iso: string | null | undefined) =>
  iso
    ? new Date(iso).toLocaleString("fr-FR", { timeZone: TZ, day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })
    : "—";
export const shortDay = (isoDate: string) =>
  new Date(isoDate + "T12:00:00Z").toLocaleDateString("fr-FR", { timeZone: TZ, weekday: "short", day: "numeric" });

export function ago(iso: string | null | undefined) {
  if (!iso) return "jamais";
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 90) return "à l'instant";
  if (s < 3600) return `il y a ${Math.round(s / 60)} min`;
  if (s < 86400) return `il y a ${Math.round(s / 3600)} h`;
  return `il y a ${Math.round(s / 86400)} j`;
}

export const STATUS_LABEL: Record<string, string> = {
  pending_validation: "À valider",
  validated: "Validée",
  rejected: "Rejetée",
  paid: "Payée",
  cancelled: "Annulée",
  open: "En constitution",
  sealed: "Scellé",
  shipped: "Expédié",
  initiated: "Initié",
  processing: "En cours",
  success: "Payé",
  failed: "Échec",
  active: "Actif",
  in_progress: "En cours",
  resolved: "Résolu",
  inactive: "Inactif",
};

export const STATUS_TONE: Record<string, "neutral" | "info" | "success" | "warning" | "danger"> = {
  pending_validation: "warning",
  validated: "info",
  rejected: "danger",
  paid: "success",
  cancelled: "neutral",
  open: "warning",
  sealed: "info",
  shipped: "success",
  initiated: "neutral",
  processing: "info",
  success: "success",
  failed: "danger",
  active: "success",
  in_progress: "info",
  resolved: "success",
  inactive: "neutral",
};

export const OPERATOR_LABEL: Record<string, string> = {
  orange_money: "Orange Money",
  mtn_momo: "MTN MoMo",
  wave: "Wave",
  moov_money: "Moov Money",
};

export const EUDR_ISSUE_LABEL: Record<string, string> = {
  missing_geometry: "Pas de géolocalisation",
  polygon_required_above_4ha: "Polygone requis (> 4 ha)",
  deforestation_flagged: "Alerte déforestation",
  deforestation_unchecked: "Déforestation non vérifiée",
};

export const ROLE_LABEL: Record<string, string> = { super_admin: "Super admin", admin: "Administrateur", collector: "Collecteur" };

export const ISSUE_CATEGORY_LABEL: Record<string, string> = {
  app_bug: "L'application ne marche pas",
  sync: "Synchronisation / données manquantes",
  data_error: "Erreur de poids, prix ou montant",
  payment: "Paiement",
  account: "Connexion / compte",
  other: "Autre",
};

export const ISSUE_SOURCE_LABEL: Record<string, string> = {
  web: "Web",
  mobile: "Téléphone collecteur",
  ussd: "Producteur (USSD)",
  public: "Acheteur (page lot)",
};
