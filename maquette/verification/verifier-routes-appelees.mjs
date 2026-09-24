/* Vérifie, PAR ANALYSE STATIQUE (pas d'exécution), qu'aucun écran n'appelle
   une route qui n'existe plus côté serveur — le contrôle qui aurait détecté
   immédiatement la régression du chantier A (casse et retour client
   renvoyaient 404 depuis le renommage de route du sous-chantier 2, sans
   qu'aucune des 94 suites Playwright existantes ne le voie, puisqu'aucune
   d'elles ne cliquait sur ces deux boutons précis).

   Principe : un renommage de route (`server/app/routes/*.py`) doit casser
   CE contrôle, pas seulement une fonctionnalité en production. Deux listes
   construites PAR LECTURE DE FICHIERS, aucun serveur ni navigateur requis :

     1. Les routes RÉELLES : chaque `@<routeur>.<methode>("chemin")` dans
        server/app/routes/*.py, préfixé par le `prefix=` du routeur
        correspondant (déduit dynamiquement, pas codé en dur — un nouveau
        fichier de routes ou un préfixe changé n'exige aucune mise à jour
        ici).
     2. Les routes APPELÉES : chaque `appelApi(...)`, `telechargerFichier(...)`
        et `fetch(...)` dans maquette/*.html et maquette/api.js, plus les
        affectations `.src = "/..."` (image servie directement, ex. le
        logo). Les segments dynamiques (concaténation `+ variable +`) sont
        traités comme un joker ; la chaîne de requête (après `?`) est
        ignorée.

   Limite assumée (pas trop lourd pour ce cycle, comme demandé) : ceci est
   un contrôle STATIQUE, pas une navigation réelle — il ne prouve pas qu'un
   écran donné APPELLE effectivement une route à l'usage (ça, c'est le rôle
   de verifier-cablage.mjs et consorts), seulement qu'aucune route qu'il
   POURRAIT appeler n'est un 404 garanti. Il ne voit pas non plus une route
   appelée depuis une chaîne construite de façon trop dynamique pour être
   reconnue par les motifs ci-dessous (aucun cas de ce genre trouvé dans la
   maquette actuelle — voir le README de ce dossier pour le détail de
   l'audit qui a précédé ce script).
*/
import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve, join } from "node:path";

const ICI = dirname(fileURLToPath(import.meta.url));
const RACINE_DEPOT = resolve(ICI, "..", "..");
const DOSSIER_ROUTES = join(RACINE_DEPOT, "server", "app", "routes");
const DOSSIER_MAQUETTE = join(RACINE_DEPOT, "maquette");

const ok = [], ko = [];
const verifier = (cond, libelle) => (cond ? ok : ko).push(libelle);

// ---------------------------------------------------------------------------
// 1. Routes RÉELLES — lues dans server/app/routes/*.py.
// ---------------------------------------------------------------------------

function routesReelles() {
  const routes = []; // { methode, gabarit, fichier }
  for (const fichier of readdirSync(DOSSIER_ROUTES)) {
    if (!fichier.endsWith(".py") || fichier === "__init__.py") continue;
    const texte = readFileSync(join(DOSSIER_ROUTES, fichier), "utf8");

    // Chaque routeur défini dans le fichier, avec son préfixe (vide si
    // APIRouter() sans argument prefix — ex. demonstration.py).
    const prefixes = {};
    for (const m of texte.matchAll(/(\w+)\s*=\s*APIRouter\(([^)]*)\)/g)) {
      const nomVar = m[1];
      const args = m[2];
      const mp = /prefix\s*=\s*"([^"]*)"/.exec(args);
      prefixes[nomVar] = mp ? mp[1] : "";
    }
    if (Object.keys(prefixes).length === 0) continue;

    const nomsRouteurs = Object.keys(prefixes).join("|");
    const reDecorateur = new RegExp(
      `@(${nomsRouteurs})\\.(get|post|put|patch|delete)\\(\\s*\\n?\\s*"([^"]*)"`,
      "g"
    );
    for (const m of texte.matchAll(reDecorateur)) {
      const [, nomVar, methode, sousChemin] = m;
      const gabarit = (prefixes[nomVar] + sousChemin) || "/";
      routes.push({ methode: methode.toUpperCase(), gabarit, fichier });
    }
  }
  return routes;
}

