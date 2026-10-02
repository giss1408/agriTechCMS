## 🎯 Focus : Gestion de coopératives + CRM de collecte agricole

C'est le modèle le plus viable pour un premier SaaS agritech en Côte d'Ivoire. Voici un plan détaillé, de l'architecture technique aux premiers clients.

---

## 1. Les concurrents existants (ce qui marche déjà)

Le marché ivoirien a déjà plusieurs acteurs, mais **rien n'est dominant** dans le créneau "gestion de coopératives + CRM de collecte". Voici la carte concurrentielle :

| Startup | Modèle | Ce qu'elle fait | Ce qui manque |
|---|---|---|---|
| **Investiv** | Agriculture de précision | Drones + capteurs + WeFly GIS (géolocalisation, traçage production) | Levé 1,5 M$ Série A en 2021 https://agriculture.ci/2025/07/21/lavenir-de-lagriculture-ivoirienne-les-start-ups-agritech-cles-a-suivre-en-2025/. Pas de module CRM de collecte ni de paiement mobile money intégré https://agriculture.ci/2025/07/21/lavenir-de-lagriculture-ivoirienne-les-start-ups-agritech-cles-a-suivre-en-2025/ |
| **Jool International** | Gestion intelligente de plantations | Jool Monitor (données drones), Jool Spray (pulvérisation par drone) | Levé 3 M$ en 2022 https://digitalmag.ci/agritech-3-startups-qui-se-demarquent-dans-lagriculture-de-precision-en-cote-divoire/. Acquis WeFly Agri https://agriculture.ci/2025/07/21/lavenir-de-lagriculture-ivoirienne-les-start-ups-agritech-cles-a-suivre-en-2025/. Focus hardware + data, pas SaaS de gestion coopérative https://digitalmag.ci/agritech-3-startups-qui-se-demarquent-dans-lagriculture-de-precision-en-cote-divoire/ |
| **Trusty (Trustineo)** | Traçabilité blockchain cacao | Blockchain pour traçabilité complète, QR code pour consommateur européen | Levé 2 M$ (Partech Africa, Enza Capital) https://agriculture.ci/2025/07/21/lavenir-de-lagriculture-ivoirienne-les-start-ups-agritech-cles-a-suivre-en-2025/. Solution premium, pas accessible aux petites coopératives https://agriculture.ci/2025/07/21/lavenir-de-lagriculture-ivoirienne-les-start-ups-agritech-cles-a-suivre-en-2025/ |
| **Wi Agri** | Marketplace agri | Met en relation agriculteurs + acheteurs selon prévisions de récolte | Pas de module de gestion de coopérative ni CRM https://www.agencewebgram.com/2026/09/Comment-l-Agri-Tech-et-les-logiciels-de-gestion-transforment-l-agriculture-africaine.html |
| **SmartERP (WebGram, Sénégal)** | ERP intégré agriculture | Gestion complète pour exploitations agricoles | Solution sénégalaise, pas adaptée CI (TVA CNPS, SYSCOA, mobile money) https://www.agencewebgram.com/2026/09/Comment-l-Agri-Tech-et-les-logiciels-de-gestion-transforment-l-agriculture-africaine.html |

**L'opportunité :** Il n'existe pas encore de SaaS local **100 % adapté à la CI** qui combine : gestion coopérative + CRM collecte + paiement mobile money + conformité fiscale locale + accessibilité prix bas.

---

## 2. Architecture technique du SaaS

### Stack recommandée (coût maîtrisé, scalable)

