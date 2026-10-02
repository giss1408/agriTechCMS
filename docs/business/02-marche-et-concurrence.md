# Marché et concurrence

> Source : `archive/ConceptAgriTech.md`, `archive/CommentAgriTech.md`. Les renvois `[1]…[6]` de l'archive
> pointaient vers des sources perdues : les chiffres ci-dessous sont donc à **re-sourcer** avant tout usage
> dans un dossier de financement. Les points marqués 🔎 sont des hypothèses à vérifier pendant la validation
> terrain ([03-validation-terrain.md](03-validation-terrain.md)).

## Pourquoi le secteur est porteur

| Facteur | Ce qu'on sait | Statut |
|---|---|---|
| Poids du cacao | La Côte d'Ivoire est le 1er producteur mondial (~40 % du volume). | Connu, à sourcer |
| Pression réglementaire | Le règlement UE contre la déforestation (EUDR) impose une géolocalisation par parcelle (polygone au-delà de 4 ha). Sa date d'application a été repoussée plusieurs fois. | 🔎 vérifier la date en vigueur |
| Pouvoir de paiement | Les coopératives manipulent des milliards de FCFA par campagne : la cible est B2B, pas le producteur. | À confirmer par les appels |
| Mobile money | Orange Money, MTN MoMo, Wave : infrastructure mature, agrégateurs (CinetPay, Julaya…). | Connu |
| Écosystème | MBC Africa Agri-Business Accelerator, Hub1040, Seedspace, Orange Fab CI, Digital Africa. | À vérifier (programmes ouverts ?) |

## Prix d'achat : un paramètre réglementé

Le prix bord-champ du cacao est **fixé par l'État (Conseil du Café-Cacao)** à chaque campagne
(ouverture de la campagne principale le 1er octobre). Ces dernières campagnes il se situe dans une fourchette
de l'ordre de **1 800 à 2 800 FCFA/kg** 🔎. L'exemple « 800 FCFA/kg » de l'archive est obsolète et faussait
tous les calculs de volume. Conséquences produit :

- la grille de prix est **versionnée** et paramétrable par la coopérative (dates d'effet) ;
- une collecte est valorisée au prix en vigueur **à sa date de collecte**, jamais au prix du jour de la synchro ;
- prélever une commission sur le paiement au producteur d'un prix fixé par l'État est politiquement risqué :
  on facture la coopérative, pas le producteur ([finance/01-tarification.md](../finance/01-tarification.md)).

## Carte concurrentielle

| Acteur | Positionnement | Ce qui manque pour notre cible |
|---|---|---|
| Investiv | Agriculture de précision, drones, SIG | Pas de CRM de collecte ni de paiement |
| Jool International | Données drones, pulvérisation | Hardware + data, pas de gestion quotidienne |
| Trusty (Trustineo) | Traçabilité blockchain premium | Trop cher pour une coopérative moyenne |
| Wi Agri | Mise en relation agriculteurs / acheteurs | Pas de gestion de coopérative |
| SmartERP (Sénégal) | ERP agricole | Pas adapté CI (mobile money, SYSCOHADA) |

### Angles morts de l'analyse initiale (à traiter en priorité) 🔎

1. **Système national de traçabilité du Conseil Café-Cacao** (carte du producteur, enregistrement des
   producteurs et des ventes). Question clé : notre outil **complète-t-il** ce système (saisie terrain, paiements,
   lots) ou fait-il **doublon** ? Positionnement visé : complément, avec export vers les formats officiels.
2. **Outils fournis gratuitement par les exportateurs** (programmes de durabilité de Barry Callebaut, Cargill,
   Olam/ofi, etc.) : de nombreuses coopératives certifiées utilisent déjà l'outil de leur acheteur. Notre
   argument : **un seul outil quel que soit l'acheteur**, données qui appartiennent à la coopérative.
3. **Éditeurs internationaux de traçabilité** (Farmforce, SourceTrace, Koltiva, etc.) : souvent vendus aux
   exportateurs, pas aux coopératives. Notre différenciation : prix, mobile money natif, hors-ligne, français, support terrain.

> Si la validation montre que les coopératives cibles sont **toutes** équipées par leur acheteur ou par l'État,
> il faut pivoter la cible vers les coopératives non certifiées / l'anacarde, ou vendre aux exportateurs.

## Risques

| Risque | Impact | Mitigation |
|---|---|---|
| Doublon avec le système national / les outils exportateurs | **Élevé** | Question n°6 des appels de validation ; positionnement complément + export |
| Adoption lente | Moyen | Pilote gratuit 3 mois, formation 2 h, passage hebdomadaire |
| Connectivité rurale | Moyen | Architecture hors-ligne d'abord (SQLite local, synchro différentielle) |
| Capacité de paiement des petites coopératives | Moyen | Cibler 200+ producteurs, tarification par taille |
| Saisonnalité (revenus concentrés en campagne) | Moyen | Abonnement annuel payé en début de campagne |
| Réglementation EUDR repoussée / allégée | Moyen | L'argument « paiement + fin des erreurs » doit tenir seul |
| Fraude / pression sur les pesées | Moyen | Photo de la pesée, GPS, journal d'audit, validation admin |
