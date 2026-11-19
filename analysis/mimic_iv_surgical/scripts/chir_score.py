"""
Cohorte chirurgicale MIMIC-IV — ÉTAPE 2, partie A : scores des ECG index (après le enregistrement du protocole, 17/11/2026 16:05).
Aucun événement lu ici : ce script ne produit que des scores et leur répartition.
- 12 dérivations : repris de results/mimic_complet (même modèle figé v4, déjà calculé pour tous les ECG MIMIC).
- I–III et I seul : calculés ici avec exactement la fonction formats() de score_3formats.py.
- Score S = noisy-OR des 5 sorties calibrées (FEVG ≤50, PAPS ≥40, dysfonction VD, RAo serré, HCM),
  calibrateurs « diagnostic / internal » — identique à table3_mimic.py et au manuscrit (1 − ∏(1 − p)).
Usage : nohup python3 scripts/chir_score.py results/chir_index_v1_c34.csv > results/chir_score.log 2>&1 &
Reprise automatique : les paquets déjà écrits ne sont pas recalculés.
"""
from study_config import required_dir, workspace_dir, script_path
import numpy as np, pandas as pd, wfdb, sys, time, glob, torch
from pathlib import Path
IDX = sys.argv[1] if len(sys.argv) > 1 else "results/chir_index_v1_c34.csv"
tag = Path(IDX).stem.replace("chir_index_v1_", "")
sys.argv = ["x"]; exec(open(script_path("rotation_memes_patients.py")).read().split("A = pd.read_csv")[0])   # charge le modèle figé (SC, BASE, ORD)
torch.set_num_threads(2)
HP = ["lvef_lte_50", "ph_rvsp40", "rv_dysfunction", "as_severe", "hcm"]
OUT = Path(f"results/chir_scores_{tag}"); OUT.mkdir(exist_ok=True)

def formats(x):                                   # copie exacte de scripts/score_3formats.py
    I, II = x[0], x[1]
    l3 = x.copy(); l3[3], l3[4], l3[5] = -(I + II) / 2, I - II / 2, II - I / 2; l3[6:] = II
    l1 = x.copy(); l1[1:] = I
    return {"limb3": l3, "lead1": l1}

# ---------- ECG index -> fichier MIMIC-IV-ECG
U = pd.read_csv(IDX, parse_dates=["ecg_time"])[["subject_id", "ecg_time"]].drop_duplicates()
rl = pd.read_csv(BASE / "record_list.csv"); rl["ecg_time"] = pd.to_datetime(rl.ecg_time)
U = U.merge(rl[["subject_id", "study_id", "ecg_time", "path"]], on=["subject_id", "ecg_time"], how="left")
U = U.sort_values("study_id").drop_duplicates(["subject_id", "ecg_time"]).reset_index(drop=True)
print(f"{len(U)} ECG index | sans fichier : {int(U.path.isna().sum())}", flush=True)
U = U[U.path.notna()].reset_index(drop=True)

# ---------- 12 dérivations : déjà calculé
fc = sorted(glob.glob("results/mimic_complet/paquet_*.csv"))
C = pd.concat(pd.read_csv(f, usecols=lambda c: c in ["study_id", "refus"] + ["raw_" + h for h in HP]) for f in fc)
print(f"mimic_complet : {len(fc)} paquets, {len(C)} ECG (record_list : {len(rl)})", flush=True)

# ---------- I–III et I : à calculer
TP = 1000; NP = (len(U) + TP - 1) // TP; t0 = time.time()
for k in range(NP):
    f = OUT / f"part_{k:03d}.csv"
    if f.exists(): continue
    L = []
    for _, r in U.iloc[k * TP:(k + 1) * TP].iterrows():
        ligne = {"study_id": r.study_id}
        try:
            rec = wfdb.rdrecord(str(BASE / r.path))
            x = np.nan_to_num(np.stack([rec.p_signal[:, rec.sig_name.index(n)] for n in ORD]).astype(np.float32))
            for fmt, xx in formats(x).items():
                p = SC.predict(xx, fs=float(rec.fs), leads=fmt, population="internal", strict=True)
                if p["problems"]: ligne[f"refus_{fmt}"] = "; ".join(map(str, p["problems"]))[:120]; continue
                ligne.update({f"{fmt}_{h}": p["panel"][h]["raw"] for h in HP if h in p["panel"]})
        except Exception as e:
            ligne["refus_lecture"] = type(e).__name__
        L.append(ligne)
    pd.DataFrame(L).to_csv(f, index=False); print(f"part {k + 1}/{NP} | {(time.time() - t0) / 3600:.2f} h", flush=True)

# ---------- assemblage, contrôle qualité, score combiné
F3 = pd.concat(pd.read_csv(f) for f in sorted(OUT.glob("part_*.csv")))
D = U[["subject_id", "study_id", "ecg_time"]].merge(C, on="study_id", how="left").merge(F3, on="study_id", how="left")
CAL = {f: SC._calibration_set(SC.panel, f, "diagnostic", "internal")[0] for f in ("12lead", "limb3", "lead1")}
cal = lambda fmt, h, x: np.clip(np.interp(np.asarray(x, float), np.asarray(CAL[fmt][h]["x"], float), np.asarray(CAL[fmt][h]["y"], float)), 0, 1)
noisy = lambda ps: 1 - np.prod([1 - p for p in ps], axis=0)
cols = {"12lead": ["raw_" + h for h in HP], "limb3": ["limb3_" + h for h in HP], "lead1": ["lead1_" + h for h in HP]}
for fmt, cc in cols.items():
    for c in cc:
        if c not in D: D[c] = np.nan
    D[f"ok_{fmt}"] = D[cc].notna().all(axis=1)
    D[f"S_{fmt}"] = noisy([cal(fmt, h, D[c]) for h, c in zip(HP, cc)])
D["qc_ok"] = D.ok_12lead & D.ok_limb3 & D.ok_lead1          # protocole : refus dans un format = exclu de tous
D[["subject_id", "study_id", "ecg_time", "qc_ok", "S_12lead", "S_limb3", "S_lead1"]].to_csv(f"results/chir_scores_{tag}.csv", index=False)

# ---------- résumé (scores seulement, aucun événement)
print(f"\nECG index : {len(D)} | refus 12 dérivations : {int((~D.ok_12lead).sum())} | I–III : {int((~D.ok_limb3).sum())} | I : {int((~D.ok_lead1).sum())} | exclus (un refus ou plus) : {int((~D.qc_ok).sum())}")
q = D[D.qc_ok]
for fmt in cols:
    s = q[f"S_{fmt}"]
    print(f"  {fmt:<7} médiane {s.median():.3f} | P95 {s.quantile(.95):.3f} | ≥0.635 : {(s >= .635).mean():.1%} | ≥0.453 : {(s >= .453).mean():.1%}")
print(f"\nécrit : results/chir_scores_{tag}.csv (scores par ECG, reste sur la VM). Terminé.", flush=True)