| Couche | Technologie | Pourquoi |
|---|---|---|
| **Frontend mobile** | Flutter (Android + iOS) | Un seul codebase, offline-first natif, fonctionne sans connexion (zones rurales) |
| **Frontend web** | React.js ou Vue.js | Dashboard pour dirigeants de coopératives et acheteurs |
| **Backend** | Node.js (NestJS) ou Python (FastAPI) | API REST, scalable, écosystème riche |
| **Base de données** | PostgreSQL (cloud) + SQLite local (mobile) | PostgreSQL pour données relationnelles complexes, SQLite pour synchronisation offline |
| **Cloud** | AWS ou DigitalOcean (Frasca, région Europe) | Coût maîtrisé, latence acceptable depuis l'Afrique |
| **Paiement** | API CinetPay ou Julaya | Unifie Orange Money, MTN MoMo, Wave CI https://agriculture.ci/2025/07/21/lavenir-de-lagriculture-ivoirienne-les-start-ups-agritech-cles-a-suivre-en-2025/ |
| **Authentification** | JWT + numéro de téléphone | Pas de email dans les zones rurales, SMS OTP pour connexion |
| **Notifications** | SMS (Twilio ou local) + WhatsApp Business API | SMS obligatoire en zone rurale, WhatsApp pour les urbains |

### Modules fonctionnels

```
1. ADMIN (dirigeant coopérative)
   ├── Tableau de bord (collectes du jour, encaissements, alertes)
   ├── Gestion des adhérents (ajout, fiche producteur, parcelle GPS)
   ├── Gestion des collectes (saisie ou import)
   ├── Rapports (mensuels, exportables)
   ├── Paramètres (taux TVA, CNPS, seuils d'alerte)
   └── Historique complet (traçabilité par producteur)

2. COLLECTEUR (terrain, mobile)
   ├── Saisir une collecte (producteur, quantité, qualité, prix)
   ├── Scanner code QR producteur (si déjà enregistré)
   ├── Mode hors-ligne (sauvegarde locale, sync quand connexion)
   ├── Historique des collectes du jour
   └── Alertes (paiements en attente, producteur en retard)

3. PRODUCTEUR (optionnel, app légère)
   ├── Voir ses collectes passées
   ├── Solde en temps réel
   ├── Recevoir notifications SMS/WhatsApp
   └── Historique par campagne

4. ACHETEUR (dashboard B2B, optionnel)
   ├── Voir les livraisons en temps réel
   ├── Exporter rapports de traçabilité
   ├── Certificats (Rainforest, Fairtrade, UE deforestation)
   └── Facturation intégrée
```

### Flux de synchronisation offline-first

```
Collecteur en zone sans réseau
    ↓
Saisie sur app mobile → données stockées en SQLite local
    ↓
Collecteur revient en zone couverte (4G Orange/MTN)
    ↓
Sync automatique avec serveur cloud (différentiel, pas de overwrite)
    ↓
Validation admin → génération rapport + paiement mobile money
```

---

## 3. Plan de lancement (0 à 12 mois)

### Phase 1 : MVP (Mois 1-4)
**Objectif :** Produit fonctionnel avec 1 coopérative pilote

| Action | Détail |
|---|---|
| **Recruter** | 1 développeur backend (Node.js), 1 développeur mobile (Flutter), 1 product manager (toi ou un associé) |
| **Cibler pilote** | Trouver 1 coopérative cacao/anacarde dans le sud-ouest (Daloa, Issia, Lakota) via réseaux locaux ou incubateurs (Hub1040, Seedspace) https://digitalmag.ci/agritech-3-startups-qui-se-demarquent-dans-lagriculture-de-precision-en-cote-divoire/ |
| **Développer** | Modules : gestion adhérents, saisie collectes, dashboard admin, sync offline |
| **Déployer** | Installer sur 2-3 téléphones collecteurs + 1 tablette admin |
| **Coût** | ~15-25 millions FCFA (salaires 4 mois + cloud + SMS) |

### Phase 2 : Premiers clients (Mois 5-8)
**Objectif :** 5 coopératives payantes

| Action | Détail |
|---|---|
| **Pricing pilote** | 10 000 FCFA/mois pendant 3 mois (gratuit), puis 20 000 FCFA/mois après |
| **Acquisition** | Présence sur salons agricoles (Salon International de l'Agriculture d'Abidjan), référencement via MBC Agri-Business Accelerator https://digitalmag.ci/agritech-3-startups-qui-se-demarquent-dans-lagriculture-de-precision-en-cote-divoire/, bouche-à-oreille |
| **Support** | 1 technicien terrain (déplacement hebdomadaire dans les coopératives) |
| **Intégrer** | Module paiement mobile money via CinetPay/Julaya |
| **Coût** | ~8-12 millions FCFA (support + marketing + infrastructure) |

