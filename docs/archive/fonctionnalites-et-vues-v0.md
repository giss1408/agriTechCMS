## 🖥️ Fonctionnalités & Vues du CRM de Collecte Agricole

Voici la description complète, module par module, avec les écrans (views) à concevoir pour le MVP.

---

## 1. Module ADMIN / DIRIGEANT (Web dashboard)

### Vue 1 : Tableau de bord (Dashboard)
**Écran d'accueil après connexion.**

```
┌─────────────────────────────────────────────────────┐
│  COOPÉRATIVE CACAO BONOUA          [🔔] [👤 Admin]  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │Collectes │ │Poids     │ │Montant   │ │Alertes │ │
│  │du jour   │ │total     │ │à payer   │ │        │ │
│  │24        │ │3,2 t     │ │1,8M FCFA │ │7       │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────┘ │
│                                                     │
│  📊 Graphique : Évolution des collectes (7 jours)   │
│  ▁▂▃▅▇▆▄                                            │
│                                                     │
│  ⚠️ Alertes en attente :                            │
│  • 5 paiements producteurs en retard                │
│  • 2 lots qualité < seuil (humidité > 8 %)          │
│  • Stock sacs vides insuffisant                     │
│                                                     │
│  🏆 Top collecteurs du mois                         │
│  1. Konan Y. — 45 collectes                          │
│  2. Yao M.  — 38 collectes                           │
└─────────────────────────────────────────────────────┘
```

**Fonctionnalités :**
- KPIs temps réel (collectes, poids, montants)
- Graphiques journaliers/hebdomadaires/saisonniers
- Liste des alertes cliquables
- Classement des collecteurs
- Export PDF/Excel en 1 clic

---

### Vue 2 : Gestion des adhérents (producteurs)
**Liste + fiches détaillées des producteurs membres.**

```
┌─────────────────────────────────────────────────────┐
│  ADHÉRENTS                    [+ Ajouter] [🔍 Rech.]│
├─────────────────────────────────────────────────────┤
│  Filtres : [Zone ▾] [Statut ▾] [Campagne ▾]        │
├─────────────────────────────────────────────────────┤
│  #  Nom            Parcelle    Total livré  Solde   │
│  1  KOFFI A.       GPS: 7.2/-5 │ 2,4 t      ✓ Payé │
│  2  YAO B.         GPS: 7.4/-6 │ 1,8 t      45K FCFA│
│  3  KONAN C.       GPS: 7.1/-5 │ 3,1 t      ✓ Payé │
│  ...                                                │
├─────────────────────────────────────────────────────┤
│  Pagination : < 1 2 3 ... 12 >                      │
└─────────────────────────────────────────────────────┘
```

**Vue fiche producteur (au clic) :**
- **Onglet 1 — Identité** : nom, prénom, téléphone, CIN, photo, date adhésion, statut actif/inactif
- **Onglet 2 — Parcelle(s)** : carte avec point GPS, superficie, variété (cacao, anacarde...), année plantation
- **Onglet 3 — Historique collectes** : tableau chronologique (date, poids, qualité, prix, paiement)
- **Onglet 4 — Paiements** : solde dû, historique mobile money, reçus téléchargeables
- **Onglet 5 — Documents** : scan CIN, certificat bio/Rainforest, photos parcelle

**Fonctionnalités :**
- Recherche par nom/téléphone
- Import Excel/CSV en masse (pour migrer depuis tableurs)
- Attribution d'un QR code unique par producteur
- Carte interactive des parcelles (Leaflet.js ou Google Maps)
- Statut "à risque" si taux d'humidité répété bas

---

### Vue 3 : Suivi des collectes
**Le cœur du système : toutes les collectes saisies par les collecteurs terrain.**

```
┌─────────────────────────────────────────────────────┐
│  COLLECTES              [+ Nouvelle] [Importer CSV] │
├─────────────────────────────────────────────────────┤
│  Date : [01/10/2026 ▾]  Collecteur : [Tous ▾]      │
│  Qualité : [Toutes ▾]   Zone : [Toutes ▾]          │
├─────────────────────────────────────────────────────┤
│  ID    Date    Producteur   Poids   Qual.  Montant  │
│  #1042 01/10   KOFFI A.     120 kg  A      96 000  │
│  #1041 01/10   YAO B.       85 kg   B      63 750  │
│  #1040 01/10   KONAN C.     210 kg  A      168 000 │
│  ...                                                │
├─────────────────────────────────────────────────────┤
│  Totaux filtrés : 24 collectes | 3,2 t | 1,8M FCFA  │
└─────────────────────────────────────────────────────┘
```

