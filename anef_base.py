import os, sys, json, hmac, hashlib, re, requests
from playwright.sync_api import sync_playwright

BASE = "https://administration-etrangers-en-france.interieur.gouv.fr"
LOGIN = BASE + "/usagers/#/espace-personnel/connexion-inscription"
COMPTE = BASE + "/usagers/#/espace-personnel/mon-compte"
API = BASE + "/api"
USER = os.environ["ANEF_USER"]
PWD = os.environ["ANEF_PASS"]
TOPIC = os.environ["NTFY_TOPIC"]
TEST = os.environ.get("TEST") == "true"
FICHIER = "etat/anef.json"

ETAPES = {
 "demande_envoyee": "Demande envoyee",
 "examen_pieces": "Examen des pieces (verification formelle)",
 "demande_deposee": "Demande recevable, en attente d'affectation",
 "traitement_instruction": "Instruction en cours",
 "recepisse_completude": "Recepisse de completude (dossier complet)",
 "traitement_instruction_2": "Enquetes en cours, date d'entretien a fixer",
 "entretien_assimilation": "Entretien d'assimilation",
 "traitement_plateforme_3": "Avis de la prefecture en cours",
 "decision_prefecture": "Decision de la prefecture",
 "traitement_sdanf_1": "Controle SDANF",
 "traitement_scec": "Traitement SCEC (Nantes)",
 "traitement_sdanf_2": "Validation SDANF",
 "decision_prise": "Decision prise",
 "ceremonie_naturalisation": "Decret publie / ceremonie",
}
DEBUT = ["demande_envoyee", "demande_envoyee", "examen_pieces"]
SUITE = ["demande_deposee", "traitement_instruction", "recepisse_completude", "traitement_instruction_2",
   "entretien_assimilation", "traitement_plateforme_3"]
FRISES = {
 "DECISION_PLATEFORME_AVANT_VF": DEBUT + ["traitement_instruction", "decision_prefecture"],
 "DECISION_PLATEFORME_AVANT_RECEPISSE_COMPLETUDE": DEBUT + ["demande_deposee", "traitement_instruction", "decision_prefecture"],
 "DECISION_PLATEFORME_AVANT_EA": DEBUT + SUITE[:4] + ["decision_prefecture"],
 "DECISION_PLATEFORME_APRES_EA": DEBUT + SUITE + ["decision_prefecture"],
 "DECISION_SDANF_AVANT_SCEC": DEBUT + SUITE + ["traitement_sdanf_1", "decision_prise"],
 "DECISION_SDANF_APRES_SCEC": DEBUT + SUITE + ["traitement_sdanf_1", "traitement_scec", "traitement_sdanf_2", "decision_prise"],
 "COMPLET_SANS_SCEC": DEBUT + SUITE + ["traitement_sdanf_1", "decision_prise", "ceremonie_naturalisation"],
 "COMPLET": DEBUT + SUITE + ["traitement_sdanf_1", "traitement_scec", "traitement_sdanf_2", "decision_prise", "ceremonie_naturalisation"],
}


def notif(titre, msg, prio="4"):
 try:
  r = requests.post("https://ntfy.sh/" + TOPIC, data=msg.encode("utf-8"),
        headers={"Title": titre, "Priority": prio, "Click": BASE + "/usagers/"}, timeout=15)
  print("notification envoyee:", r.status_code)
 except Exception as e:
  print("notification erreur:", type(e).__name__)


def empreinte(valeur):
 texte = json.dumps(valeur, sort_keys=True, ensure_ascii=False)
 return hmac.new(PWD.encode(), texte.encode(), hashlib.sha256).hexdigest()[:16]


def lire_etat():
 try:
  with open(FICHIER) as f:
   return json.load(f)
 except Exception:
  return None


def ecrire_etat(etat):
 os.makedirs("etat", exist_ok=True)
 with open(FICHIER, "w") as f:
  json.dump(etat, f)


def nom_etape(frise):
 if not frise:
  return "inconnue"
 t = str(frise.get("type_frise") or "").upper()
 if t == "COMPLET" and frise.get("has_step_scec") is False:
  t = "COMPLET_SANS_SCEC"
 liste = FRISES.get(t, FRISES["COMPLET"])
 i = frise.get("id_active")
 if isinstance(i, int) and 0 <= i < len(liste):
  return ETAPES[liste[i]] + " (etape " + str(i) + ")"
 return "etape " + str(i) + " (" + t + ")"