### Phase 3 : Scaling (Mois 9-12)
**Objectif :** 20-30 coopératives, levée de fonds

| Action | Détail |
|---|---|
| **Levée de fonds** | Postuler au **Digital Africa Seed Fund 2026** (jusqu'à 100 K€ pré-amorçage, CI éligible)[6] |
| **Étendre** | Module CRM pour acheteurs/traders (50 000-200 000 FCFA/mois) |
| **Recruter** | 1 commercial terrain, 1 support client, 1 développeur supplémentaire |
| **Certifications** | Module premium traçabilité UE (réponse à la regulation déforestation) https://agriculture.ci/2025/07/21/lavenir-de-lagriculture-ivoirienne-les-start-ups-agritech-cles-a-suivre-en-2025/ |
| **Objectif revenus** | 30 coopératives × 20 000 FCFA = **600 000 FCFA/mois** + CRM acheteurs × 3 = **+450 000 FCFA/mois** = **1,05 million FCFA/mois** |

---

## 4. Économie du modèle (prévisionnel)

### Coûts annuels (année 1)

| Poste | Coût annuel (FCFA) |
|---|---|
| Salaires (3 personnes) | 36-48 millions |
| Cloud + SMS + API | 2-3 millions |
| Marketing terrain | 3-4 millions |
| Support terrain | 2-3 millions |
| **Total** | **43-58 millions** |

### Revenus potentiels (année 2, avec 50 coopératives + 5 acheteurs)

| Source | Détail | Revenu mensuel (FCFA) | Revenu annuel (FCFA) |
|---|---|---|---|
| Abonnement coopératives | 50 × 25 000 | 1 250 000 | 15 millions |
| CRM acheteurs | 5 × 100 000 | 500 000 | 6 millions |
| Commission transactions | 1 % sur collectes (estimé 500 M FCFA/an) | - | 5 millions |
| Module certification | 20 × 30 000 | 600 000 | 7,2 millions |
| **Total** | | **2 350 000/mois** | **33,2 millions** |

> **Seuil de rentabilité :** environ 15-20 coopératives payantes (vers mois 10-14). La levée de fonds Digital Africa Seed Fund (jusqu'à 100 K€ ≈ 65 millions FCFA) permet de couvrir les pertes jusqu'à ce seuil[6].

---

## 5. Ce qu'il faut faire dès maintenant

1. **Valider le problème** : parler à 10-15 dirigeants de coopératives (cacao, anacarde, mangue) pour confirmer que la gestion papier/tableur est bien leur problème n°1
2. **Postuler au Digital Africa Seed Fund 2026** (candidatures ouvertes, éligible CI)[6]
3. **Rejoindre un incubateur local** : Hub1040 ou Seedspace Abidjan (focus agritech + fintech) https://digitalmag.ci/agritech-3-startups-qui-se-demarquent-dans-lagriculture-de-precision-en-cote-divoire/
4. **Trouver un co-fondateur technique** (développeur fullstack ou mobile) si tu n'es pas développeur toi-même
5. **Regarder les salons** : Salon International de l'Agriculture d'Abidjan (souvent en novembre-décembre) pour rencontrer les coopératives

Tu veux que je détaille un point précis (par exemple le cahier des charges technique du MVP, le pitch pour les investisseurs, ou la stratégie d'acquisition terrain) ?




L'agriculture ivoirienne est un secteur qui "marche" pour un SaaS parce qu'il combine **une nécessité critique**, **un pouvoir de paiement**, et **une transformation numérique en cours**. Voici les 5 raisons structurelles :

## 1. Le cacao, une filière sous pression réglementaire internationale

La Côte d'Ivoire produit environ **40 % du cacao mondial**[2]. Les acheteurs européens (chocolatiers, transformateurs) sont soumis à la **réglementation UE sur la déforelation** (EUDR), qui exige une traçabilité par parcelle de production. Les coopératives ivoiriennes doivent prouver que leur cacao ne provient pas de zones déforestées, avec géolocalisation exacte, dates de récolte, et historique.

Les coopératives gèrent cela sur papier ou Excel aujourd'hui. Un SaaS de traçabilité n'est pas un "plus" — c'est une **condition de survie commerciale**. Les acheteurs internationaux vont imposer l'outil comme contition d'achat.

## 2. Un pouvoir de paiement réel

Les coopératives ivoiriennes **collectent et vendent des milliards de FCFA par saison**. Une coopérative cacao moyenne gère des millions de transactions par campagne. Le SaaS ne se vend pas à des paysans pauvres — il se vend à des **structures professionnelles** qui :
- Encaissent des paiements mobile money (Orange Money, MTN MoMo, Wave CI)
- Paient des salaires à des collecteurs et administratifs
- Achètent des intrants pour leurs membres
- Facturent des acheteurs internationaux

Le modèle de revenus est donc **B2B avec pouvoir de paiement**, pas B2C avec paiement micro-transactions.

## 3. Un marché fragmenté, pas de dominant

Le marché agritech ivoirien est dominé par des startups **high-tech / hardware** (drones, satellites, capteurs) :
- **Investiv** (levé 1,5 M$ Série A, 2021) : drones + géolocalisation[1]
- **Jool International** (levé 3 M$, 2022) : gestion intelligente de plantations, Jool Spray par drone[3]
- **Trusty/Trustineo** (levé 2 M$, 2022) : traçabilité blockchain premium[1]

Aucune n'adresse le **cœur de métier quotidien des coopératives** : gestion des adhérents, saisie des collectes, suivi des paiements, génération de rapports. C'est un créneau **low-tech, high-impact**, avec des concurrents directs quasi inexistants.

## 4. L'infrastructure mobile money mature

La Côte d'Ivoire dispose de **34 millions de comptes mobile money actifs** pour 27 millions d'habitants, traitant plus de **20 milliards $ de transactions annuelles**[1]. Les APIs de paiement sont matures (CinetPay, Julaya)[1]. Cela signifie :
- Tes clients peuvent payer ton abonnement SaaS en FCFA par mobile money
- Ton SaaS peut intégrer les paiements aux producteurs (plus de chèques, plus de cash)
- Tu peux facturer par transaction (commission sur collectes)

L'infrastructure est là, contrairement à de nombreux pays africains où le paiement digital est encore embryonnaire.

## 5. Un écosystème de soutien actif

Plusieurs programmes ciblent spécifiquement ce créneau :
- **MBC Africa Agri-Business Accelerator** : accompagne les startups de la chaîne de valeur agricole[3]
- **Digital Africa Seed Fund 2026** : jusqu'à 100 K€ en pré-amorçage pour agritech en CI[6]
- **Orange Fab CI** : 10 millions FCFA par startup[3]
- **Climate Smart Agriculture Youth Network (CSAYN)** : focus agriculture climato-intelligente[3]
- **Start-up Boost Capital, FILT, FII** : mécanismes de financement public en cours de développement[1]

Ces programmes fournissent **mentorat, financement, et réseau** — ce qui réduit considérablement le risque de lancement.

---

## ⚠️ Les risques réels (pour être honnête)

| Risque | Impact | Mitigation |
|---|---|---|
| **Adoption lente des coopératives** | Moyenne | Pilote gratuit pendant 3 mois, support terrain intensif |
| **Connectivity en zone rurale** | Moyenne | Architecture offline-first (SQLite local, sync 4G) |
| **Concurrence de solutions internationales** | Faible | Elles ne sont pas adaptées CI (TVA, CNPS, SYSCOA, mobile money) |
| **Pouvoir de paiement limité des petites coopératives** | Moyenne | Cibler d'abord les coopératives de taille moyenne (200+ producteurs) |
| **Changement de réglementation (EUDR)** | Faible | Ton SaaS devient PLUS nécessaire si la régulation se durcit |

---

## 🎯 En résumé

Ce secteur marche parce que :

1. **Les coopératives ont un problème critique** (traçabilité exigée par l'UE)
2. **Elles ont de l'argent** (milliards de FCFA de transactions saisonnières)
3. **Personne ne leur vend de solution adaptée** (les startups existantes font du drone/blockchain, pas de gestion quotidienne)
4. **L'infrastructure digitale est prête** (mobile money, 4G, APIs)
5. **Le financement et l'accompagnement existent** (Digital Africa Seed Fund, Orange Fab, MBC Accelerator)

Ce n'est pas un secteur "sexy" comme la fintech ou l'IA, mais c'est un secteur **réel, avec des clients qui paient, un problème urgent, et peu de concurrence directe**. C'est exactement le profil d'un SaaS B2B qui peut devenir rentable et scalable.

Tu veux qu'on détaille la stratégie d'acquisition des premiers clients (qui contacter, comment les convaincre, quel discours utiliser) ?



## 🎯 Stratégie d'acquisition des 10 premiers clients

L'acquisition en agritech ivoirien est **terrain, relationnelle et saisonnière**. Voici le plan concret.

---

## 1. Qui contacter (liste ciblée)

### Les cibles prioritaires (coopératives de 200-500 producteurs)

| Filière | Zone géographique | Comment les trouver |
|---|---|---|
| **Cacao** | Sud-Ouest (Daloa, Issia, Lakota, Zoukougbeu) | SOGECACAO, COFACE, CECOP, Union des Coopératrices de Côte d'Ivoire (UCI-CI) |
| **Anacarde (cashew)** | Centre-Nord (Korhogo, Ferkessédougou, Boundiali) | UNACAD, coopératives de l'ONECA (Office National de Commercialisation des Amandes de Cajou) |
| **Mangue / Fruits** | Sud (Abidjan périphérie, Dabou, Grand-Lahou) | Groupements de femmes, périmètres irrigués, coopératives de transformation |
| **Hévéa** | Centre-Est (Dikodougou, Abengourou) | Coopératives liées à SOCFIPH (Société de Fibres et Plastiques) |

### Les relais clés (ceux qui peuvent te mettre en contact)

| Relai | Pourquoi | Comment les joindre |
|---|---|---|
| **MBC Africa Agri-Business Accelerator** | Accélère des agritechs, connaît toutes les coopératives | Site web, LinkedIn, email contact |
| **Hub1040 / Seedspace Abidjan** | Incubateurs tech, réseau d'anciens dans l'agri | Candidature programme d'accompagnement |
| **Digital Africa Seed Fund** | Programme de financement, réseau de mentors | Candidature en ligne (candidatures ouvertes)[6] |
| **ONG agricoles** : GIZ, USAID, FAO | Travaillent avec des coopératives cibles | Email contact programme agriculture CI |
| **Chambre d'Agriculture de CI** | Regroupe 80 % des coopératives | Siège à Abidjan, téléphone 07 07 07 XX XX |
| **Banques agricoles** : BOA CI, BICICI, Coris Bank | Connaissent les coopératives solvables | Commercial terrain, agences zones rurales |

---

## 2. Le discours (pitch qui marche)

### Problème : ne pas dire "digitalisation" ou "SaaS"

Les dirigeants de coopératives ne se reconnaissent pas dans ces mots. Voici le bon angle :

**❌ Ce qui ne marche pas :**
> "Bonjour, nous avons un SaaS cloud de gestion de coopératives avec synchronisation offline-first..."

**✅ Ce qui marche :**

> "Bonjour, nous aidons les coopératives à **suivre exactement combien chaque producteur a livré**, **payer automatiquement par mobile money**, et **générer les rapports demandés par les acheteurs européens** (traçabilité, certification).
> 
> Aujourd'hui, beaucoup de coopératives perdent des données sur papier, et les acheteurs demandent de plus en plus de preuves de traçabilité. Notre outil résout ça : le collecteur saisit sur téléphone, les données sont sauvegardées même sans réseau, et le dirigeant a un tableau de bord avec tout en temps réel.
> 
> On propose un **essai gratuit de 3 mois** avec 2 téléphones et 1 tablette. Si ça ne vous aide pas, on repart. Pas d'engagement."

### Les 3 arguments clés

1. **Traçabilité EU** : "C'est exigé par l'Europe, on vous aide à être conformes"[1]
2. **Paiement mobile money** : "Plus de cash, plus de pertes, les producteurs reçoivent directement sur leur téléphone"[1]
3. **Essai gratuit sans engagement** : "On installe, on forme, vous testez. Si ça marche pas, on repart"

---

## 3. Le plan d'action terrain (Mois 1-3)

### Semaine 1-2 : Préparation

```
Action 1 : Créer une démo live (pas juste des slides)
  ├── Installer le MVP sur 2 téléphones Android
  ├── Simuler 10 producteurs fictifs + 5 collectes
  ├── Préparer un rapport de traçabilité exportable (PDF)
  └── Tester le flux de paiement mobile money (CinetPay sandbox)

Action 2 : Préparer un flyer A5 en français + langues locales
  ├── Titre : "Suivez vos collectes, payez vos producteurs, traçabilité EU"
  ├── 3 points clés (traçabilité, paiement, gratuit 3 mois)
  ├── QR code vers démo en ligne
  └── Numéro WhatsApp + email

Action 3 : Identifier 20 coopératives cibles
  ├── Contacter MBC Accelerator pour liste de coopératives partenaires[3]
  ├── Contacter Digital Africa Seed Fund pour referrals[6]
  ├── Lister les coopératives cacao de Daloa (zone dense)
  └── Lister les coopératives anacarde de Korhogo (zone dense)
```

### Semaine 3-6 : Premiers contacts

```
Action 1 : Déplacer dans le sud-ouest (Daloa, 4 jours/semaine)
  ├── Visiter 3-4 coopératives par jour
  ├── Proposer démo live + essai gratuit
  ├── Prendre contacts directs (président, secrétaire, trésorier)
  └── Noter objections et questions récurrentes

Action 2 : Participer à 1 salon/agro-event
  ├── Salon International de l'Agriculture d'Abidjan (novembre-décembre)
  ├── Forum de l'Anacarde (souvent à Korhogo)
  └── Stand simple : 1 tablette avec démo + flyer

Action 3 : Obtenir 2-3 premiers pilotes
  ├── Coopération 1 : Cacao, Daloa, 200+ producteurs
  ├── Coopération 2 : Anacarde, Korhogo, 150+ producteurs
  └── Coopération 3 : Mangue, Grand-Lahou, 100+ producteurs
```

### Semaine 7-12 : Onboarding des pilotes

```
Action 1 : Installer sur le terrain
  ├── Former 2 collecteurs par coopérative (2h de formation)
  ├── Former 1 dirigeant au dashboard (1h de formation)
  ├── Laisser 2 téléphones + 1 tablette pendant 3 mois
  └── Passer 1 fois par semaine pour support terrain

Action 2 : Collecter feedback
  ├── Journal d'usage (quand ils utilisent, pourquoi pas)
  ├── Interview hebdomadaire (15 min, questions ouvertes)
  ├── Ajuster MVP en fonction des retours
  └── Documenter les cas d'usage réels

Action 3 : Preuves sociales
  ├── Demander 1 témoignage vidéo (30 sec) d'un dirigeant satisfait
  ├── Créer 1 étude de cas chiffrée ("Coopérative X : 50 collectes/jour, 0 erreur")
  └── Partager sur LinkedIn + réseaux agricoles
```

---

## 4. Canal d'acquisition prioritaire (par ordre d'importance)

### 1. Réseaux de coopératives (le plus puissant)

**Pourquoi ça marche :** Les coopératives ivoiriennes fonctionnent en **réseau**. Une coopérative cacao de Daloa connaît toutes les autres. Si tu convaincs la présidente de l'UCI-CI (Union des Coopératrices de CI), tu as accès à 50+ coopératives en 1 coup.

**Comment faire :**
- Contacter l'**UCI-CI** (Union des Coopératrices de Côte d'Ivoire) : proposition d'essai gratuit pour toutes leurs membres
- Contacter la **COCOBOD** (pour le Ghana, mais aussi partenaire CI)
- Contacter **SOGECACAO** (premier acheteur de cacao) : ils ont intérêt à ce que leurs coopératives partenaires soient bien traçables

### 2. ONG et bailleurs (le plus rapide pour crédibilité)

**Pourquoi ça marche :** Les ONG (GIZ, USAID, FAO, Union Européenne) **subventionnent déjà des coopératives** pour la digitalisation. Si tu es "recommandé" par une ONG, tu as la confiance immédiate.

**Comment faire :**
- Contacter le programme **DigiGreen & Agri** (UE + GIZ en CI)[1]
- Contacter **USAID Feed the Future** (présent en CI, focus agriculture)
- Proposer un partenariat : "On fournit le logiciel, vous le recommandez à vos coopératives partenaires"

### 3. Salons et événements (le plus visible)

**Pourquoi ça marche :** Les événements agricoles réunissent **toute la chaîne de valeur** (coopératives, acheteurs, ONG, instituts techniques). C'est un point de contact concentré.

**Comment faire :**
- **Salon International de l'Agriculture d'Abidjan** (novembre-décembre) : stand ou participation
- **Forum de l'Anacarde** (Korhogo, souvent en fin d'année) : cible anacarde
- **VivaTech Paris 2026** : la CI expose 30 startups/PME tech, dont agritech[4] — excellent pour visibilité internationale

### 4. LinkedIn + WhatsApp (le plus scalable)

**Pourquoi ça marche :** Les dirigeants de coopératives de taille moyenne sont sur **LinkedIn et WhatsApp**. C'est un canal sous-exploité en agritech CI.

**Comment faire :**
- Créer contenu éducatif : "Comment la traçabilité EU change vos ventes de cacao", "3 erreurs de gestion de coopérative que vous pouvez éviter"
- Poster sur LinkedIn + partager dans groupes WhatsApp agricoles
- Utiliser **WhatsApp Business API** pour messaging ciblé

---

## 5. Objections fréquentes et réponses

| Objection | Réponse |
|---|---|
| **"C'est trop cher pour nous"** | "L'essai est gratuit 3 mois. Ensuite, c'est 20 000 FCFA/mois — moins cher qu'un collecteur. Et vous gagnez en efficacité" |
| **"On n'a pas de réseau ici"** | "L'application fonctionne sans internet. Les collecteurs saisissent sur téléphone, les données se synchronisent quand ils reviennent en zone couverte" |
| **"On a toujours fait comme ça (sur papier)"** | "Le papier, c'est bien pour commencer. Mais les acheteurs européens demandent maintenant des preuves de traçabilité. Avec le papier, c'est difficile. Avec notre outil, c'est automatique" |
| **"On n'a jamais utilisé d'application"** | "On forme vos collecteurs en 2 heures. C'est plus simple qu'un téléphone : ils scannent un QR code, saisissent le poids, et c'est tout. On reste 1 semaine pour les accompagner" |
| **"On va regarder et on revient vers vous"** | "Pas de problème. Je vous laisse cette tablette avec la démo. Voici mon WhatsApp. Si vous avez une question, envoyez-moi un message. Et je repasse dans 2 semaines" |

---

## 6. KPIs à suivre (Mois 1-6)

| KPI | Cible Mois 3 | Cible Mois 6 |
|---|---|---|
| Coopératives contactées | 30 | 80 |
| Démos réalisées | 15 | 40 |
| Pilotes en cours | 3 | 8 |
| Coopératives payantes | 1 | 5 |
| NPS (satisfaction) | > 30 | > 50 |
| Taux d'adoption (collecteurs actifs/jour) | > 60 % | > 80 % |

---

## 📌 Prochaines étapes concrètes

1. **Cette semaine :** Créer la démo live sur 2 téléphones + flyer A5
2. **Cette semaine :** Contacter MBC Accelerator + Digital Africa Seed Fund pour referrals[3][6]
3. **Mois prochain :** Déplacer 4 jours/semaine à Daloa (zone dense en coopératives cacao)
4. **Mois 2 :** Obtenir 2-3 pilotes + commencer l'onboarding
5. **Mois 3 :** Collecter premiers témoignages + ajuster le produit

Tu veux que je prépare le **script de premier appel téléphonique** ou le **template de premier email de prospection** ?