import sys
from anef_base import *
from anef_web import recuperer

def resume(d):
 lignes = ["Etape : " + nom_etape(d["frise"]),
     "Statut : " + str(d["statut"]).split("|")[0]]
 if d["date_statut"]:
  lignes.append("Depuis le : " + str(d["date_statut"])[:10])
 if d["entretien"]:
  lignes.append("Entretien : " + str(d["entretien"])[:16].replace("T", " "))
 if d["decret"]:
  lignes.append("Decret n. " + str(d["decret"]))
 if d["notifications"]:
  n = d["notifications"][-1]
  lignes.append("Derniere notification : " + str(n["date"])[:10] + " " + str(n["type"] or "") + " " + str(n["motif"] or ""))
 return "\n".join(lignes)


ancien = lire_etat() or {}
try:
 data = recuperer()
except Exception as e:
 echecs = ancien.get("echecs", 0) + 1
 print("echec de la verification n.", echecs, ":", type(e).__name__, str(e)[:150])
 ancien["echecs"] = echecs
 ecrire_etat(ancien)
 if echecs == 3 or (echecs > 3 and (echecs - 3) == (echecs - 3) // 24 * 24) or TEST:
  notif("Suivi ANEF : connexion impossible",
     "Le suivi n'arrive plus a lire ton dossier (" + str(echecs) + " echecs de suite). "
     "Verifie ton identifiant / mot de passe ANEF ou si le site est en maintenance.", "3")
 sys.exit(0 if echecs < 3 else 1)

champs = {k: empreinte(v) for k, v in data.items()}
anciens = ancien.get("champs")
nouveau = {"champs": champs, "echecs": 0}
ecrire_etat(nouveau)

if anciens is None:
 print("premier releve enregistre")
 notif("Suivi ANEF active", "Le suivi de ton dossier tourne.\n" + resume(data), "3")
else:
 changes = [k for k in champs if champs[k] != anciens.get(k)]
 print("changements:", changes if changes else "aucun")
 if changes:
  noms = {"statut": "statut", "date_statut": "date du statut", "frise": "etape", "notifications": "nouvelle notification",
    "decret": "decret", "entretien": "entretien", "complement": "demande de complement"}
  notif("ANEF : ton dossier a change !",
     "Changement : " + ", ".join(noms.get(c, c) for c in changes) + "\n\n" + resume(data), "5")
 elif TEST:
  notif("Test suivi ANEF", "Aucun changement.\n" + resume(data), "3")
