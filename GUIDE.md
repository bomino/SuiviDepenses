# Guide d'utilisation — Suivi des Dépenses

Bienvenue dans **Suivi des Dépenses**, l'application bilingue (français/anglais) pour suivre les dépenses de chantier en temps réel, partagées entre l'équipe.

Ce guide s'adresse aux **utilisateurs finaux** : administrateurs (chefs de chantier, responsables) et ouvriers (foremen, manœuvres). Pour la documentation technique de déploiement, voir `DEPLOY.md`.

---

## Sommaire

1. [Présentation rapide](#1-présentation-rapide)
2. [Premiers pas](#2-premiers-pas)
3. [Pour les ouvriers](#3-pour-les-ouvriers)
4. [Pour les administrateurs](#4-pour-les-administrateurs)
5. [Installer l'application sur votre téléphone](#5-installer-lapplication-sur-votre-téléphone)
6. [Trucs et astuces](#6-trucs-et-astuces)
7. [Dépannage](#7-dépannage)

---

## 1. Présentation rapide

**À quoi sert l'application ?**
Saisir, classer et suivre toutes les dépenses d'un ou plusieurs chantiers — matériaux, main-d'œuvre, transport, permis, etc. — depuis un téléphone, une tablette ou un ordinateur. Les chiffres se mettent à jour pour toute l'équipe en temps réel.

**Deux types d'utilisateurs :**

| Rôle | Ce qu'ils peuvent faire |
|---|---|
| **Admin** (chef de projet) | Voir **toutes** les dépenses de **tous les projets**. Créer/renommer/supprimer des projets. Ajouter/supprimer des utilisateurs. Affecter chaque utilisateur à un projet. Modifier ou supprimer n'importe quelle dépense. |
| **Ouvrier** (par défaut) | Voir uniquement les dépenses qu'il a saisies, **sur le projet auquel il est affecté**. Ajouter, modifier, supprimer ses propres dépenses. |

**Multi-projet** — une seule installation peut suivre plusieurs chantiers en parallèle (ex. « Villa Tower », « Rénovation 14e »). Les ouvriers ne voient que leur chantier ; l'admin voit tout.

---

## 2. Premiers pas

### 2.1 Se connecter

1. Ouvrez l'URL fournie par votre administrateur (ex. `https://votre-app.up.railway.app`).
2. L'écran de **Connexion** s'affiche.
3. Saisissez votre **nom d'utilisateur** et votre **mot de passe**.
4. Cliquez sur **Se connecter**.

> Si vous n'avez pas encore de compte, demandez à votre administrateur de vous en créer un (voir §4.2).

### 2.2 Aperçu de l'écran

Une fois connecté(e), vous voyez :

- **En-tête (haut)** :
  - Le titre **Suivi des Dépenses** et le nom du projet en cours.
  - Une pastille **En ligne** (vert) : la connexion au serveur fonctionne ; vos données sont partagées avec l'équipe.
  - Boutons : **FR/EN** (langue), **Exporter** (télécharger CSV), **Tout effacer**, et — pour les admins — **Gérer les utilisateurs** et **Déconnexion**.
  - Votre nom d'utilisateur (avec une pastille orange si vous êtes admin).

- **Tableau de bord** : 4 cartes de totaux — **Total**, **Payé**, **Impayé**, **Attente**.

- **Formulaire** « Ajouter une dépense ».

- **Liste des dépenses** avec barre de filtres et bouton **Réinitialiser**.

### 2.3 Changer la langue

Cliquez sur **FR** (en haut à droite) pour passer en français ou **EN** pour passer en anglais. Votre choix est mémorisé pour la prochaine ouverture.

> En français, les montants s'affichent en **FCFA**. En anglais, en **dollars ($)**.

---

## 3. Pour les ouvriers

### 3.1 Ajouter une dépense

1. Dans le formulaire **Ajouter une dépense** :
   - **Description** *(obligatoire)* — ex. « Sacs de ciment 50 kg ».
   - **Montant** *(obligatoire)* — chiffre positif. Ex. `25000`.
   - **Catégorie** — Matériaux, Main-d'œuvre, Équipement, Permis, Sous-traitants, Transport, Services, Divers.
   - **Date** — préremplie à aujourd'hui ; modifiable.
   - **Payé par** — nom de la personne qui a effectué le paiement (texte libre).
   - **État** — **Payé**, **Attente** (en attente de validation/paiement), ou **Impayé**.
   - **Remarques** — note libre, optionnelle.
2. Cliquez sur **Ajouter**.
3. La dépense apparaît immédiatement dans la liste, et les totaux du tableau de bord se mettent à jour.

### 3.2 Modifier une dépense

1. Dans la liste, cliquez sur l'icône **✎** (crayon) à côté de la dépense.
2. Le formulaire se remplit avec les valeurs existantes ; le titre devient **Modifier la dépense**.
3. Modifiez les champs souhaités.
4. Cliquez sur **Mettre à jour** (ou **Annuler** pour abandonner).

### 3.3 Supprimer une dépense

Cliquez sur l'icône **✕** (croix rouge) à côté de la dépense, puis confirmez.

> ⚠️ La suppression est irréversible. Pas de corbeille.

### 3.4 Filtrer la liste

Au-dessus de la liste, vous disposez de filtres :

- **Catégorie** — afficher uniquement une catégorie.
- **État** — afficher uniquement Payé / Attente / Impayé.
- **Date Du / Au** — restreindre à une période.
- **Recherche** — chercher dans la description, le payeur ou les remarques.
- **Réinitialiser** — efface tous les filtres en un clic.

Les totaux du tableau de bord couvrent **toutes** les dépenses, pas seulement celles filtrées. Le compteur à côté de « Toutes les dépenses » indique le nombre de lignes affichées après filtrage.

### 3.5 Exporter en CSV

Cliquez sur **Exporter** dans l'en-tête. Un fichier `.csv` est téléchargé, prêt à être ouvert dans Excel, LibreOffice Calc ou Google Sheets. Les en-têtes sont traduits selon la langue active.

### 3.6 Tout effacer

Le bouton **Tout effacer** supprime **toutes vos dépenses** sur le projet en cours. Une confirmation est demandée. Pour les admins, il efface tout le projet visible. **Action irréversible**.

### 3.7 « Aucun projet affecté »

Si vous voyez ce message à l'ouverture de l'application, cela signifie que votre administrateur ne vous a pas encore affecté(e) à un chantier. Contactez-le pour qu'il vous assigne un projet (voir §4.4). Tant que vous n'êtes pas affecté(e), vous ne pouvez pas saisir de dépense.

---

## 4. Pour les administrateurs

L'admin a accès à un bouton supplémentaire dans l'en-tête : **Gérer les utilisateurs**. Le panneau qui s'ouvre comporte deux sections : **Projets** et **Utilisateurs**.

### 4.1 Gérer les projets

**Ajouter un projet**
1. Cliquez sur **Gérer les utilisateurs**.
2. Dans la section **Projets**, saisissez le nom du chantier (ex. « Villa Mer 2026 ») et cliquez sur **Ajouter un projet**.

**Renommer un projet**
1. À côté du projet voulu, cliquez sur **Renommer**.
2. Saisissez le nouveau nom et validez.

**Supprimer un projet**
1. Cliquez sur **Supprimer** (rouge) à côté du projet.
2. Confirmez.

> ⚠️ Supprimer un projet **efface toutes ses dépenses** et **désaffecte les ouvriers qui y étaient**. Leurs comptes restent actifs, mais ils verront « Aucun projet affecté » jusqu'à ce qu'on les réaffecte.

### 4.2 Ajouter un utilisateur

Dans la section **Utilisateurs** :

1. Saisissez un **nom d'utilisateur** unique.
2. Saisissez un **mot de passe** (minimum 6 caractères).
3. Cochez **Faire de cet utilisateur un admin** si vous souhaitez lui donner les droits d'administration.
4. Cliquez sur **Ajouter**.

Le nouvel utilisateur apparaît dans la liste. Communiquez-lui ses identifiants ; il pourra changer son mot de passe **uniquement** via vous (réinitialisation, voir §4.5).

### 4.3 Promouvoir / rétrograder un utilisateur

À côté de chaque utilisateur, le bouton **Promouvoir admin** (ou **Rétrograder** si déjà admin) bascule son rôle. Vous **ne pouvez pas** retirer votre propre rôle d'admin (sécurité contre le verrouillage accidentel).

### 4.4 Affecter un utilisateur à un projet

Dans la liste des utilisateurs, chaque ligne comporte un menu déroulant des projets. Sélectionnez le projet souhaité ; l'affectation est enregistrée immédiatement.

Pour **désaffecter** quelqu'un, choisissez **— Aucun projet —**. La personne reste utilisateur mais ne peut plus saisir de dépense tant qu'elle n'a pas de projet.

### 4.5 Réinitialiser le mot de passe d'un utilisateur

À côté de l'utilisateur, cliquez sur **Réinitialiser**. Saisissez le nouveau mot de passe (minimum 6 caractères). L'ancien mot de passe est immédiatement invalidé.

> Communiquez le nouveau mot de passe à l'utilisateur de vive voix ou via un canal sécurisé (pas par e-mail si possible).

### 4.6 Supprimer un utilisateur

Cliquez sur **Supprimer** (rouge) à côté de l'utilisateur.

> ⚠️ Supprimer un utilisateur **efface toutes ses dépenses**. Vous ne pouvez pas vous supprimer vous-même.

### 4.7 Renommer le projet en cours (raccourci)

Dans l'en-tête, cliquez sur le nom du projet (à côté de l'icône crayon). Saisissez le nouveau nom. Cela renomme le projet auquel **vous-même** êtes affecté ; pour renommer un autre projet, passez par **Gérer les utilisateurs** → section **Projets** → **Renommer**.

---

## 5. Installer l'application sur votre téléphone

L'application est une **PWA** (Progressive Web App) : elle peut être installée comme une application native, fonctionne hors-ligne pour la consultation, et reçoit automatiquement les mises à jour.

### 5.1 Sur Android (Chrome / Edge)

1. Ouvrez l'URL de l'application dans Chrome.
2. Une bannière **« Installer pour un accès rapide »** apparaît au bas de l'écran après quelques secondes. Cliquez sur **Installer**.
3. *(Alternative)* Menu Chrome (⋮) → **Installer l'application** ou **Ajouter à l'écran d'accueil**.
4. L'icône orange « $ » apparaît sur votre écran d'accueil.

### 5.2 Sur iPhone / iPad (Safari)

1. Ouvrez l'URL dans **Safari** (pas Chrome — Safari uniquement sur iOS).
2. Touchez l'icône **Partager** (carré avec flèche vers le haut).
3. Faites défiler et touchez **Sur l'écran d'accueil**.
4. Confirmez **Ajouter**.

### 5.3 Sur ordinateur (Chrome, Edge)

1. Dans la barre d'adresse, cliquez sur l'icône **Installer** (à droite de l'URL, ressemble à un écran avec une flèche).
2. Confirmez **Installer**.

L'application s'ouvre dans sa propre fenêtre, sans la barre d'URL.

---

## 6. Trucs et astuces

### 6.1 Mises à jour

Quand votre administrateur déploie une nouvelle version, vous verrez la bannière **« Nouvelle version disponible »** lors de votre prochaine ouverture. Cliquez sur **Actualiser** pour basculer immédiatement, ou **Plus tard** pour terminer ce que vous étiez en train de faire (la nouvelle version sera appliquée à la prochaine ouverture).

### 6.2 Travailler hors-ligne

Si la connexion réseau est perdue (chantier sans Wi-Fi), la pastille bascule à **Hors ligne** et l'application stocke vos saisies localement dans le navigateur. **Attention** : dans ce cas, vos données ne sont **pas** synchronisées avec l'équipe tant que vous ne récupérez pas la connexion. Pour un chantier qui doit toujours être à jour, restez en ligne.

### 6.3 Catégories disponibles

| Catégorie | Pour quoi |
|---|---|
| **Matériaux** | Ciment, sable, gravier, fer à béton, briques, peinture, etc. |
| **Main-d'œuvre** | Salaires des ouvriers, journées de chantier |
| **Équipement** | Location/achat d'outils, échafaudages, bétonnière |
| **Permis** | Frais administratifs, autorisations municipales |
| **Sous-traitants** | Plombier, électricien, peintre payés à la tâche |
| **Transport** | Carburant, location de camion, livraisons |
| **Services** | Eau, électricité du chantier, internet temporaire |
| **Divers** | Tout ce qui ne rentre pas dans les autres catégories |

### 6.4 États de paiement

- **Payé** — la dépense a été réglée.
- **Attente** — engagée mais en attente de validation/paiement.
- **Impayé** — somme due, non encore réglée.

Le tableau de bord affiche le total pour chaque état, ce qui vous permet de voir d'un coup d'œil combien il vous reste à payer.

### 6.5 Sauvegarde / export régulier

Il est recommandé de cliquer sur **Exporter** au moins une fois par semaine pour conserver une copie locale du fichier CSV. C'est une assurance en cas de problème côté serveur.

---

## 7. Dépannage

| Problème | Cause probable | Solution |
|---|---|---|
| « Identifiants invalides » à la connexion | Faute de frappe, ou mot de passe modifié sans que vous soyez prévenu(e) | Demandez à votre admin de réinitialiser votre mot de passe (§4.5). |
| « Aucun projet affecté » bloque la saisie | L'admin ne vous a pas encore assigné à un chantier | Contactez l'admin (§4.4). |
| La pastille indique **Hors ligne** | Connexion Wi-Fi/4G perdue | Reconnectez-vous au réseau ; la pastille redevient **En ligne** automatiquement. |
| Les boutons sont trop petits sur mon téléphone | Ancienne version cachée par le navigateur | Forcez l'actualisation : sur mobile, fermez complètement l'application (pas juste minimiser) et rouvrez-la. Sur ordinateur : Ctrl+Maj+R (Windows) ou Cmd+Maj+R (Mac). |
| Mon CSV exporté affiche des caractères bizarres dans Excel | Encoding | À l'ouverture dans Excel, choisir **UTF-8** comme encodage. Le fichier inclut déjà un BOM ; LibreOffice Calc et Google Sheets le détectent automatiquement. |
| Je vois des dépenses qui ne sont pas les miennes (en tant qu'ouvrier) | Vous êtes admin sans le savoir, ou bug | Demandez à votre admin de vérifier votre rôle dans **Gérer les utilisateurs**. |
| L'application ne se charge pas du tout | Serveur indisponible ou problème réseau | Réessayez dans quelques minutes. Si ça persiste, prévenez votre administrateur (qui peut consulter le statut de déploiement Railway). |
| « Vous n'êtes pas affecté à un projet à renommer » (admin) | Vous êtes admin mais désaffecté | Réaffectez-vous via **Gérer les utilisateurs**, ou créez un projet et auto-affectez-vous. |

---

## En cas de problème non résolu

Contactez votre administrateur ou la personne qui vous a fourni l'accès. Si vous êtes vous-même administrateur, voir `DEPLOY.md` pour la documentation technique (Railway, base de données, journaux).

Bonne gestion de chantier ! 🏗️
