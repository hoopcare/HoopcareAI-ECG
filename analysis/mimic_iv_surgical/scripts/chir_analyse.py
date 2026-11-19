"""
Cohorte chirurgicale MIMIC-IV — ÉTAPE 2, partie B : analyses du protocole enregistré (17/11/2026),
dans l'ordre du tableau « Analyses ». Aucune analyse ajoutée ; tout écart sera signalé comme déviation.
Entrées (sur la VM) : results/chir_index_v1_c34.csv, chir_scores_c34.csv, chir_covariables_c34.csv
  + pour les sensibilités : chir_cohorte_v1_c4.csv / chir_covariables_c4.csv, chir_cohorte_v1_c34_ecg90.csv / chir_covariables_c34_ecg90.csv
Sortie : results/chir_resultats_c34.txt — agrégats seulement (effectifs, risques, OR, AUROC).
Usage : python3 scripts/chir_analyse.py
"""
from study_config import required_dir, workspace_dir, script_path
import os, re, glob, numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
W = str(workspace_dir()); os.chdir(W); MH = str(required_dir("HOOPCARE_DATA_ROOT") / "mimic-iv/v3.1/hosp") + "/"
OUT = open("results/chir_resultats_c34.txt", "w")
def p(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); OUT.write(s + "\n")
T1, T2 = 0.635, 0.453
HP = ["lvef_lte_50", "ph_rvsp40", "rv_dysfunction", "as_severe", "hcm"]
lgt = lambda s: np.log(np.clip(s, 1e-6, 1 - 1e-6) / (1 - np.clip(s, 1e-6, 1 - 1e-6)))
pc = lambda a, b: f"{a} ({a / b:.1%})" if b else f"{a}"

# ---------- outils statistiques
def logit_fit(X, y):                                   # Newton-Raphson, erreurs types de Wald
    X = np.column_stack([np.ones(len(X)), X]); b = np.zeros(X.shape[1])
    for _ in range(100):
        pr = 1 / (1 + np.exp(-np.clip(X @ b, -30, 30))); H = X.T @ (X * (pr * (1 - pr))[:, None]) + 1e-9 * np.eye(len(b))
        d = np.linalg.solve(H, X.T @ (y - pr)); b += d
        if np.abs(d).max() < 1e-9: break
    return b, np.sqrt(np.diag(np.linalg.inv(H)))
def covs(d, rcri=True, rcol="rcri"):
    a = (d.age - 65) / 10; X = pd.DataFrame({"age": a, "age2": a ** 2, "sexe_h": d.sexe_h.astype(float)}, index=d.index)
    if rcri: X = X.join(pd.get_dummies(d[rcol].clip(upper=3).astype(int), prefix="rcri").drop(columns=["rcri_0"], errors="ignore").astype(float))
    X = X.join(pd.get_dummies(d.urgence, prefix="urg").drop(columns=["urg_programmée"], errors="ignore").astype(float))
    X = X.join(pd.get_dummies(d.categorie.fillna("autre"), prefix="cat").drop(columns=["cat_orthopédie"], errors="ignore").astype(float))
    return X.loc[:, X.std() > 0]
def or_aj(d, expo, y="y30", rcri=True, rcol="rcri"):
    X = pd.concat([pd.Series(np.asarray(expo, float), index=d.index, name="expo"), covs(d, rcri, rcol)], axis=1)
    b, se = logit_fit(X.values, d[y].values.astype(float))
    return f"{np.exp(b[1]):.2f} ({np.exp(b[1] - 1.96 * se[1]):.2f}–{np.exp(b[1] + 1.96 * se[1]):.2f})"
def auc_ic(y, s, B=2000):
    y, s = np.asarray(y), np.asarray(s, float); r = np.random.default_rng(0); bs = []
    for _ in range(B):
        i = r.integers(0, len(y), len(y))
        if 0 < y[i].sum() < len(i): bs.append(roc_auc_score(y[i], s[i]))
    return f"{roc_auc_score(y, s):.3f} ({np.percentile(bs, 2.5):.3f}–{np.percentile(bs, 97.5):.3f})"
