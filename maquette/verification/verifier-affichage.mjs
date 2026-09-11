/* Vérifie, PAR EXÉCUTION, que les 4 écrans de la maquette s'affichent aux 5
   largeurs cibles sans débordement horizontal, sans erreur console, et avec des
   cibles tactiles d'au moins 44 px sur mobile. Produit une capture par cas dans
   ../captures/.

   Prérequis : servir la maquette d'abord —  depuis ../  :  py -m http.server 8080
   Puis, depuis ce dossier :  npm install  &&  npm run affichage
*/
import { chromium } from "playwright";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const ICI  = dirname(fileURLToPath(import.meta.url));
const BASE = process.env.MAQUETTE_URL || "http://127.0.0.1:8080/";
const OUT  = resolve(ICI, "..", "captures") + "/";

const pages = [
  { file: "connexion.html",    nom: "connexion" },
  { file: "vente.html",        nom: "vente" },
  { file: "tableau-bord.html", nom: "tableau-bord" },
  { file: "inventaire.html",   nom: "inventaire" },
];
const largeurs = [360, 390, 768, 1366, 1920];

const browser = await chromium.launch({ channel: "chrome" });
const resultats = [];

for (const p of pages) {
  for (const w of largeurs) {
    const h = w < 700 ? 780 : w < 1400 ? 800 : 960;
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    const erreursConsole = [];
    page.on("console", (m) => { if (m.type() === "error") erreursConsole.push(m.text()); });
    page.on("pageerror", (e) => erreursConsole.push("PAGEERROR: " + e.message));
    await page.goto(BASE + p.file, { waitUntil: "networkidle" });
    await page.waitForTimeout(150);

    const m = await page.evaluate(() => {
      const de = document.documentElement, vw = window.innerWidth;
      const debordants = [...document.querySelectorAll("*")]
        .filter((el) => el.getBoundingClientRect().right > vw + 1)
        .slice(0, 6)
        .map((el) => el.tagName.toLowerCase() + (el.className ? "." + String(el.className).trim().split(/\s+/).join(".") : ""));
      const cibles = [...document.querySelectorAll("button, a, input, select, [role=option]")]
        .map((el) => Math.round(el.getBoundingClientRect().height)).filter((x) => x > 0);
      return {
        innerWidth: vw,
        overflowH: de.scrollWidth > de.clientWidth + 1,
        debordants,
        cibleMin: cibles.length ? Math.min(...cibles) : null,
      };
    });

    await page.screenshot({ path: OUT + p.nom + "-" + w + ".png", fullPage: true });
    resultats.push({ page: p.nom, w, ...m, erreursConsole });
    console.log(
      `${p.nom.padEnd(14)} ${String(w).padStart(4)}  débordement=${m.overflowH}` +
      `  cibleMin=${m.cibleMin}px  erreurs=${erreursConsole.length}` +
      (m.debordants.length ? `  ${JSON.stringify(m.debordants)}` : "")
    );
    await ctx.close();
  }
}
await browser.close();

const echecs = resultats.filter(
  (r) => r.overflowH || r.erreursConsole.length || (r.w <= 768 && r.cibleMin !== null && r.cibleMin < 44)
);
console.log(`\n${resultats.length} captures — ${echecs.length} échec(s).`);
if (echecs.length) { console.log(JSON.stringify(echecs, null, 2)); process.exit(1); }
