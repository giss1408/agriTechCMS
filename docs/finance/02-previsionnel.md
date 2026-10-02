# Prévisionnel et seuil de rentabilité

> Corrige `archive/CommentAgriTech.md` §4. L'archive annonçait un seuil de rentabilité à **15–20 coopératives** :
> c'est faux avec ses propres chiffres (20 × 25 000 FCFA × 12 = 6 M FCFA/an de revenus pour 43–58 M FCFA de
> coûts). Même le scénario « année 2 » de l'archive (33,2 M FCFA) ne couvrait pas les coûts de l'année 1.

## Formule

```
Seuil (nombre de coopératives) = coûts mensuels ÷ revenu mensuel moyen par coopérative
```

## Coûts

| Poste | Année 1 (FCFA) | Année 2 (FCFA) | Commentaire |
|---|---|---|---|
| Salaires | 36–48 M | 48–60 M | A1 : 3 personnes (back, mobile, produit/terrain). A2 : + 1 commercial terrain, + 1 support |
| Cloud, SMS, API | 2–3 M | 3–5 M | Le SMS (OTP, notifications) est le poste variable principal |
| Marketing terrain, salons | 3–4 M | 4–6 M | |
| Déplacements / support terrain | 2–3 M | 4–6 M | Passage hebdomadaire chez chaque pilote |
| **Total** | **43–58 M** | **59–77 M** | soit **3,6–4,8 M/mois** en A1, **4,9–6,4 M/mois** en A2 |

## Seuil de rentabilité

Avec ~55 000 FCFA/mois par coopérative ([01-tarification.md](01-tarification.md)) :

| Structure de coûts | Coûts mensuels | Seuil |
|---|---|---|
| Équipe année 1 | 3,6–4,8 M | **65–87 coopératives** |
| Équipe année 2 | 4,9–6,4 M | **89–116 coopératives** |

Chaque licence exportateur (ex. 5 000 t tracées × 1 000 FCFA = 5 M FCFA/an ≈ 420 000 FCFA/mois) abaisse le
seuil d'environ 8 coopératives : **c'est le levier le plus puissant à valider**.

## Scénarios

| | Année 1 | Année 2 | Année 3 |
|---|---|---|---|
| Coopératives payantes (fin d'année) | 5 | 50 | 130 |
| Coopératives payantes (moyenne sur l'année) | 2 | 30 | 95 |
| Revenus abonnements + frais | ~1,3 M | ~20 M | ~63 M |
| Licences exportateurs | 0 | 0–5 M | 5–15 M |
| **Revenus totaux** | **~1,3 M** | **20–25 M** | **68–78 M** |
| Coûts | 43–58 M | 59–77 M | 70–85 M |
| **Résultat** | **≈ –42 à –57 M** | **≈ –34 à –57 M** | **≈ –17 à +8 M** |

**Lecture :** l'équilibre se joue en année 3, et **dépend des licences exportateurs ou d'une équipe plus
légère**. Le besoin de financement cumulé avant équilibre est de l'ordre de **90–130 M FCFA (140–200 K€)** :
le Digital Africa Seed Fund (jusqu'à 100 K€ ≈ 65,6 M FCFA) ne couvre que l'année 1. Il faut prévoir une
deuxième source (subvention de programme bailleur, prêt d'honneur, revenus de licence exportateur).

## Ce qui ferait bouger ces chiffres

| Levier | Effet |
|---|---|
| Fondateur technique (pas de salaire dev la 1re année) | Coûts A1 –12 à –18 M |
| 1 contrat exportateur dès l'année 2 | Seuil –8 coopératives par tranche de 5 000 t |
| Programme bailleur finançant l'équipement de N coopératives | Revenus garantis + acquisition accélérée |
| Prix accepté plus élevé que l'hypothèse (question 7) | Seuil proportionnellement plus bas |