def bloc(d, flag, nom, y="y30", rcri=True, rcol="rcri"):
    f = np.asarray(flag, bool); yy = d[y].values; n1, e1, e0 = int(f.sum()), int(yy[f].sum()), int(yy[~f].sum())
    p(f"  {nom} | n {len(d)} | signalés {pc(n1, len(d))}, décès {pc(e1, n1)} | autres {len(d) - n1}, décès {pc(e0, len(d) - n1)} | OR ajusté {or_aj(d, f, y, rcri, rcol)}")
    return e1, e0

# ---------- scores 12 dérivations pour des ECG hors du fichier de scores (sensibilités)
def s12_pour(df):
    import sys; sys.argv = ["x"]; ns = {}
    exec(open(script_path("rotation_memes_patients.py")).read().split("A = pd.read_csv")[0], ns); SC, BASE = ns["SC"], ns["BASE"]
    CAL = SC._calibration_set(SC.panel, "12lead", "diagnostic", "internal")[0]
    rl = pd.read_csv(BASE / "record_list.csv", usecols=["subject_id", "study_id", "ecg_time"]); rl["ecg_time"] = pd.to_datetime(rl.ecg_time)
    C = pd.concat(pd.read_csv(f, usecols=lambda c: c in ["study_id"] + ["raw_" + h for h in HP]) for f in sorted(glob.glob("results/mimic_complet/paquet_*.csv")))
    d = df.merge(rl, on=["subject_id", "ecg_time"], how="left").sort_values("study_id").drop_duplicates(["subject_id", "ecg_time"]).merge(C, on="study_id", how="left")
    cal = lambda h, x: np.clip(np.interp(np.asarray(x, float), np.asarray(CAL[h]["x"], float), np.asarray(CAL[h]["y"], float)), 0, 1)
    d["S_12lead"] = 1 - np.prod([1 - cal(h, d["raw_" + h]) for h in HP], axis=0); d["ok12"] = d[["raw_" + h for h in HP]].notna().all(axis=1)
    return d[["subject_id", "ecg_time", "S_12lead", "ok12"]]

# ---------- données
pat = pd.read_csv(MH + "patients.csv.gz", usecols=["subject_id", "dod"], parse_dates=["dod"])
I = pd.read_csv("results/chir_index_v1_c34.csv", parse_dates=["chartdate", "ecg_time"])
S = pd.read_csv("results/chir_scores_c34.csv", parse_dates=["ecg_time"])
V = pd.read_csv("results/chir_covariables_c34.csv")
def issues(d):
    j = (d.dod - d.chartdate).dt.days; d["y30"] = ((j >= 0) & (j <= 30)).astype(int); d["y90"] = ((j >= 0) & (j <= 90)).astype(int); return d
D = issues(I.merge(S, on=["subject_id", "ecg_time"], how="left").merge(pat, on="subject_id", how="left"))
D["qc_ok"] = D.qc_ok.fillna(False).astype(bool)
P0 = D[~D.echo365]; P = P0[P0.qc_ok].merge(V.drop(columns=["hadm_id", "chartdate"]), on="subject_id")
diag = set(pd.read_csv("results/paires_principales.csv").query("cible.str.contains('FEVG')", engine="python").subject_id.astype(int))
sous_puissance = P.y30.sum() < 100

p("=== 0. Flux et répartition du score (protocole enregistré)")
p(f"  cohorte principale {len(P0)} | exclus contrôle qualité (refus dans ≥ 1 format) {int((~P0.qc_ok).sum())} | analysés {len(P)} | décès 30 j {int(P.y30.sum())} | 90 j {int(P.y90.sum())}")
if sous_puissance: p("  MOINS DE 100 DÉCÈS À 30 J : analyse principale rapportée, sous-groupes non rapportés, cohorte décrite comme sous-puissante")
for fmt in ("12lead", "limb3", "lead1"):
    s = P["S_" + fmt]; p(f"  {fmt:<7} part ≥0.635 {(s >= T1).mean():.1%} | ≥0.453 {(s >= T2).mean():.1%} | P95 MIMIC {s.quantile(.95):.3f}")

