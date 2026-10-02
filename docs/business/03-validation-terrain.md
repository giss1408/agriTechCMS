# Validation terrain (Phase A) — à faire avant de signer le premier pilote

> Source : `archive/prochaines-etapes-v0.md`. Le MVP de ce dépôt sert de **démo live** pour ces entretiens
> (`make seed` charge une coopérative de démonstration complète).

## Objectif

Confirmer, auprès de **10 à 15 dirigeants de coopératives**, que :

1. la gestion papier/Excel des collectes est un problème prioritaire ;
2. ils ne sont pas déjà équipés (par l'État ou leur acheteur) d'un outil qui fait la même chose ;
3. ils paieraient un abonnement annuel.

## Cibles

| Filière | Zone | Taille visée |
|---|---|---|
| Cacao | Sud-Ouest : Daloa, Issia, Lakota, Zoukougbeu | 200–500 producteurs |
| Anacarde | Nord : Korhogo, Ferkessédougou, Boundiali | 150–500 producteurs |

Relais : Chambre d'Agriculture, MBC Accelerator, Hub1040 / Seedspace, ONG et programmes de bailleurs, banques
connaissant les coopératives solvables.

## Script d'entretien (20 min, questions ouvertes)

1. Comment enregistrez-vous les collectes aujourd'hui ? Qui saisit, sur quoi, quand ?
2. Combien de temps prend la préparation des rapports pour vos acheteurs ? Qui le fait ?
3. Comment payez-vous les producteurs (cash, mobile money, chèque) ? Combien de temps après la livraison ?
4. Avez-vous déjà perdu une vente ou subi une décote faute de preuve de traçabilité ?
5. Faites-vous des avances aux producteurs ? Comment les suivez-vous ?
6. **Utilisez-vous déjà un outil fourni par votre acheteur, le Conseil Café-Cacao ou une ONG ? Qu'est-ce qui ne va pas avec ?**
7. *(après la démo)* Pour un outil qui fait ça, combien seriez-vous prêts à payer par an ? Qui décide ?

Ne pas proposer de prix avant la question 7. Noter les mots exacts utilisés.

## Démo (10 min)

1. Téléphone en mode avion → saisir une collecte en scannant le QR d'un producteur.
2. Réactiver le réseau → la collecte apparaît sur le tableau de bord.
3. Valider, constituer un lot, ouvrir la page de traçabilité acheteur.
4. Lancer un paiement groupé (sandbox) → montrer le SMS de confirmation.
5. Composer le menu USSD de démo (simulateur) → solde du producteur.

## Critères de décision (go / no-go)

| Signal | Seuil « go » |
|---|---|
| Coopératives qui citent la collecte/paiement comme top 3 des problèmes | ≥ 6 / 10 |
| Coopératives **non** équipées d'un outil équivalent | ≥ 5 / 10 |
| « Oui, je paierais » avec un montant ≥ 300 000 FCFA/an | ≥ 3 / 10 |
| Coopératives prêtes à démarrer un pilote dans le mois | ≥ 2 |

Moins de 3 « oui je paierais » → **ajuster le positionnement avant d'écrire plus de code** (cible anacarde,
vente aux exportateurs, ou module paiement seul).

## Fiche de compte rendu (une par entretien)

```
Coopérative :            Filière :          Producteurs :       Zone :
Interlocuteur / rôle :
Outil actuel :           Équipé par acheteur/État ? (o/n, lequel) :
Problème n°1 cité :
Mode de paiement :       Délai de paiement :     Avances (o/n) :
Volonté de payer (montant, verbatim) :
Décideur :               Pilote possible (o/n, date) :
Objections :
```
