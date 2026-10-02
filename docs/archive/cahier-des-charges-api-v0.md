## 📦 Cahier des charges API REST — CRM Collecte Agricole

**Stack cible :** Node.js (NestJS) ou Python (FastAPI) · PostgreSQL · JWT auth · JSON partout
**Base URL :** `https://api.votreapp.ci/v1`

---

## 0. Conventions générales

### En-têtes communs
```http
Authorization: Bearer <jwt_token>
Content-Type: application/json
Accept-Language: fr
X-Device-Id: <uuid_appareil>        # pour traçabilité sync offline
X-Idempotency-Key: <uuid>           # obligatoire sur POST critiques (collectes, paiements)
```

### Format de réponse standard
```json
{
  "success": true,
  "data": { },
  "meta": { "page": 1, "per_page": 20, "total": 340 },
  "errors": []
}
```

### Codes HTTP utilisés
| Code | Usage |
|---|---|
| `200` | Succès lecture/update |
| `201` | Ressource créée |
| `202` | Paiement accepté (asynchrone) |
| `400` | Validation invalide |
| `401` | Token absent/expiré |
| `403` | Rôle non autorisé |
| `404` | Ressource inexistante |
| `409` | Conflit (ex : sync doublon, idempotency) |
| `422` | Erreur métier (poids > seuil, solde insuffisant) |
| `429` | Rate limit dépassé |

### Pagination & filtres (query params standards)
```
GET /producers?page=1&per_page=20&search=koffi&zone=daloa&status=active&sort=-created_at
```

---

## 1. Authentification & Utilisateurs

### Auth (OTP par SMS — pas d'email en zone rurale)

| Méthode | Endpoint | Description | Rôle |
|---|---|---|---|
| POST | `/auth/request-otp` | Envoie un code SMS au téléphone | Public |
| POST | `/auth/verify-otp` | Vérifie le code → retourne JWT + refresh token | Public |
| POST | `/auth/refresh` | Renouvelle l'access token | Auth |
| POST | `/auth/logout` | Révoque le refresh token | Auth |
| POST | `/auth/change-password` | Change le mot de passe (admin web) | Auth |

```json
// POST /auth/request-otp
{ "phone": "+2250712345678" }

// POST /auth/verify-otp
{ "phone": "+2250712345678", "otp": "482910", "device_id": "uuid-appareil" }

// Réponse 200
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "dGhpcyBpcyB...",
    "expires_in": 86400,
    "user": {
      "id": "usr_abc123",
      "name": "Konan Yao",
      "role": "collector",
      "cooperative_id": "coop_xyz789"
    }
  }
}
```

### Utilisateurs (admins, collecteurs)

| Méthode | Endpoint | Description | Rôle |
|---|---|---|---|
| GET | `/users` | Liste les utilisateurs de la coopérative | Admin |
| POST | `/users` | Crée un utilisateur (collecteur/admin) | Admin |
| GET | `/users/:id` | Détail utilisateur | Admin |
| PATCH | `/users/:id` | Modifie (nom, rôle, statut actif) | Admin |
| DELETE | `/users/:id` | Désactive (soft delete) | Admin |
| GET | `/users/me` | Profil connecté + permissions | Auth |

---

## 2. Coopérative & Paramètres

| Méthode | Endpoint | Description | Rôle |
|---|---|---|---|
| GET | `/cooperative` | Infos de ma coopérative | Auth |
| PATCH | `/cooperative` | Modifie (logo, RCCM, TVA, coordonnées) | Super admin |
| GET | `/settings/purchase-prices` | Grille de prix d'achat | Auth |
| POST | `/settings/purchase-prices` | Ajoute un prix (produit + qualité) | Admin |
| PATCH | `/settings/purchase-prices/:id` | Modifie un prix | Admin |
| GET | `/settings/alerts` | Seuils d'alerte (humidité max, poids max) | Auth |
| PUT | `/settings/alerts` | Met à jour les seuils | Admin |
| GET | `/zones` | Zones de collecte | Auth |
| POST | `/zones` | Crée une zone | Admin |

```json
// POST /settings/purchase-prices
{
  "product": "cacao",
  "quality": "A",
  "price_per_kg": 800,
  "currency": "XOF",
  "effective_from": "2026-10-01",
  "effective_to": null
}
```