p("\n=== 1. Analyse principale : décès à 30 j, score 12 dérivations ≥0.635 (ajusté sur âge, âge², sexe, RCRI 0/1/2/≥3, urgence, catégorie)")
bloc(P, P.S_12lead >= T1, "S ≥0.635")

p("\n=== 2. Seuils secondaires et score continu")
bloc(P, P.S_12lead >= T2, "S ≥0.453")
p(f"  logit du score (par unité) | OR ajusté {or_aj(P, lgt(P.S_12lead))}")
p("  critère secondaire, décès à 90 j :"); bloc(P, P.S_12lead >= T1, "S ≥0.635", y="y90")
q95 = P.S_12lead.quantile(.95); p(f"  RECALIBRATION (secondaire) : 95e percentile MIMIC = {q95:.3f}"); bloc(P, P.S_12lead >= q95, "S ≥ P95 MIMIC")
adm = pd.read_csv(MH + "admissions.csv.gz", usecols=["hadm_id", "hospital_expire_flag"])
dx = pd.read_csv(MH + "diagnoses_icd.csv.gz", usecols=["hadm_id", "icd_code", "icd_version"], dtype={"icd_code": str}); dx = dx[dx.hadm_id.isin(P.hadm_id)]
dx["c"] = dx.icd_code.str.replace(".", "", regex=False).str.upper()
mace = lambda c, v: c.startswith(("I21", "I22", "I46", "I61", "I63")) if v == 10 else (c.startswith(("410", "4275", "431")) or bool(re.match(r"^43[34]\d1$", c)))
hm = set(dx[[mace(c, v) for c, v in zip(dx.c, dx.icd_version)]].hadm_id) | set(adm[adm.hospital_expire_flag == 1].hadm_id)
P["mace"] = P.hadm_id.isin(hm).astype(int); f = (P.S_12lead >= T1).values
p(f"  MACE codés au séjour index (descriptif ; antériorité non séparable) : signalés {pc(int(P.mace[f].sum()), int(f.sum()))} | autres {pc(int(P.mace[~f].sum()), int((~f).sum()))}")

p("\n=== 3. Patients à bas risque : RCRI 0")
if sous_puissance: p("  non rapporté (sous-puissance)")
else:
    R0 = P[P.rcri == 0]; e1, e0 = bloc(R0, R0.S_12lead >= T1, "RCRI 0, S ≥0.635", rcri=False)
    p(f"  part des décès RCRI 0 survenus chez les signalés : {pc(e1, e1 + e0)}")

p("\n=== 4. Score seul contre RCRI : AUROC pour le décès à 30 j (bootstrap patient, 2 000)")
p(f"  score 12 dérivations {auc_ic(P.y30, P.S_12lead)} | RCRI (0–6) {auc_ic(P.y30, P.rcri)}")

p("\n=== 5. Valeur incrémentale : modèle de base ± logit du score, AUROC hors pli (5 plis séparés par patient)")
Xc = covs(P).values; X1 = np.column_stack([Xc, lgt(P.S_12lead.values)]); yv = P.y30.values; o0, o1 = np.zeros(len(P)), np.zeros(len(P))
for tr, te in StratifiedKFold(5, shuffle=True, random_state=0).split(Xc, yv):
    o0[te] = LogisticRegression(C=1e6, max_iter=10000).fit(Xc[tr], yv[tr]).predict_proba(Xc[te])[:, 1]
    o1[te] = LogisticRegression(C=1e6, max_iter=10000).fit(X1[tr], yv[tr]).predict_proba(X1[te])[:, 1]
r = np.random.default_rng(0); bd = []
for _ in range(2000):
    i = r.integers(0, len(yv), len(yv))
    if 0 < yv[i].sum() < len(i): bd.append(roc_auc_score(yv[i], o1[i]) - roc_auc_score(yv[i], o0[i]))
for nom, o in (("base", o0), ("base + score", o1)):
    pente = logit_fit(lgt(o)[:, None], yv.astype(float))[0][1]
    p(f"  {nom:<13} AUROC {auc_ic(yv, o)} | pente de calibration {pente:.2f} | attendu/observé {o.mean() / yv.mean():.2f}")