**Fonctionnalités :**
- Saisie manuelle (si admin saisit au bureau)
- Visualisation des données synchronisées depuis le terrain
- Validation/rejet des collectes en attente
- Modification avec journal d'audit (qui a changé quoi, quand)
- Détail d'une collecte : photos pesée, signature producteur, notes

---

### Vue 4 : Paiements producteurs
**Gestion centralisée des paiements via mobile money.**

```
┌─────────────────────────────────────────────────────┐
│  PAIEMENTS                                          │
├─────────────────────────────────────────────────────┤
│  ☐ Tout sélectionner                                │
│  Producteur   Téléphone     Montant    Opérateur    │
│  ☐ KOFFI A.   07 12 34 56   96 000    Orange Money  │
│  ☐ YAO B.     05 98 76 54   63 750    MTN MoMo      │
│  ☐ KONAN C.   01 23 45 67   168 000   Wave          │
├─────────────────────────────────────────────────────┤
│  [💸 Payer sélection (3)] → Total : 327 750 FCFA    │
└─────────────────────────────────────────────────────┘
```

**Fonctionnalités :**
- Sélection multiple → paiement groupé en 1 clic (via API CinetPay/Julaya)
- Envoi automatique SMS de confirmation au producteur
- Reçu numérique archivé
- Gestion des échecs de paiement (retry, paiement manuel)
- Rapprochement comptable (export SYSCOA)
- Historique complet par producteur et par période

---

### Vue 5 : Rapports & Traçabilité
**Génération des documents exigés par les acheteurs et certificateurs.**

```
┌─────────────────────────────────────────────────────┐
│  RAPPORTS                                           │
├─────────────────────────────────────────────────────┤
│  📄 Rapport de campagne (période ▾)                 │
│  📄 Traçabilité par lot (sélection lot ▾)           │
│  📄 Conformité EUDR (parcelles géolocalisées)       │
│  📄 Certification Rainforest/Fairtrade              │
│  📄 Synthèse financière mensuelle                   │
│  📄 Performance collecteurs                         │
├─────────────────────────────────────────────────────┤
│  [⬇️ Générer PDF]  [📧 Envoyer par email]           │
└─────────────────────────────────────────────────────┘
```

**Fonctionnalités :**
- Templates pré-formatés aux standards des acheteurs (SOGECACAO, Olam, Barry Callebaut)
- Export PDF avec logo coopérative + QR code vérification
- Conformité réglementation UE déforestation (parcelles + coordonnées GPS)[1]
- Envoi automatique planifié (chaque lundi matin au président)
- Partage sécurisé avec lien (pour un acheteur qui veut vérifier)

---

### Vue 6 : Paramètres
**Configuration propre à chaque coopérative.**

```
┌─────────────────────────────────────────────────────┐
│  PARAMÈTRES                                         │
├─────────────────────────────────────────────────────┤
│  👥 Utilisateurs (collecteurs, admins)              │
│  💰 Prix d'achat par produit/qualité                │
│     Cacao A : 800 FCFA/kg | Cacao B : 750 FCFA/kg   │
│  📱 Comptes mobile money (CinetPay)                 │
│  🗺️ Zones de collecte                              │
│  📊 Seuils d'alerte (humidité, poids max)           │
│  🏢 Infos coopérative (logo, N° RCCM, TVA)          │
└─────────────────────────────────────────────────────┘
```

---

## 2. Module COLLECTEUR (App mobile Android)

### Vue 7 : Accueil collecteur
```
┌──────────────────────┐
│  👋 Konan Y.         │
│  ● Hors-ligne        │
│  ⟳ 12 en attente     │
│  ──────────────────  │
│  [📷 Scanner QR]     │
│  [➕ Nouvelle collecte]│
│  [📋 Mes collectes   │
│      du jour : 8]    │
└──────────────────────┘
```

**Fonctionnalités :**
- Indicateur réseau visible (vert = connecté, orange = hors-ligne)
- Nombre de collectes non synchronisées
- Bouton scanner QR code producteur (accès rapide)

---

### Vue 8 : Saisie d'une collecte
**L'écran le plus important du produit. Doit prendre moins de 60 secondes.**

