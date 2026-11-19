from study_config import script_path
import numpy as np, pandas as pd, wfdb, sys, time, torch
from pathlib import Path
sys.argv = ["x"]; exec(open(script_path("rotation_memes_patients.py")).read().split("A = pd.read_csv")[0])
torch.set_num_threads(2)
OUT = Path("results/mimic_3formats"); OUT.mkdir(exist_ok=True)
H = ["lvef_lte_30", "lvef_lte_35", "lvef_lte_40", "lvef_lte_45", "lvef_lte_50", "ph_rvsp40", "ph_rvsp50", "ph_rvsp60",
     "rv_dysfunction", "as_severe", "hcm", "hyperk_ge55", "hyperk_ge60", "hypok_le35", "hypok_le30"]
P = pd.read_csv("results/paires_principales.csv"); P["t"] = pd.to_datetime(P.t)
rl = pd.read_csv(BASE / "record_list.csv"); rl["t"] = pd.to_datetime(rl.ecg_time)
U = P[["subject_id", "t"]].drop_duplicates().merge(rl[["subject_id", "t", "path"]], on=["subject_id", "t"], how="left")
print(len(U), "ECG uniques | sans fichier :", int(U.path.isna().sum()), flush=True)
U = U[U.path.notna()].reset_index(drop=True)
def formats(x):
    I, II = x[0], x[1]
    l3 = x.copy(); l3[3], l3[4], l3[5] = -(I + II) / 2, I - II / 2, II - I / 2; l3[6:] = II
    l1 = x.copy(); l1[1:] = I
    return {"limb3": l3, "lead1": l1}
TP = 2000; NP = (len(U) + TP - 1) // TP; t0 = time.time()
for k in range(NP):
    f = OUT / f"part_{k:03d}.csv"
    if f.exists(): continue
    L = []
    for _, r in U.iloc[k * TP:(k + 1) * TP].iterrows():
        ligne = {"subject_id": r.subject_id, "t": r.t}
        try:
            rec = wfdb.rdrecord(str(BASE / r.path))
            x = np.nan_to_num(np.stack([rec.p_signal[:, rec.sig_name.index(n)] for n in ORD]).astype(np.float32))
            for fmt, xx in formats(x).items():
                p = SC.predict(xx, fs=float(rec.fs), leads=fmt, population="internal", strict=True)
                if p["problems"]: ligne[f"refus_{fmt}"] = "; ".join(map(str, p["problems"]))[:120]; continue
                ligne.update({f"{fmt}_{h}": p["panel"][h]["raw"] for h in H if h in p["panel"]})
                ligne[f"{fmt}_hgb_v"] = p["regression"].get("hgb_v", {}).get("value")
        except Exception as e:
            ligne["refus_lecture"] = type(e).__name__
        L.append(ligne)
    pd.DataFrame(L).to_csv(f, index=False); print(f"part {k + 1}/{NP} | {(time.time() - t0) / 3600:.1f} h", flush=True)
print("Terminé", flush=True)
