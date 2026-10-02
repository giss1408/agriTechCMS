# Vision produit

> Source consolidée de `archive/ConceptAgriTech.md` et `archive/CommentAgriTech.md`.
> Ce document est la référence : en cas de contradiction avec l'archive, c'est lui qui fait foi.

## Le problème

Les coopératives agricoles ivoiriennes (cacao, anacarde) gèrent leurs **collectes**, leurs **paiements aux
producteurs** et leurs **rapports pour les acheteurs** sur carnet papier ou Excel. Conséquences :

- pertes et erreurs de saisie (poids, qualité, montant dû) ;
- paiements en cash, lents, sans preuve ;
- impossibilité de prouver l'origine d'un lot (parcelle, producteur, date) alors que les acheteurs
  européens l'exigent de plus en plus (règlement UE contre la déforestation — EUDR, certifications
  Rainforest / Fairtrade).

## La réponse : un « carnet de collecte numérique » qui fait trois choses

| # | Promesse au dirigeant | Ce que le produit fait |
|---|---|---|
| 1 | « Vous savez exactement ce que chaque producteur a livré. » | Le collecteur saisit la pesée sur un téléphone Android en moins de 60 s, **même sans réseau**. Le montant est calculé par le serveur à partir de la grille de prix datée. |
| 2 | « Vous payez vos producteurs sans cash. » | Paiement groupé Orange Money / MTN MoMo / Wave, déduction automatique des avances, SMS de confirmation. |
| 3 | « Vous prouvez l'origine de chaque sac. » | Les collectes sont regroupées en **lots** ; chaque lot a un lien/QR de traçabilité pour l'acheteur et un export GeoJSON des parcelles compatible EUDR. |

On ne vend pas « un SaaS » ni « la digitalisation » : on vend ces trois phrases.

## Utilisateurs

| Rôle | Support | Besoin principal |
|---|---|---|
| Dirigeant / gestionnaire de coopérative | Web (tablette ou PC) | Voir, valider, payer, prouver |
| Collecteur (pisteur) | App Android, hors-ligne | Saisir vite, sans erreur, sans réseau |
| Producteur | USSD / SMS (pas d'app) | Connaître son solde et ses livraisons |
| Acheteur / exportateur | Lien web public par lot | Vérifier l'origine d'un lot |

## Périmètre du MVP

**Dans le MVP (pilote gratuit 3 mois)**

- Connexion par code SMS (OTP) pour tous les rôles internes
- Adhérents + parcelles (point GPS ou polygone) + QR code producteur + import CSV
- Saisie des collectes hors-ligne, synchronisation, validation/rejet par l'admin
- Grille de prix versionnée par produit et qualité, seuils d'alerte (humidité, poids)
- Lots : constitution, scellage, expédition, page de traçabilité acheteur
- Paiements groupés mobile money (fournisseur « sandbox » en démo, adaptateur CinetPay à brancher)
- Avances aux producteurs déduites des paiements
- Tableau de bord, export CSV des collectes, export GeoJSON EUDR
- Menu USSD producteur (solde, dernières livraisons, prix du jour)

**Après les premiers retours (hors MVP)**

- Rapports PDF aux formats des acheteurs, envoi planifié
- WhatsApp Business (notifications riches)
- Contrôle automatique déforestation (croisement satellite)
- Unions de coopératives (multi-coopératives), portail acheteur avec compte
- Marketplace d'intrants, crédit, crédits carbone (voir les idées 3 et 4 de l'archive)

## Pourquoi commencer par là

1. **Accès direct aux producteurs** : une coopérative de 300 membres = 300 producteurs identifiés, géolocalisés,
   avec un historique de livraisons — la base de tout service futur (intrants, crédit, carbone).
2. **Données de traçabilité** : la parcelle géolocalisée est l'actif que réclament les acheteurs.
3. **Revenus récurrents** : les coopératives s'engagent sur des campagnes entières.

## Principes produit

- **Le terrain d'abord** : chaque écran collecteur doit fonctionner sans réseau, avec un pouce, au soleil.
- **Le serveur fait foi** : prix, montants, statuts sont calculés côté serveur ; le téléphone affiche une estimation.
- **Rien ne se perd, rien ne s'écrase** : chaque saisie a un identifiant créé sur le téléphone, toute modification est journalisée.
- **Pas de vocabulaire technique** devant le client.
