/*
 * Everything the app says, in French.
 *
 * The same keys as `en.js`, in the same order, so the two read side by side —
 * `catalogues.test.js` fails if either grows a key the other has not. Comments
 * are not repeated here: the English catalogue is where a string's reasoning
 * lives, and a translated copy of it would be one more thing to keep in step.
 *
 * Apostrophes are typographic (’) throughout. French is full of them, and the
 * curly one both reads correctly and keeps every string in single quotes.
 */
export const fr = {
  /* ---- The app, and its chrome ------------------------------------------ */

  /* A product name, not a phrase. It is in the catalogue so that the day it
     becomes translatable there is a place to translate it. */
  'app.name': 'Campaign Manager',

  'shell.openNav': 'Ouvrir la navigation',
  'shell.campaignNav': 'Campagne',

  'chrome.switchTheme': 'Changer de thème',
  'chrome.campaignSettings': 'Paramètres de la campagne',
  'chrome.closeCampaign': 'Fermer la campagne',
  'chrome.signOut': 'Se déconnecter',

  'nav.resources': 'Ressources',
  'nav.pcs': 'PJ',
  'nav.npcs': 'PNJ',
  'nav.locations': 'Lieux',
  'nav.factions': 'Factions',
  'nav.organization': 'Organisation',
  'nav.sessions': 'Sessions',
  'nav.agenda': 'Agenda',

  /* ---- Document titles -------------------------------------------------- */

  'route.home': 'Vos campagnes',
  'route.sessions': 'Notes de session',
  'route.structure': 'Structure',
  'route.act': 'Acte',
  'route.sequence': 'Séquence',
  'route.scene': 'Scène',
  'route.campaignSettings': 'Paramètres de la campagne',
  'route.login': 'Connexion',
  'route.signup': 'Créer un compte',
  'route.forgotPassword': 'Réinitialiser votre mot de passe',
  'route.resetPassword': 'Choisir un nouveau mot de passe',
  'route.verifyEmail': 'Confirmer votre adresse',
  'route.ssoCallback': 'Connexion en cours',
  'route.styleguide': 'Guide de style',
  'route.notFound': 'Introuvable',

  /* ---- Signing in ------------------------------------------------------- */

  'login.title': 'Connexion',
  'login.username': 'Nom d’utilisateur',
  'login.password': 'Mot de passe',
  'login.submit': 'Se connecter',
  'login.signedOut.retry': 'La connexion sera de nouveau possible dans {wait}.',
  'login.wait.seconds': '{count} secondes',
  'login.wait.minute': 'une minute',
  'login.wait.minutes': '{count} minutes',
  'login.error.credentials':
    'Ce nom d’utilisateur et ce mot de passe ne correspondent à aucun compte.',
  'login.error.generic': 'Un problème est survenu lors de la connexion. Réessayez.',
  'login.or': 'ou',
  'login.discord': 'Continuer avec Discord',
  'login.google': 'Continuer avec Google',
  'login.noAccount': 'Pas encore de compte ?',
  'login.createOne': 'Créez-en un',
  'login.forgotPassword': 'Mot de passe oublié ?',

  /* ---- Creating an account ---------------------------------------------- */

  'signup.title': 'Créer un compte',
  'signup.username': 'Nom d’utilisateur',
  'signup.email': 'E-mail',
  'signup.password': 'Mot de passe',
  'signup.submit': 'Créer le compte',
  'signup.error.notAccepted': 'Cela n’a pas été accepté. Essayez autre chose.',
  'signup.error.email':
    'Cela ne ressemble pas à une adresse e-mail utilisable. Essayez-en une autre.',
  'signup.error.usernameTaken': 'Ce nom d’utilisateur est déjà pris. Essayez-en un autre.',
  'signup.error.something': 'Quelque chose là-dedans n’a pas été accepté.',
  'signup.error.generic': 'Un problème est survenu lors de la création du compte. Réessayez.',
  'signup.haveOne': 'Vous en avez déjà un ?',
  'signup.signIn': 'Connectez-vous',

  /* ---- Asking for a reset link ------------------------------------------ */

  'forgot.title': 'Réinitialiser votre mot de passe',
  'forgot.sent':
    'Si cela correspond à un compte, un message est en route. Le lien ne fonctionne qu’une fois et expire dans une heure.',
  'forgot.backToSignIn': 'Retour à la connexion',
  'forgot.identifier': 'Adresse e-mail ou nom d’utilisateur',
  'forgot.submit': 'Envoyer un lien de réinitialisation',
  'forgot.remembered': 'Ça vous revient ?',
  'forgot.signIn': 'Connectez-vous',
  'forgot.error.generic': 'Un problème est survenu. Réessayez dans un instant.',

  /* ---- Choosing a new password ------------------------------------------ */

  'reset.title': 'Choisir un nouveau mot de passe',
  'reset.done': 'Votre mot de passe a été changé, et toutes les sessions ont été déconnectées.',
  'reset.signIn': 'Se connecter',
  'reset.missingToken': 'Il manque son jeton à ce lien. Demandez-en un nouveau et réessayez.',
  'reset.requestLink': 'Demander un lien de réinitialisation',
  'reset.password': 'Nouveau mot de passe',
  'reset.submit': 'Changer mon mot de passe',
  'reset.askNewLink': 'Demander un nouveau lien',
  'reset.error.invalidLink':
    'Ce lien n’est plus valide. Il a peut-être expiré, ou déjà été utilisé — demandez-en un nouveau.',
  'reset.error.generic': 'Un problème est survenu. Réessayez dans un instant.',

  /* ---- Confirming an address -------------------------------------------- */

  'verify.working': 'Confirmation de votre adresse…',
  'verify.done.title': 'Adresse confirmée',
  'verify.done.detail': 'Merci — cette adresse est désormais vérifiée.',
  'verify.done.continue': 'Continuer',
  'verify.unusable.title': 'Ce lien n’est plus valide',
  'verify.unusable.detail':
    'Il a peut-être expiré, ou déjà été utilisé. Connectez-vous et demandez-en un nouveau depuis votre compte.',
  'verify.failed.title': 'Un problème est survenu',
  'verify.failed.detail':
    'Nous n’avons pas pu confirmer l’adresse pour le moment. Le lien reste valable — réessayez dans un instant.',
  'verify.signIn': 'Se connecter',

  /* ---- Coming back from a provider -------------------------------------- */

  'sso.working': 'Finalisation de votre connexion…',
  'sso.backToSignIn': 'Retour à la connexion',
  'sso.provider': 'le fournisseur',
  'sso.cancelled.title': 'Connexion annulée',
  'sso.cancelled.detail':
    'Vous n’avez pas autorisé l’application sur {provider}, rien n’a donc changé ici.',
  'sso.provider-unavailable.title': '{provider} n’a pas répondu',
  'sso.provider-unavailable.detail':
    'Nous n’avons pas pu joindre {provider} pour le moment. Votre compte n’a rien d’anormal — réessayez dans un instant.',
  'sso.no-email.title': 'Votre compte {provider} n’a pas d’adresse e-mail',
  'sso.no-email.detail':
    'Un compte ici en a besoin, pour les réinitialisations de mot de passe et les confirmations. Ajoutez une adresse à {provider} et réessayez, ou connectez-vous plutôt avec un mot de passe.',
  'sso.unverified-email.title': '{provider} n’a pas confirmé votre adresse',
  'sso.unverified-email.detail':
    'Nous n’acceptons qu’une adresse que le fournisseur a confirmée, afin que personne ne puisse atteindre un compte en saisissant l’adresse de quelqu’un d’autre dans un profil. Confirmez-la auprès de {provider}, puis revenez.',
  'sso.email-in-use.title': 'Cette adresse appartient déjà à un compte ici',
  'sso.email-in-use.detail':
    'Ce compte n’a pas encore confirmé l’adresse, nous ne pouvons donc pas la lier à {provider} en toute sécurité. Connectez-vous avec votre mot de passe, confirmez votre adresse, et {provider} s’y liera ensuite.',
  'sso.no-session.title': 'La connexion n’a pas tenu',
  'sso.no-session.detail':
    '{provider} vous a connecté, mais la session n’est pas parvenue jusqu’à cet onglet. Essayez de vous reconnecter.',
  'sso.failed.title': 'Un problème est survenu',
  'sso.failed.detail':
    'Nous n’avons pas pu terminer votre connexion avec {provider}. Réessayez dans un instant.',

  /* ---- Choosing a campaign ---------------------------------------------- */

  'home.unreachable.title': 'Nous n’avons pas pu joindre vos campagnes',
  'home.unreachable.detail':
    'L’application est connectée : cela vient de la connexion, pas de votre compte.',
  'home.retry': 'Réessayer',
  'home.welcome': 'Bienvenue, {username}',
  'home.oneThing': 'Une chose à faire pour commencer.',
  'home.empty.title': 'Lancez votre première campagne',
  'home.empty.detail':
    'Une campagne rassemble vos notes de session, vos factions, vos lieux et les personnes autour de votre table. Tout le reste ici en dépend.',
  'home.empty.action': 'Créer une campagne',
  'home.title': 'Quelle table menez-vous ?',
  'home.lede': 'Tout le reste vit à l’intérieur d’une campagne.',
  'home.waiting': 'Chargement de vos campagnes…',
  'home.newCampaign': 'Nouvelle campagne',
  'home.sources.title': 'Vos sources',
  'home.sources.note':
    'Les sources vous appartiennent, elles ne sont pas liées à une campagne — toutes celles que vous menez peuvent les voir.',
  'home.create.header': 'Nouvelle campagne',
  'home.create.submit': 'Créer la campagne',

  /* ---- A campaign's settings -------------------------------------------- */

  'settings.waiting': 'Chargement de cette campagne…',
  'settings.unreachable.title': 'Nous n’avons pas pu joindre cette campagne',
  'settings.unreachable.detail':
    'L’application est connectée : cela vient de la connexion, pas de votre compte.',
  'settings.retry': 'Réessayer',
  'settings.missing.title': 'Cette campagne n’est pas ici',
  'settings.missing.detail':
    'Elle a été supprimée, ou elle appartient à quelqu’un d’autre. Dans les deux cas, il n’y a rien à modifier.',
  'settings.backHome': 'Retour à vos campagnes',
  'settings.title': 'Paramètres de la campagne',
  'settings.lede': 'Renommer une campagne ne change rien à ce qu’elle contient.',
  'settings.submit': 'Enregistrer les modifications',
  'settings.saved': 'Enregistré',
  'settings.delete.title': 'Supprimer cette campagne',
  'settings.delete.warning':
    'Tout ce qui se trouve à cette table part avec elle, y compris chaque feuille de personnage. Il n’y a pas de retour en arrière.',
  'settings.delete.confirmBefore': 'Saisissez',
  'settings.delete.confirmAfter': 'pour confirmer',
  'settings.delete.submit': 'Supprimer la campagne',
  'settings.delete.error.gone': 'Cette campagne a déjà disparu.',
  'settings.delete.error.generic':
    'Un problème est survenu lors de la suppression de la campagne. Réessayez.',

  /* ---- The campaign's fields, for creating and editing alike ------------ */

  'campaignForm.name': 'Nom',
  'campaignForm.description': 'Description',
  'campaignForm.optional': '(facultatif)',
  'campaignForm.hint':
    'Une phrase pour présenter la table aux personnes que vous y invitez. Elle peut changer à tout moment.',
  'campaignForm.error.missingName': 'Donnez un nom à la campagne.',
  'campaignForm.error.name': 'Ce nom n’a pas été accepté. Essayez-en un autre.',
  'campaignForm.error.description':
    'Cette description n’a pas été acceptée. Essayez-en une plus courte.',
  'campaignForm.error.something': 'Quelque chose là-dedans n’a pas été accepté.',
  'campaignForm.error.gone': 'Cette campagne n’est plus là.',
  'campaignForm.error.generic':
    'Un problème est survenu lors de l’enregistrement de la campagne. Réessayez.',

  /* ---- The pages that stand in for a page ------------------------------- */

  'notFound.title': 'Cette page n’est pas dans ce volume',
  'notFound.detail':
    'Le lien est peut-être mal saisi, ou il pointe vers quelque chose qui n’a pas encore été écrit. Rien n’a été perdu.',
  'notFound.back': 'Retour aux notes de session',

  'unreachable.title': 'Serveur injoignable',
  'unreachable.detail':
    'Cela vient de chez nous, pas de chez vous — vous n’avez pas été déconnecté. Cela veut généralement dire que l’application est en cours de mise à jour, et cela passe en un instant.',
  'unreachable.retry': 'Réessayer',

  'verification.text':
    'Votre adresse e-mail n’est pas encore confirmée. La confirmer garde votre compte à vous.',
  'verification.resend': 'Renvoyer le lien',
  'verification.dismiss': 'Fermer',
  'verification.sent': 'Envoyé. Regardez votre boîte de réception.',
  'verification.failed': 'Impossible de l’envoyer pour le moment. Réessayez dans un instant.',

  'write.failed': 'Cette modification n’a pas pu être enregistrée.',

  /* ---- The three kinds -------------------------------------------------- */

  'kind.act': 'Acte',
  'kind.sequence': 'Séquence',
  'kind.scene': 'Scène',
  'kind.untitled.act': 'Acte sans titre',
  'kind.untitled.sequence': 'Séquence sans titre',
  'kind.untitled.scene': 'Scène sans titre',
  'kind.explains.act': 'Une division majeure de la campagne.',
  'kind.explains.sequence': 'Une suite de scènes qui raconte une petite histoire à elle seule.',
  'kind.explains.scene': 'Une unité de jeu : un lieu, une distribution.',

  /* ---- The outline ------------------------------------------------------ */

  'structure.heading': 'Structure',
  'structure.theCampaign': 'la campagne',
  'structure.expandAll': 'Tout déplier',
  'structure.collapseAll': 'Tout replier',
  'structure.loading': 'Chargement',
  'structure.error': 'La structure n’a pas pu être chargée.',
  'structure.retry': 'Réessayer',
  'structure.empty.before': 'Rien ici pour l’instant. Un',
  'structure.empty.word': 'acte',
  'structure.empty.after':
    'est une division majeure de la campagne — ou écrivez une scène directement sur la campagne et donnez-lui une forme plus tard.',
  'structure.emptyAct.before': 'Rien dans cet acte pour l’instant. Une',
  'structure.emptyAct.word': 'séquence',
  'structure.emptyAct.after':
    'est une suite de scènes qui raconte une petite histoire à elle seule à l’intérieur de celui-ci — ou écrivez une scène directement sur l’acte.',

  'outline.expand': 'Déplier {name}',
  'outline.collapse': 'Replier {name}',
  'outline.skipsLevel': 'Rattachée à l’acte, en sautant le niveau de la séquence',
  'outline.nameThis.act': 'Nommez cet acte',
  'outline.nameThis.sequence': 'Nommez cette séquence',
  'outline.nameThis.scene': 'Nommez cette scène',

  'add.toParent': 'Ajouter dans {parent}',

  'move.menuLabel': 'Déplacer {name}',
  'move.up': 'Monter',
  'move.down': 'Descendre',
  'move.into': 'Déplacer dans…',
  'move.delete': 'Supprimer',
  'move.dialog.title': 'Déplacer {name}',
  'move.dialog.explain':
    'Cela ira à la fin de ce que vous choisirez. La campagne est un endroit à part entière — une scène n’a pas besoin d’un acte auquel appartenir.',
  'move.dialog.placeholder': 'Choisissez où cela va',
  'move.cancel': 'Annuler',
  'move.confirm': 'Déplacer',
  'move.parent.campaign': 'La campagne',
  'move.delete.title': 'Supprimer {name} ?',
  'move.delete.confirm': 'Supprimer',
  'move.consequence.act':
    'Ses séquences et ses scènes passent à la campagne. Rien de ce qu’il contient n’est supprimé.',
  'move.consequence.sequence':
    'Ses scènes passent à l’acte au-dessus d’elle. Rien de ce qu’elle contient n’est supprimé.',
  'move.consequence.scene': 'La scène et tout ce qui y est écrit disparaissent.',

  'campaignNav.looseScene': 'Dans aucun acte',

  /* ---- A node's own page ------------------------------------------------ */

  'trail.label': 'Fil d’Ariane',
  'trail.structure': 'Structure',

  'stepper.label': 'Les scènes de part et d’autre de celle-ci',
  'stepper.previous': 'Scène précédente',
  'stepper.next': 'Scène suivante',

  'node.contents.sequence': 'séquence',
  'node.edit': 'Modifier',
  'node.save': 'Enregistrer',
  'node.cancel': 'Annuler',
  'node.title': 'Titre',
  'node.description': 'Description',
  'node.contains': 'Contient',
  'node.missing': 'Ce n’est pas ici.',
  'node.needsTitle': 'Donnez-lui un titre.',
  'node.teach.before': 'Une',
  'node.teach.word': 'séquence',
  'node.teach.after':
    'est une suite de scènes qui raconte une petite histoire à elle seule à l’intérieur d’un acte — un début et une fin, à une échelle plus petite que l’acte qui l’entoure.',
  'node.empty': 'Rien dedans pour l’instant.',
  'node.empty.act.before': 'Ajoutez une',
  'node.empty.act.word': 'séquence',
  'node.empty.act.after':
    '— une suite de scènes qui raconte une petite histoire à elle seule — ou écrivez une scène directement sur cet acte.',
  'node.empty.sequence': 'Écrivez-y une scène.',

  'scene.body': 'Contenu',
  'scene.unwritten':
    'Rien n’est encore écrit. C’est l’état normal de la plus grande partie d’une campagne.',
  'scene.status.planned': 'prévue',
  'scene.status.done': 'jouée',
  'scene.status.skipped': 'ignorée',
  'scene.status.option.planned': 'Prévue',
  'scene.status.option.done': 'Jouée',
  'scene.status.option.skipped': 'Ignorée',
  'scene.status.hint': '{status} — marquer comme {next}',

  'progress.empty': 'vide',
  'progress.notStarted': 'pas commencé',
  'progress.finished': 'terminé',
  'progress.ongoing': 'en cours',
  'progress.spelled': '{label} — {played} scènes jouées sur {total}',
  'progress.none': 'vide — rien n’y est encore écrit',

  /* ---- Writing prose ------------------------------------------------------ */

  'markdown.hint': 'Ce champ accepte le markdown de Campaign Manager.',
  'markdown.toolbar': 'Insérer du markdown',
  'markdown.insert': 'Insérer {name}',
  'markdown.entity': 'Entité',
  'markdown.commonmark.bold': 'Gras',
  'markdown.commonmark.italic': 'Italique',
  'markdown.commonmark.heading': 'Titre',
  'markdown.commonmark.bullet': 'Liste',
  'markdown.commonmark.ordered': 'Numérotée',
  'markdown.commonmark.quote': 'Citation',
  'markdown.commonmark.code': 'Code',
  'markdown.commonmark.codeBlock': 'Bloc de code',
  'markdown.commonmark.rule': 'Filet',
  'markdown.commonmark.link': 'Lien',
  'markdown.directive.dice': 'Dés',
  'markdown.directive.ref': 'Source',
  'markdown.directive.readAloud': 'À voix haute',
  'markdown.directive.color': 'Couleur',

  /* Les teintes portent des noms de table, pas de longueurs d'onde — « wyrd »
     reste « wyrd », comme en anglais : c'est un nom propre, pas un adjectif. */
  'prose.hue.blood': 'Sang',
  'prose.hue.torch': 'Torche',
  'prose.hue.moss': 'Mousse',
  'prose.hue.scrying': 'Scrutation',
  'prose.hue.verdigris': 'Vert-de-gris',
  'prose.hue.wyrd': 'Wyrd',
  'prose.hue.slate': 'Ardoise',
  /* « Soutenu » plutôt que « gras » : la barre d'outils appelle déjà `**` du
     gras, et un niveau d'intensité n'est pas une graisse de caractère. */
  'prose.tier.bold': 'Soutenu',
  'prose.tier.medium': 'Moyen',
  'prose.tier.subtle': 'Discret',

  /* ---- What prose renders as -------------------------------------------- */

  'entity.npc': 'PNJ',
  'entity.location': 'Lieu',
  'entity.item': 'Objet',
  'entity.monster': 'Monstre',
  'entity.faction': 'Faction',
  'entity.session': 'Session',
  'readAloud.label': 'À lire à voix haute',
  'dice.crit': 'critique',
  'dice.fumble': 'échec critique',
  'statblock.actions': 'Actions',
}
