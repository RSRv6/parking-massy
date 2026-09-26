import os, sys, time, requests
from datetime import datetime
from playwright.sync_api import sync_playwright
URL = "https://www.effia.com/parking/parking-gare-de-massy-vilmorin-pr-effia?entry=2026-11-01T00:00&exit=2026-11-30T00:00&vehicle=AUTO&qty=1&premium=FALSE&electric=FALSE&orderType=subscription"
DUREE = 5 * 3600 + 35 * 60
PAUSE = 5 * 60
def notif(titre, msg, prio):
 try:
  r = requests.post("https://ntfy.sh/massy-parking-7ceb6a7293", data=msg.encode(), headers={"Title": titre, "Priority": prio, "Click": URL}, timeout=15)
  print("notif", r.status_code, flush=True)
 except Exception as e:
  print("notif erreur", e, flush=True)
def relancer():
 r = requests.post("https://api.github.com/repos/" + os.environ["REPO"] + "/actions/workflows/veille.yml/dispatches",
  headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"], "Accept": "application/vnd.github+json"},
  json={"ref": "main", "inputs": {"test": "false"}}, timeout=15)
 print("relance", r.status_code, r.text[:200], flush=True)
def visible(loc):
 return any(loc.nth(i).is_visible() for i in range(loc.count()))
def verifier(p):
 b = p.chromium.launch()
 try:
  page = b.new_page(locale="fr-FR", viewport={"width": 1280, "height": 900})
  page.goto(URL, wait_until="networkidle", timeout=60000)
  for t in ["Refuser", "Continuer sans accepter", "Tout refuser", "Accepter"]:
   try:
    page.get_by_role("button", name=t).first.click(timeout=2000)
    break
   except Exception:
    pass
  try:
   page.locator("a[href='#subscribe']").first.click(timeout=5000)
  except Exception:
   pass
  page.wait_for_timeout(2000)
  ok = False
  radio = page.get_by_label("Navigo - Gratuit", exact=False)
  if radio.count() > 0:
   try:
    radio.first.check(force=True, timeout=5000)
    ok = True
   except Exception as e:
    print("radio:", e)
  if not ok:
   txt = page.get_by_text("Navigo - Gratuit", exact=False)
   for i in range(txt.count()):
    if txt.nth(i).is_visible():
     txt.nth(i).click()
     ok = True
     break
  page.wait_for_load_state("networkidle")
  page.wait_for_timeout(4000)
  complet = visible(page.get_by_text("Plus d'abonnement disponible", exact=False))
  libre = visible(page.get_by_text("S'abonner", exact=True)) or visible(page.get_by_text("restante", exact=False))
  if ok and not complet:
   page.screenshot(path="capture.png", full_page=True)
  return ok, complet, libre
 finally:
  b.close()
debut = time.time()
n = 0
with sync_playwright() as p:
 while True:
  n += 1
  try:
   ok, complet, libre = verifier(p)
  except Exception as e:
   print(str(datetime.now())[11:16], "erreur:", str(e)[:200], flush=True)
   ok, complet, libre = False, True, False
  etat = "COMPLET" if complet else ("LIBRE" if libre else "INCONNU")
  print(str(datetime.now())[11:16], "verif", n, "offre cochee:", ok, "etat:", etat, flush=True)
  if n == 1 and os.environ.get("TEST") == "true":
   notif("Test parking", "La veille tourne. Offre cochee: " + str(ok) + ". Etat: " + etat, "3")
  if ok and not complet:
   notif("Place libre a Massy Vilmorin", "Abonnement Navigo gratuit peut-etre disponible (" + etat + "). Vite !", "5")
   time.sleep(15 * 60)
   relancer()
   sys.exit("PLACE LIBRE - va vite sur effia.com")
  if time.time() - debut + PAUSE > DUREE:
   break
  time.sleep(PAUSE)
relancer()
