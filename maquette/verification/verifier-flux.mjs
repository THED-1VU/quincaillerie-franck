/* Vérifie, PAR EXÉCUTION, les parcours clés de la maquette :
   - connexion : messages d'erreur près du champ, couple valide -> écran de vente ;
   - vente : ajout au panier en 2 actions (taper + Entrée), fusion d'un article
     déjà présent, F4 change le mode de paiement, F9 = une seule confirmation,
     aucune fenêtre superposée ;
   - inventaire : aucune "quantité attendue" côté page, saisie + Entrée = article
     suivant.

   Prérequis : servir la maquette —  depuis ../  :  py -m http.server 8080
   Puis, depuis ce dossier :  npm install  &&  npm run flux
*/
import { chromium } from "playwright";
const BASE = process.env.MAQUETTE_URL || "http://127.0.0.1:8080/";
const b = await chromium.launch({ channel: "chrome" });
const ok = [], ko = [];
const check = (cond, label) => (cond ? ok : ko).push(label);

/* ---------- CONNEXION ---------- */
{
  const ctx = await b.newContext({ viewport: { width: 1366, height: 768 } });
  const p = await ctx.newPage();
  await p.goto(BASE + "connexion.html");

  await p.click("button[type=submit]");
  const err = await p.$("#zone-erreur");
  const txt0 = (await err.textContent()).trim();
  check((await err.isVisible()) && /identifiant.*mot de passe/i.test(txt0),
        `connexion: erreur affichée si tout vide ("${txt0}")`);

  await p.fill("#identifiant", "awa");
  await p.fill("#motdepasse", "faux");
  await p.click("button[type=submit]");
  const txt1 = (await p.textContent("#zone-erreur")).trim();
  check(/incorrect/i.test(txt1) && /bloque/i.test(txt1),
        'connexion: erreur "identifiant ou mot de passe incorrect" + mention blocage');

  await p.fill("#motdepasse", "franck");
  await Promise.all([p.waitForURL(/vente\.html/), p.click("button[type=submit]")]);
  check(p.url().endsWith("vente.html"), "connexion: awa/franck -> écran de vente");
  await ctx.close();
}

/* ---------- VENTE ---------- */
{
  const ctx = await b.newContext({ viewport: { width: 1366, height: 768 } });
  const p = await ctx.newPage();
  await p.goto(BASE + "vente.html");

  const nbLignes = async () => (await p.$$("#panier .panier__ligne")).length;
  const qteLigne1 = async () => p.inputValue("#panier .panier__ligne:nth-child(1) .panier__mini");

  const avant = await nbLignes();
  await p.click("#recherche");
  await p.type("#recherche", "robi");   // ACTION 1
  await p.keyboard.press("Enter");      // ACTION 2
  const apres = await nbLignes();
  check(apres === avant + 1, `vente: "robi" + Entrée ajoute 1 ligne (${avant} -> ${apres}) en 2 actions`);

  const q1 = parseInt(await qteLigne1(), 10);
  await p.type("#recherche", "ciment");
  await p.keyboard.press("Enter");
  const q2 = parseInt(await qteLigne1(), 10);
  check(q2 === q1 + 1 && (await nbLignes()) === apres,
        `vente: article déjà présent -> quantité +1 sans doublon (${q1} -> ${q2})`);

  const focusId = await p.evaluate(() => document.activeElement && document.activeElement.id);
  check(focusId === "recherche", "vente: le focus revient sur la recherche après ajout");

  const modeAvant = await p.inputValue("#paiement");
  await p.keyboard.press("F4");
  const modeApres = await p.inputValue("#paiement");
  check(modeAvant !== modeApres, `vente: F4 change le mode de paiement (${modeAvant} -> ${modeApres})`);

  await p.keyboard.press("F9");
  check(/confirmer l'encaissement/i.test(await p.textContent("#zone-confirmation")),
        "vente: 1er F9 demande UNE confirmation");
  await p.keyboard.press("F9");
  check(await (await p.$("#zone-succes")).isVisible(),
        "vente: 2e F9 valide (message de succès)");

  const modaux = await p.evaluate(() => document.querySelectorAll("dialog, [role=dialog], .modal").length);
  check(modaux === 0, "vente: aucune fenêtre superposée (0 dialog/modal)");
  await ctx.close();
}

/* ---------- INVENTAIRE (à l'aveugle) ---------- */
{
  const ctx = await b.newContext({ viewport: { width: 390, height: 780 } });
  const p = await ctx.newPage();
  await p.goto(BASE + "inventaire.html");

  const js = (await (await fetch(BASE + "donnees-simulees.js")).text())
    .replace(/\/\/.*$/gm, "").replace(/\/\*[\s\S]*?\*\//g, "");
  // Le tableau des articles à compter ne doit porter QUE id / nom / unité :
  // aucune quantité (attendue, prévue, stock) ne descend jusqu'à la page.
  const tab = js.slice(js.indexOf("articles: [", js.indexOf("inventaire:")));
  const corps = tab.slice(0, tab.indexOf("]"));
  check(!/(attendu|pr[ée]vu|quantit|qte|\bstock\s*:)/i.test(corps),
        "inventaire: le tableau des articles ne porte aucune quantité (id / nom / unité seulement)");
  // Aucun champ pré-rempli : l'agent part d'une saisie vide.
  check((await p.inputValue("#saisie")) === "",
        "inventaire: le champ de saisie est vide au départ (rien n'est pré-rempli)");

  const art1 = await p.textContent("#art-nom");
  await p.fill("#saisie", "28");
  await p.keyboard.press("Enter");
  const art2 = await p.textContent("#art-nom");
  check(art1 !== art2, `inventaire: saisie + Entrée -> article suivant (${art1} -> ${art2})`);
  check((await p.textContent("#progression")).trim().startsWith("2 /"),
        `inventaire: progression mise à jour (${(await p.textContent("#progression")).trim()})`);
  await ctx.close();
}

await b.close();
console.log(`RÉUSSIS (${ok.length}) :`);
ok.forEach((s) => console.log("  [ok] " + s));
if (ko.length) { console.log(`\nÉCHECS (${ko.length}) :`); ko.forEach((s) => console.log("  [ECHEC] " + s)); }
process.exit(ko.length ? 1 : 0);
