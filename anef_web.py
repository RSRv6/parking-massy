from anef_base import *
from playwright.sync_api import sync_playwright

JS_FETCH = """async (urls) => {
  const out = {};
  for (const [k, u] of Object.entries(urls)) {
 try {
   const r = await fetch(u, {credentials: 'include'});
   const t = await r.text();
   let j = null;
   try { j = JSON.parse(t); } catch (e) {}
   out[k] = {status: r.status, json: j};
 } catch (e) { out[k] = {status: 0, json: null}; }
  }
  return out;
}"""


def connexion(page):
 page.goto(COMPTE, wait_until="networkidle", timeout=60000)
 champ = "input[name='username'], input[type='email'], input#username"
 for t in ["Tout refuser", "Refuser", "Continuer sans accepter", "Accepter"]:
  try:
   page.get_by_role("button", name=t).first.click(timeout=1500)
   break
  except Exception:
   pass
 try:
  page.wait_for_selector(champ, timeout=15000)
 except Exception:
  page.goto(LOGIN, wait_until="networkidle", timeout=60000)
  boutons = page.locator("dsfr-button button, p-button button, button, a.fr-btn")
  for i in range(boutons.count()):
   b = boutons.nth(i)
   try:
    if b.is_visible() and re.fullmatch(r"\s*se\s*connecter\s*", b.inner_text(), re.I):
     b.click()
     break
   except Exception:
    pass
  page.wait_for_selector(champ, timeout=30000)
 page.fill(champ, USER)
 page.fill("input[name='password'], input[type='password']", PWD)
 page.locator("button[type='submit'], input[type='submit']").first.click()
 page.wait_for_url(lambda u: "administration-etrangers-en-france" in u, timeout=60000)
 page.wait_for_load_state("networkidle")
 if "mon-compte" not in page.url:
  page.goto(COMPTE, wait_until="networkidle", timeout=60000)
 page.wait_for_timeout(3000)


def recuperer():
 with sync_playwright() as p:
  b = p.chromium.launch()
  page = b.new_page(locale="fr-FR")
  try:
   connexion(page)
   res = page.evaluate(JS_FETCH, {
    "stepper": API + "/anf/dossier-stepper",
    "frise": API + "/anf/usager/dossiers/frise-stepper",
    "notifs": API + "/notifications",
   })
   st = res["stepper"]
   dossier = (st.get("json") or {}).get("dossier") if isinstance(st.get("json"), dict) else None
   if not dossier or not dossier.get("statut"):
    raise RuntimeError("statut introuvable (HTTP " + str(st.get("status")) + ")")
   detail = None
   if dossier.get("id"):
    d = page.evaluate(JS_FETCH, {"d": API + "/anf/usager/dossiers/" + str(dossier["id"])})["d"]
    if isinstance(d.get("json"), dict):
     detail = d["json"].get("data", d["json"])
  finally:
   b.close()
 fj = res["frise"].get("json")
 fj = fj.get("data", fj) if isinstance(fj, dict) else None
 frise = {k: fj.get(k) for k in ("id_active", "type_frise", "has_step_scec")} if fj else None
 nj = res["notifs"].get("json")
 items = []
 if isinstance(nj, dict):
  items = nj.get("_items") or nj.get("items") or nj.get("data") or []
 elif isinstance(nj, list):
  items = nj
 notifs = sorted([{"type": n.get("type_notification"), "motif": n.get("motif_notification"),
       "date": n.get("_created") or n.get("date_creation") or n.get("date")}
      for n in items if isinstance(n, dict)], key=lambda n: str(n["date"]))
 decret = None
 entretien = None
 complement = None
 if detail:
  try:
   for it in detail["demande"]["informations"]["etat_civil"]["identites_decrets"] or []:
    if isinstance(it, dict) and (it.get("decret") or {}).get("id"):
     decret = it["decret"]["id"]
  except Exception:
   pass
  entretien = (detail.get("entretien_assimilation") or {}).get("date_rdv")
  complement = detail.get("demande_complement")
 return {
  "statut": dossier.get("statut"),
  "date_statut": dossier.get("date_statut"),
  "frise": frise,
  "notifications": notifs,
  "decret": decret,
  "entretien": entretien,
  "complement": complement,
 }