```
┌──────────────────────┐
│  ← NOUVELLE COLLECTE │
│  ──────────────────  │
│  Producteur          │
│  [📷 Scanner QR]     │
│  ou [🔍 Rechercher]  │
│  ✅ KOFFI Amadou     │
│  ──────────────────  │
│  Poids (kg)          │
│  [ 120 ]             │
│  ──────────────────  │
│  Qualité             │
│  (●) A  ( ) B  ( ) C │
│  ──────────────────  │
│  Humidité (%)        │
│  [ 6,5 ]             │
│  ──────────────────  │
│  📷 Photo pesée      │
│  ──────────────────  │
│  Montant calculé :   │
│  96 000 FCFA         │
│  ──────────────────  │
│  [ ✔ VALIDER ]       │
└──────────────────────┘
```

**Fonctionnalités :**
- Scan QR → producteur pré-rempli automatiquement
- Calcul automatique du montant (poids × prix selon qualité)
- Mode hors-ligne total (sauvegarde SQLite locale)
- Photos compressées avant upload (économie data)
- Signature écran du producteur (optionnel)
- Annulation/modification avant synchronisation

---

### Vue 9 : Historique du jour
- Liste des collectes effectuées aujourd'hui
- Statut par collecte : ✓ synchronisée / ⟳ en attente
- Total du jour (nombre, poids, montant)
- Possibilité de corriger une erreur avant sync

---

## 3. Module PRODUCTEUR (USSD + WhatsApp — pas d'app)

**Réalité terrain :** les producteurs n'installeront pas une app. Le canal doit être **gratuit et universel**.

### Canal USSD (*123#)
```
*123# → Menu :
1. Voir mon solde
2. Mes dernières collectes
3. Contacter ma coopérative
```

### Canal WhatsApp Business
- Notification auto à chaque paiement : 
  > *"Bonjour Koffi, votre collecte du 01/10 (120 kg cacao A) est payée : 96 000 FCFA reçus sur Orange Money. Solde campagne : 1,2M FCFA."*
- Réponses automatiques aux questions fréquentes (prix du jour, prochaine collecte)

---

## 4. Module ACHETEUR (dashboard web externe — phase 2)

### Vue 10 : Portail traçabilité acheteur
- Connexion sécurisée par lien/token (pas de compte complexe)
- Voir l'origine d'un lot : coopérative → collecteur → producteurs → parcelles sur carte
- Télécharger les certificats de conformité (EUDR, Rainforest)
- Scanner le QR code d'un sac → voir toute sa chaîne de traçabilité

---

## 5. Matrice des rôles et accès

| View | Admin | Collecteur | Producteur | Acheteur |
|---|---|---|---|---|
| Dashboard global | ✅ | ❌ | ❌ | ❌ |
| Adhérents | ✅ | Lecture | Son profil | ❌ |
| Collectes | ✅ CRUD | ✅ Create | Lecture (siennes) | Lot acheté |
| Paiements | ✅ | ❌ | Notification | ❌ |
| Rapports | ✅ | ❌ | ❌ | ✅ son lot |
| Paramètres | ✅ | ❌ | ❌ | ❌ |

---

## 6. Priorisation pour le MVP (ordre de développement)

| Sprint | Views livrées | Durée estimée |
|---|---|---|
| **Sprint 1** | Vue 7, 8, 9 (mobile collecteur offline-first) | 4 semaines |
| **Sprint 2** | Vue 2, 3 (adhérents + suivi collectes web) | 3 semaines |
| **Sprint 3** | Vue 1, 6 (dashboard + paramètres) | 2 semaines |
| **Sprint 4** | Vue 4 (paiements mobile money CinetPay) | 3 semaines |
| **Sprint 5** | Vue 5 (rapports PDF + export traçabilité) | 2 semaines |
| **Phase 2** | USSD/WhatsApp producteur + portail acheteur | Après premiers clients |

> **Conseil :** Les sprints 1-3 suffisent pour le pilote gratuit. Tu peux tester la valeur auprès des coopératives **sans le module paiement**, en commençant par "numériser le carnet de collecte". Le paiement mobile money vient ensuite comme argument de conversion vers l'abonnement payant.

Tu veux que je fasse le **modèle de base de données** (schéma PostgreSQL des tables producteurs, collectes, paiements...) ou le **cahier des charges API** (endpoints REST) pour lancer le développement ?