p(f"  différence d'AUROC {roc_auc_score(yv, o1) - roc_auc_score(yv, o0):+.3f} ({np.percentile(bd, 2.5):+.3f} à {np.percentile(bd, 97.5):+.3f})")

p("\n=== 6. Configurations de dérivations (mêmes ECG)")
for fmt, nom in (("12lead", "12 dérivations"), ("limb3", "I–III"), ("lead1", "I seul")):
    bloc(P, P["S_" + fmt] >= T1, f"{nom}, S ≥0.635"); p(f"    AUROC décès 30 j {auc_ic(P.y30, P['S_' + fmt])}")

p("\n=== 7. Précision diagnostique chez les opérés : cohorte pont (définitions de la validation diagnostique)")
ns = {}; exec(open(script_path("joindre_echo.py")).read().split('print("\\n=== principal')[0], ns)
X, lvef, pasp, rv_vis, as_pos, sept = (ns[k] for k in ("X", "lvef", "pasp", "rv_vis", "as_pos", "sept"))
x = X.loc[lvef.notna(), ["subject_id", "te"]].copy()
x["prim"] = ((lvef <= 50) | (pasp >= 40) | (rv_vis == 1) | as_pos | (sept >= 1.5))[lvef.notna()].fillna(False).astype(int).values
B = D[D.pont & D.qc_ok][["subject_id", "ecg_time", "S_12lead"]].sort_values("ecg_time")
B = pd.merge_asof(B, x.sort_values("te"), left_on="ecg_time", right_on="te", by="subject_id", direction="nearest", tolerance=pd.Timedelta(days=14)).dropna(subset=["te"])
fl = (B.S_12lead >= T2).values; yb = B.prim.values.astype(bool)
p(f"  n {len(B)} | atteinte structurelle {pc(int(yb.sum()), len(B))} | AUROC {auc_ic(yb.astype(int), B.S_12lead)}")
p(f"  seuil 0.453 : sensibilité {fl[yb].mean():.1%} | spécificité {(~fl[~yb]).mean():.1%} | probabilité prédite moyenne {B.S_12lead.mean():.1%} contre observée {yb.mean():.1%}")

p("\n=== 8. Recouvrement : analyse principale sans les patients de la validation diagnostique")
Q = P[~P.subject_id.isin(diag)]; bloc(Q, Q.S_12lead >= T1, "hors validation diagnostique")

p("\n=== 9. Sensibilités (analyse principale)")
Q = P[P.gap <= 7]; bloc(Q, Q.S_12lead >= T1, "ECG ≤ 7 j")
Q = P[P.urgence == "programmée"]; bloc(Q, Q.S_12lead >= T1, "admissions programmées seulement")
bloc(P, P.S_12lead >= T1, "RCRI variante B (tous codes du séjour index)", rcol="rcri_B")
for coh, nom in (("c34_ecg90", "ECG ≤ 90 j"), ("c4", "classe HCUP 4 seule")):
    if not (os.path.exists(f"results/chir_cohorte_v1_{coh}.csv") and os.path.exists(f"results/chir_covariables_{coh}.csv")):
        p(f"  {nom} : fichiers absents (lancer chir_rcri.py sur results/chir_cohorte_v1_{coh}.csv)"); continue
    c = pd.read_csv(f"results/chir_cohorte_v1_{coh}.csv", parse_dates=["chartdate", "ecg_time"])
    s = s12_pour(c[["subject_id", "ecg_time"]]).merge(S[["subject_id", "ecg_time", "qc_ok"]], on=["subject_id", "ecg_time"], how="left")
    s["ok"] = s.ok12 & s.qc_ok.fillna(True).astype(bool)    # hors fichier de scores : contrôle 12 dérivations seulement
    Q = issues(c.merge(s[s.ok], on=["subject_id", "ecg_time"]).merge(pat, on="subject_id", how="left")).merge(pd.read_csv(f"results/chir_covariables_{coh}.csv").drop(columns=["hadm_id", "chartdate"]), on="subject_id")
    bloc(Q, Q.S_12lead >= T1, nom)
p("\nécrit : results/chir_resultats_c34.txt (agrégats seulement). Terminé."); OUT.close()