> **Note métier :** les prix sont versionnés dans le temps (`effective_from/to`) car les cours du cacao changent chaque campagne. Une collecte garde le prix appliqué au moment de la saisie.

---

## 3. Producteurs (Adhérents)

| Méthode | Endpoint | Description | Rôle |
|---|---|---|---|
| GET | `/producers` | Liste paginée + filtres (zone, statut, search) | Auth |
| POST | `/producers` | Crée un producteur | Admin, Collecteur |
| GET | `/producers/:id` | Fiche complète | Auth |
| PATCH | `/producers/:id` | Modifie identité/statut | Admin |
| DELETE | `/producers/:id` | Désactive (soft delete) | Admin |
| POST | `/producers/import` | Import CSV/Excel en masse | Admin |
| GET | `/producers/:id/qr-code` | Génère/récupère QR code PNG | Auth |
| GET | `/producers/by-phone/:phone` | Recherche rapide par téléphone | Auth |
| GET | `/producers/:id/balance` | Solde dû + total campagne | Auth |

```json
// POST /producers
{
  "first_name": "Amadou",
  "last_name": "Koffi",
  "phone": "+2250712345678",
  "cin_number": "CIN12345678",
  "gender": "M",
  "birth_year": 1975,
  "zone_id": "zone_daloa_1",
  "membership_date": "2024-03-15",
  "mobile_money": {
    "operator": "orange_money",
    "account": "+2250712345678"
  },
  "parcels": [
    {
      "latitude": 7.23456,
      "longitude": -5.67890,
      "area_hectares": 2.5,
      "crop": "cacao",
      "planted_year": 2010
    }
  ]
}

// GET /producers/:id/balance → 200
{
  "success": true,
  "data": {
    "producer_id": "prod_abc123",
    "campaign": "2026-2027",
    "total_delivered_kg": 2400,
    "total_earned": 1920000,
    "total_paid": 1500000,
    "balance_due": 420000,
    "last_delivery": "2026-09-28"
  }
}
```

### Parcelles (sous-ressource, critique pour EUDR)

| Méthode | Endpoint | Description | Rôle |
|---|---|---|---|
| GET | `/producers/:id/parcels` | Liste les parcelles | Auth |
| POST | `/producers/:id/parcels` | Ajoute une parcelle (GPS polygon ou point) | Admin, Collecteur |
| PATCH | `/parcels/:id` | Modifie superficie/culture | Admin |
| DELETE | `/parcels/:id` | Supprime une parcelle | Admin |

---

## 4. Collectes ⭐ (module cœur)

| Méthode | Endpoint | Description | Rôle |
|---|---|---|---|
| GET | `/collections` | Liste + filtres (date, collecteur, qualité, zone, statut) | Auth |
| POST | `/collections` | Crée une collecte | Collecteur, Admin |
| GET | `/collections/:id` | Détail complet | Auth |
| PATCH | `/collections/:id` | Modifie (avant validation) | Admin |
| POST | `/collections/:id/validate` | Valide une collecte en attente | Admin |
| POST | `/collections/:id/reject` | Rejette avec motif | Admin |
| DELETE | `/collections/:id` | Annule (soft delete, journalisé) | Admin |
| GET | `/collections/stats/daily` | Agrégats du jour (nb, poids, montant) | Auth |
| GET | `/collections/export` | Export CSV/PDF filtré | Admin |

```json
// POST /collections   (avec header X-Idempotency-Key obligatoire)
{
  "client_uuid": "clt_550e8400-e29b-41d4-a716-446655440000",
  "producer_id": "prod_abc123",
  "collected_at": "2026-10-01T08:30:00Z",
  "weight_kg": 120,
  "quality": "A",
  "moisture_percent": 6.5,
  "product": "cacao",
  "notes": "Séchage correct",
  "photos": ["img_uuid_1"],
  "producer_signature": "base64_png_signature_optional",
  "gps": { "lat": 7.2345, "lng": -5.6789 }
}

// Réponse 201 — le montant est calculé côté serveur, JAMAIS client
{
  "success": true,
  "data": {
    "id": "col_1042",
    "reference": "COL-2026-10-01-1042",
    "producer_id": "prod_abc123",
    "collector_id": "usr_collector1",
    "weight_kg": 120,
    "quality": "A",
    "unit_price": 800,
    "amount": 96000,
    "currency": "XOF",
    "status": "pending_validation",
    "sync_source": "offline_mobile",
    "created_at": "2026-10-01T10:15:22Z"
  }
}
```