function gabaritEnRegex(gabarit) {
  const echappe = gabarit
    .split("/")
    .map((segment) => (/^\{.*\}$/.test(segment) ? "[^/]+" : segment.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")))
    .join("/");
  return new RegExp("^" + echappe + "$");
}

// ---------------------------------------------------------------------------
// 2. Routes APPELÉES — lues dans maquette/*.html et maquette/api.js.
// ---------------------------------------------------------------------------

// Découpe le contenu d'une parenthèse ouvrante déjà repérée (renvoie le
// texte entre elle et sa fermante correspondante).
function extraireInterieurParentheses(texte, debutParenthese) {
  let profondeur = 1;
  let i = debutParenthese + 1;
  const debut = i;
  while (i < texte.length && profondeur > 0) {
    if (texte[i] === "(") profondeur++;
    else if (texte[i] === ")") profondeur--;
    if (profondeur === 0) break;
    i++;
  }
  return texte.slice(debut, i);
}

// Découpe une liste d'arguments en morceaux de PROFONDEUR 0 (respecte les
// parenthèses/accolades/crochets imbriqués) — nécessaire pour retrouver
// l'argument à un INDEX donné, pas seulement le premier.
function diviserArgsTopNiveau(expr) {
  const args = [];
  let profondeur = 0, debut = 0;
  for (let i = 0; i < expr.length; i++) {
    const c = expr[i];
    if (c === "{" || c === "(" || c === "[") profondeur++;
    else if (c === "}" || c === ")" || c === "]") profondeur--;
    else if (c === "," && profondeur === 0) { args.push(expr.slice(debut, i).trim()); debut = i + 1; }
  }
  const dernier = expr.slice(debut).trim();
  if (dernier) args.push(dernier);
  return args;
}

// Depuis UN argument (ex. `"/foo/" + x.id + "/bar"`), construit un gabarit
// avec `*` pour chaque partie dynamique, et coupe tout ce qui suit un `?`
// littéral (chaîne de requête, jamais significative pour l'existence de la
// route). `null` si l'argument n'est pas une chaîne littérale (ou une
// concaténation qui commence par une chaîne littérale) — ex. une variable
// brute passée telle quelle, non résolue par une analyse statique.
function expressionEnGabarit(argument) {
  if (!argument || (!argument.startsWith('"') && !argument.startsWith("'"))) return null;
  const morceaux = argument.split("+").map((m) => m.trim());
  let gabarit = "";
  for (const morceau of morceaux) {
    const chaine = /^["']([^"']*)["']$/.exec(morceau);
    if (chaine) {
      let valeur = chaine[1];
      const posPoint = valeur.indexOf("?");
      if (posPoint !== -1) { gabarit += valeur.slice(0, posPoint); break; }
      gabarit += valeur;
    } else {
      gabarit += "*";
    }
  }
  return gabarit || null;
}

function methodeDepuisOptions(expr) {
  const m = /method\s*:\s*["'](\w+)["']/.exec(expr || "");
  return m ? m[1].toUpperCase() : "GET";
}

// ---------------------------------------------------------------------------
// Fonctions d'enveloppe locales (ex. `appeler(chemin, methode, corps, ...)`
// dans stock.html, `appeler(chemin, corps, ...)` dans rh.html) : sans les
// suivre, un appel qui PASSE PAR une telle enveloppe est invisible pour ce
// script — trouvé en écrivant ce contrôle (les routes de stock.html/rh.html
// passées à l'enveloppe locale n'étaient sinon jamais reconnues). Détecte,
// par fichier, quel paramètre de l'enveloppe porte le CHEMIN et lequel (s'il
// existe) porte la MÉTHODE, en lisant le corps de la fonction elle-même.
function enveloppesLocales(texte) {
  const enveloppes = []; // { nom, indexChemin, methodeFixe?, indexMethode? }
  const reDef = /(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)\s*\{/g;
  let m;
  while ((m = reDef.exec(texte))) {
    const nom = m[1];
    const params = m[2].split(",").map((p) => p.trim()).filter(Boolean);
    // Corps de la fonction : depuis l'accolade ouvrante jusqu'à sa fermante.
    let profondeur = 1, i = m.index + m[0].length;
    const debutCorps = i;
    while (i < texte.length && profondeur > 0) {
      if (texte[i] === "{") profondeur++;
      else if (texte[i] === "}") profondeur--;
      if (profondeur === 0) break;
      i++;
    }
    const corps = texte.slice(debutCorps, i);

    const appelInterne = /\bappelApi\(\s*([^,)]+)/.exec(corps);
    if (!appelInterne) continue;
    const nomParamChemin = appelInterne[1].trim();
    const indexChemin = params.indexOf(nomParamChemin);
    if (indexChemin === -1) continue; // ne relaie pas un de ses propres paramètres

    const methodeFixe = /method\s*:\s*["'](\w+)["']/.exec(corps);
    const methodeVar = /method\s*:\s*(\w+)\b/.exec(corps);
    let indexMethode, fixe;
    if (methodeFixe) fixe = methodeFixe[1].toUpperCase();
    else if (methodeVar) {
      const idx = params.indexOf(methodeVar[1]);
      if (idx !== -1) indexMethode = idx;
    }

    enveloppes.push({ nom, indexChemin, methodeFixe: fixe, indexMethode });
  }
  return enveloppes;
}

function routesAppelees() {
  const appels = []; // { methode, gabarit, fichier }
  const fichiers = readdirSync(DOSSIER_MAQUETTE)
    .filter((f) => f.endsWith(".html"))
    .map((f) => join(DOSSIER_MAQUETTE, f));
  fichiers.push(join(DOSSIER_MAQUETTE, "api.js"));

  for (const chemin of fichiers) {
    const nomFichier = chemin.split(/[\\/]/).pop();
    const texte = readFileSync(chemin, "utf8");
    const enveloppes = enveloppesLocales(texte);
    const fonctionsASuivre = ["appelApi", "telechargerFichier", "fetch", ...enveloppes.map((e) => e.nom)];

    for (const fn of fonctionsASuivre) {
      const enveloppe = enveloppes.find((e) => e.nom === fn);
      const re = new RegExp(`\\b${fn}\\(`, "g");
      let m;
      while ((m = re.exec(texte))) {
        const debutParenthese = m.index + fn.length;
        const interieur = extraireInterieurParentheses(texte, debutParenthese);
        const args = diviserArgsTopNiveau(interieur);

        const indexChemin = enveloppe ? enveloppe.indexChemin : 0;
        const gabarit = expressionEnGabarit(args[indexChemin]);
        if (!gabarit) continue; // variable brute, non résolue statiquement

        let methode;
        if (fn === "telechargerFichier") methode = "GET";
        else if (enveloppe) {
          methode = enveloppe.methodeFixe
            || (enveloppe.indexMethode !== undefined
                  ? (/^["'](\w+)["']$/.exec(args[enveloppe.indexMethode])?.[1] || "GET").toUpperCase()
                  : "GET");
        } else {
          methode = methodeDepuisOptions(args[1]);
        }
        appels.push({ methode, gabarit, fichier: nomFichier });
      }
    }

    // Cas particulier : une image servie directement (`img.src = "/..."`),
    // jamais via appelApi — seul le logo (chantier C8) en dépend aujourd'hui,
    // mais le motif reste générique.
    for (const m of texte.matchAll(/\.src\s*=\s*["'](\/[^"'?]+)/g)) {
      appels.push({ methode: "GET", gabarit: m[1], fichier: nomFichier });
    }
  }
  return appels;
}

// ---------------------------------------------------------------------------
// 3. Comparaison.
// ---------------------------------------------------------------------------

const reel = routesReelles();
const reelRegex = reel.map((r) => ({ ...r, regex: gabaritEnRegex(r.gabarit) }));
const appeles = routesAppelees();

verifier(reel.length > 30, `au moins 30 routes réelles trouvées (obtenu ${reel.length}) — sinon l'extraction a probablement échoué`);
verifier(appeles.length > 20, `au moins 20 appels trouvés dans la maquette (obtenu ${appeles.length}) — sinon l'extraction a probablement échoué`);

// Un gabarit appelé (avec ses `*`) doit correspondre à AU MOINS une route
// réelle : on instancie un chemin concret (les `*` remplacés par "1") et on
// le teste contre chaque regex de route réelle, même méthode.
const dejaSignales = new Set();
for (const appel of appeles) {
  const concret = appel.gabarit.replace(/\*/g, "1");
  const correspond = reelRegex.some((r) => r.methode === appel.methode && r.regex.test(concret));
  const cle = `${appel.methode} ${appel.gabarit}`;
  if (dejaSignales.has(cle)) continue; // déjà vérifié depuis un autre écran
  dejaSignales.add(cle);
  verifier(correspond, `${appel.fichier} : ${appel.methode} ${appel.gabarit} correspond à une route réelle`);
}

// Recensement des routes réelles jamais appelées par aucun écran — un
// CONSTAT affiché à la fin, pas un échec (une route sans écran n'est pas
// forcément un bug : elle peut être volontairement hors périmètre, ou
// couverte par un usage hors maquette). Même logique de correspondance que
// le contrôle ci-dessus, dans l'autre sens : un appel couvre une route
// réelle si le chemin concret de l'appel matche le gabarit (regex) de
// cette route.
const appelesRegex = appeles.map((a) => ({ ...a, concret: a.gabarit.replace(/\*/g, "1") }));
const orphelines = reelRegex.filter((r) =>
  !appelesRegex.some((a) => a.methode === r.methode && r.regex.test(a.concret))
);

console.log(`\nRoutes réelles : ${reel.length}. Appels distincts trouvés dans la maquette : ${dejaSignales.size}.\n`);

if (ko.length > 0) {
  console.log(`ÉCHECS (${ko.length}) :`);
  ko.forEach((l) => console.log("  [ÉCHEC] " + l));
} else {
  console.log("Aucun échec : chaque route appelée par un écran existe réellement côté serveur.");
}

if (orphelines.length > 0) {
  console.log(`\nConstat (pas un échec) — ${orphelines.length} route(s) réelle(s) jamais appelée(s) par un écran :`);
  orphelines.forEach((r) => console.log(`  · ${r.methode} ${r.gabarit}  (${r.fichier})`));
}

console.log(`\nTotal : ${ok.length + ko.length} contrôles, ${ko.length} échec(s).`);
process.exit(ko.length > 0 ? 1 : 0);
