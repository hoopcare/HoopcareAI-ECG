from study_config import script_path
import numpy as np, pandas as pd, wfdb, sys, time, torch
from pathlib import Path
sys.argv = ["x"]; exec(open(script_path("rotation_memes_patients.py")).read().split("A = pd.read_csv")[0])   # recharge le modèle (SC, BASE, ORD)
torch.set_num_threads(2)
OUT = Path("results/mimic_complet"); TAILLE = 2000
rl = pd.read_csv(BASE / "record_list.csv"); N = len(rl); n_paquets = (N + TAILLE - 1) // TAILLE
print(f"{N} ECG, {n_paquets} paquets de {TAILLE}", flush=True); t0 = time.time()
for k in range(n_paquets):
    f = OUT / f"paquet_{k:04d}.csv"
    if f.exists(): continue
    lignes = []
    for _, r in rl.iloc[k * TAILLE:(k + 1) * TAILLE].iterrows():
        ligne = {"subject_id": r.subject_id, "study_id": r.study_id, "ecg_time": r.ecg_time}
        try:
            rec = wfdb.rdrecord(str(BASE / r.path)); x = np.nan_to_num(np.stack([rec.p_signal[:, rec.sig_name.index(n)] for n in ORD]).astype(np.float32))
            p = SC.predict(x, fs=float(rec.fs), leads="12lead", population="internal", strict=True)
            if p["problems"]: ligne["refus"] = "; ".join(map(str, p["problems"]))[:200]
            else:
                ligne.update({f"raw_{h}": v["raw"] for h, v in p["panel"].items()}); ligne.update({f"reg_{h}": v.get("value") for h, v in p["regression"].items()})
        except Exception as e:
            ligne["refus"] = f"erreur lecture : {type(e).__name__}"[:200]
        lignes.append(ligne)
    pd.DataFrame(lignes).to_csv(f, index=False)
    fait = k + 1; ecoule = time.time() - t0
    print(f"paquet {fait}/{n_paquets} | {ecoule / 3600:.1f} h écoulées", flush=True)
print("Terminé", flush=True)