**Statuts d'une collecte :** `pending_validation` → `validated` → `paid` (ou `rejected`)

**Règles métier API :**
- `amount = weight_kg × unit_price` calculé **serveur uniquement**
- Rejet si `moisture_percent > seuil` configuré (erreur `422`)
- Doublon détecté via `client_uuid` → réponse `409` avec la collecte existante (indispensable pour la sync offline)

### Photos (upload séparé, mode hors-ligne)

| Méthode | Endpoint | Description | Rôle |
|---|---|---|---|
| POST | `/uploads/photo` | Upload multipart (`multipart/form-data`) | Collecteur |
| GET | `/uploads/:id` | Récupère l'image (signed URL) | Auth |

---

## 5. Synchronisation Offline-First ⭐

Le module qui rend le produit utilisable en brousse.

| Méthode | Endpoint | Description | Rôle |
|---|---|---|---|
| POST | `/sync/push` | Envoie le lot de collectes créées hors-ligne | Collecteur |
| GET | `/sync/pull?since=<timestamp>` | Récupère les données modifiées depuis `<timestamp>` (prix, producteurs, statuts) | App mobile |
| GET | `/sync/status/:device_id` | État de synchro d'un appareil | Admin |

```json
// POST /sync/push — batch atomique
{
  "device_id": "uuid-appareil",
  "last_sync_at": "2026-09-30T18:00:00Z",
  "collections": [
    { "client_uuid": "clt_001", "...": "..." },
    { "client_uuid": "clt_002", "...": "..." }
  ]
}

// Réponse 200 — rapport détaillé par item
{
  "success": true,
  "data": {
    "accepted": ["clt_001"],
    "rejected": [
      {
        "client_uuid": "clt_002",
        "reason": "duplicate",
        "existing_collection_id": "col_1040"
      }
    ],
    "server_time": "2026-10-01T10:15:22Z"
  }
}
```

**Règles sync :**
- Le serveur renvoie toujours son `server_time` → l'app corrige son horloge local (dérapages d'horloge fréquents sur téléphones bas de gamme)
- `pull` utilise un timestamp incrémental → ne transfère que le différentiel (économie data)
- Jamais d'écrasement silencieux : en cas de conflit, le serveur tranche et logge l'événement

---

## 6. Paiements (Mobile Money via CinetPay/Julaya)

| Méthode | Endpoint | Description | Rôle |
|---|---|---|---|
| GET | `/payments` | Liste + filtres (statut, période, producteur) | Admin |
| POST | `/payments/batch` | Paiement groupé de plusieurs collectes validées | Admin |
| POST | `/payments/:id/retry` | Relance un paiement échoué | Admin |
| GET | `/payments/:id` | Statut détaillé d'un paiement | Auth |
| GET | `/payments/:id/receipt` | Reçu PDF | Auth |
| POST | `/payments/webhook/cinetpay` | Callback opérateur (signature vérifiée) | Interne |
| GET | `/payments/summary` | Totaux période (payé/en attente/échoué) | Admin |

```json
// POST /payments/batch
{
  "collection_ids": ["col_1042", "col_1041", "col_1040"],
  "method": "mobile_money",
  "reference_note": "Campagne octobre S1"
}

// Réponse 202 — traitement asynchrone
{
  "success": true,
  "data": {
    "batch_id": "pay_batch_55",
    "total_amount": 327750,
    "count": 3,
    "status": "processing",
    "items": [
      { "payment_id": "pay_501", "producer_id": "prod_abc123", "amount": 96000, "operator": "orange_money", "status": "initiated" }
    ]
  }
}

// POST /payments/webhook/cinetpay — callback sécurisé
{
  "payment_id": "ext_cinetpay_98765",
  "status": "success",
  "amount": 96000,
  "trans_id": "OM2