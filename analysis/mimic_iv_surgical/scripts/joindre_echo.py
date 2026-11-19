from study_config import required_file, workspace_dir
import os
os.chdir(workspace_dir())
import pandas as pd, numpy as np, glob, time
from sklearn.metrics import roc_auc_score
F_ECHO = str(required_file("HOOPCARE_ECHO_FILE"))
GARDE = {"lvef", "lvef_upper", "biplane_lvef", "tr_mmhg", "ivc", "pasp_underestimated_tr", "tapse", "rv_function",
         "av_mean_grad", "av_area_continuity", "av_pk_vel", "aortic_stenosis", "septal_thickness"}
t0 = time.time(); parts = []
for ch in pd.read_csv(F_ECHO, usecols=["subject_id", "measurement_id", "measurement_datetime", "test_type", "measurement", "result"],
                      dtype=str, chunksize=2_000_000):
    parts.append(ch[(ch.test_type == "tte") & ch.measurement.isin(GARDE) & ch.result.notna()])
M = pd.concat(parts); print(f"mesures gardées : {len(M)} ({time.time() - t0:.0f} s)")
X = M.pivot_table(index=["subject_id", "measurement_id", "measurement_datetime"], columns="measurement", values="result", aggfunc="first").reset_index()
X["subject_id"] = X.subject_id.astype(int); X["te"] = pd.to_datetime(X.measurement_datetime)
S = lambda c: X[c] if c in X else pd.Series(np.nan, index=X.index)
num = lambda c: pd.to_numeric(S(c), errors="coerce")
txt = lambda c: S(c).fillna("").astype(str).str.lower()
print("échos TTE :", len(X), "| patients :", X.subject_id.nunique())
lvef, lvu, bip = num("lvef"), num("lvef_upper"), num("biplane_lvef")
mil = pd.Series(np.where(lvu.notna() & (lvu < 100), (lvef + lvu) / 2, lvef), index=X.index)
ivc = txt("ivc")
rap = np.select([ivc.str.contains(r"0-5|nl ivc|<1\.5"), ivc.str.contains(r"5-10|10-15"), ivc.str.contains(r">15|dilated")], [3, 8, 15], 8)
tr = num("tr_mmhg"); tr[S("pasp_underestimated_tr").notna()] = np.nan
pasp = tr + rap
tapse = num("tapse"); rvf = txt("rv_function")
rv_vis = pd.Series(np.select([rvf.str.contains("moderate|severe|depressed"), rvf.str.contains("nl rv|low normal|mild|hyperdynamic")], [1.0, 0.0], np.nan), index=X.index)
g = txt("aortic_stenosis"); mg, ava, vmax = num("av_mean_grad"), num("av_area_continuity"), num("av_pk_vel")
as_pos = (mg >= 40) | (ava <= 1.0) | g.str.contains("severe")
as_neg = ~as_pos & ((vmax < 3) | g.str.match(r"^(none|minimal|mild|mod)"))
sept = num("septal_thickness")
T = {}
for t in (30, 35, 40, 45, 50): T[f"FEVG <= {t}"] = (lvef <= t, lvef.notna(), f"raw_lvef_lte_{t}")
T["FEVG < 40 (sens.)"] = (lvef < 40, lvef.notna(), "raw_lvef_lte_40")
T["FEVG <= 40 milieu (sens.)"] = (mil <= 40, lvef.notna(), "raw_lvef_lte_40")
T["FEVG <= 40 biplan (sens.)"] = (bip <= 40, bip.notna(), "raw_lvef_lte_40")
for t in (40, 50, 60): T[f"PAPS >= {t}"] = (pasp >= t, pasp.notna(), f"raw_ph_rvsp{t}")
T["PAPS >= 40 OD+5 (sens.)"] = (tr + 5 >= 40, tr.notna(), "raw_ph_rvsp40")
T["PAPS >= 40 OD+10 (sens.)"] = (tr + 10 >= 40, tr.notna(), "raw_ph_rvsp40")
T["VD TAPSE < 1,7 cm"] = (tapse < 1.7, tapse.notna(), "raw_rv_dysfunction")
T["VD visuel >= modere (sens.)"] = (rv_vis == 1, rv_vis.notna(), "raw_rv_dysfunction")
T["RAo serre"] = (as_pos, as_pos | as_neg, "raw_as_severe")
T["Septum >= 1,5 cm"] = (sept >= 1.5, sept.notna(), "raw_hcm")
F = sorted(glob.glob("results/mimic_complet/paquet_*.csv")); cols = set(pd.read_csv(F[0], nrows=0).columns)
voulu = {h for _, _, h in T.values()}; H = sorted(voulu & cols)
print("paquets :", len(F), "| têtes manquantes :", sorted(voulu - cols))
E = pd.concat(pd.read_csv(f, usecols=["subject_id", "ecg_time"] + H) for f in F); E = E[E[H[0]].notna()]
E["t"] = pd.to_datetime(E.ecg_time); E = E.sort_values("t")
def auc(y, s):
    rng = np.random.default_rng(0); bs = []
    for _ in range(500):
        i = rng.integers(0, len(y), len(y))
        if 0 < y[i].sum() < len(i): bs.append(roc_auc_score(y[i], s[i]))
    return roc_auc_score(y, s), np.percentile(bs, 2.5), np.percentile(bs, 97.5)
def evaluer(nom, jours):
    pos, elig, h = T[nom]
    if h not in E: return
    x = X.loc[elig.values, ["subject_id", "te"]].assign(y=pos[elig].astype(int).values).sort_values("te")
    m = pd.merge_asof(x, E[["subject_id", "t", h]], left_on="te", right_on="t", by="subject_id", direction="nearest", tolerance=pd.Timedelta(days=jours))
    m = m[m[h].notna()].assign(ecart=lambda d: (d.te - d.t).abs()).sort_values("ecart").groupby("subject_id").head(1)
    y, s = m.y.values, m[h].values
    if y.sum() < 10: print(f"  {nom:28s} <={jours:3d} j : positifs={y.sum()} trop peu"); return
    a, lo, hi = auc(y, s); print(f"  {nom:28s} <={jours:3d} j : {y.sum():5d}/{len(y):6d} ({y.mean():5.1%}) | AUROC {a:.3f} ({lo:.3f}-{hi:.3f})")
print("\n=== principal : ECG le plus proche de l'écho, <= 14 j, 1 paire par patient")
for nom in T: evaluer(nom, 14)
print("\n=== sensibilité à la fenêtre")
for nom in ("FEVG <= 40", "FEVG <= 50", "PAPS >= 40", "VD TAPSE < 1,7 cm", "RAo serre"):
    for j in (1, 30, 90): evaluer(nom, j)
