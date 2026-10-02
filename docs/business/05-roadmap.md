# Feuille de route

> Remplace les deux plans de sprints divergents de l'archive (`prochaines-etapes-v0.md` : 4 sprints,
> `fonctionnalites-et-vues-v0.md` : 5 sprints). Un seul plan, aligné sur le code de ce dépôt.

## Phase A — Valider (semaines 1–3) ⬅ en cours

- 10–15 entretiens de validation avec la démo ([03-validation-terrain.md](03-validation-terrain.md))
- Dossiers d'incubation / financement ([finance/03-financement.md](../finance/03-financement.md))
- Décision go / no-go selon les critères chiffrés

## Phase B — Durcir le MVP pour le pilote (semaines 4–11)

Le squelette fonctionnel existe déjà dans `apps/`. Il s'agit de le rendre fiable sur le terrain.

| Sprint | Contenu | Durée |
|---|---|---|
| B1 | App collecteur sur téléphones réels bas de gamme (Android 8+), tests en zone sans réseau, scan QR, photos compressées | 2 sem. |
| B2 | Déploiement (PostgreSQL managé, sauvegardes, supervision), import CSV des adhérents des coopératives pilotes, cartes QR imprimées | 2 sem. |
| B3 | Branchement CinetPay (ou Julaya) en réel, réconciliation, reçus | 2 sem. |
| B4 | Retours des premiers jours de pilote, rapports demandés par les acheteurs des coopératives pilotes | 2 sem. |

## Phase C — Pilote (mois 3 à 5)

- 2–3 coopératives, gratuit 3 mois, formation 2 h, passage hebdomadaire
- Mesures : adoption > 60 %, écarts papier/app, délai de paiement, temps de préparation des rapports
- Conversion en payant + témoignages

## Phase D — Après le pilote

Selon les retours : rapports PDF aux formats acheteurs, WhatsApp, unions de coopératives, contrôle
déforestation automatique, licence exportateur, puis services financiers (avances, crédit intrants).
