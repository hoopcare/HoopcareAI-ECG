"""
Cohorte chirurgicale MIMIC-IV — point 1 du protocole : opérations éligibles définies comme Harris et al. (HCUP Procedure Classes).
ÉTAPE 1 : aucun score ECG lu, aucun croisement événements × score. Effectifs et total des décès seulement.
Fichiers HCUP attendus dans HOOPCARE_HCUP_DIR (ceux qui manquent sont signalés, avec une règle de secours) :
  PClassR_v*.csv            Procedure Classes Refined, ICD-10-PCS        (obligatoire)
  pc*.csv / *ProcClass*     Procedure Classes, ICD-9-CM                  (sinon : ICD-9 = règle provisoire)
  PRCCSR*.csv               CCSR procédures ICD-10-PCS                   (sinon : cardiaque = système « 2 » de l'ICD-10-PCS)
  *prref*.csv               CCS procédures ICD-9-CM                      (sinon : cardiaque = chapitres 35–37 et 39.61)
Usage : python3 analysis/mimic_iv_surgical/scripts/chir_codes.py
Écrit results/chir_codes.txt et results/chir_cohorte_v1.csv (identifiants + dates, SANS score ni événement ; reste sur la VM).
"""
from study_config import required_dir, workspace_dir, script_path
import os, re, glob, csv, collections
import pandas as pd
H = str(required_dir("HOOPCARE_HCUP_DIR")); W = str(workspace_dir()); M = str(required_dir("HOOPCARE_DATA_ROOT") / "mimic-iv/v3.1/hosp") + "/"
OUT = open(os.path.join(W, "results", "chir_codes.txt"), "w")
def p(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); OUT.write(s + "\n")
def n_(k): return "<10" if 0 < k < 10 else f"{k:,}".replace(",", " ")
cl = lambda s: re.sub(r"[^0-9A-Za-z]", "", str(s)).upper()

def lire_hcup(motifs):
    f = sorted(x for m in motifs for x in glob.glob(os.path.join(H, m)))
    if not f: return None, None
    rows = list(csv.reader(open(f[0], encoding="latin-1")))
    i = next(k for k, r in enumerate(rows) if r and ("CODE" in cl(r[0]) or cl(r[0]).startswith("ICD")))
    return f[0], [[c.strip().strip("'\"") for c in r] for r in rows[i + 1:] if r and r[0].strip()]
# ---------- classes de procédures
pclass = {}
f10, R = lire_hcup(["PClassR_v*.csv"])
if not f10: p("INTROUVABLE : HOOPCARE_HCUP_DIR/PClassR_v*.csv"); raise SystemExit(1)
for r in R: pclass[(cl(r[0]), 10)] = int(r[2])
p(f"ICD-10-PCS : {os.path.basename(f10)} -> {n_(sum(1 for k in pclass if k[1] == 10))} codes")
f9, R = lire_hcup(["pc*.csv", "*ProcClass*.csv", "*procclass*.csv", "*PC20*.csv"])
if f9:
    for r in R:
        c = next((int(x) for x in r[1:] if x in ("1", "2", "3", "4")), None)
        if c: pclass[(cl(r[0]), 9)] = c
    p(f"ICD-9-CM : {os.path.basename(f9)} -> {n_(sum(1 for k in pclass if k[1] == 9))} codes")
else: p("ICD-9-CM : fichier Procedure Classes ABSENT -> règle de secours (chapitres 01–86, hors endoscopies/gestes au lit) ; à remplacer")
# ---------- cardiaque
CARD10 = {"CAR001", "CAR002", "CAR003", "CAR004", "CAR005", "CAR009", "CAR013", "CAR017", "CAR018", "CAR019", "CAR022", "CAR023", "CAR026", "CAR027"}
fcc, R = lire_hcup(["PRCCSR*.csv", "*prccsr*.csv"]); ccsr = {cl(r[0]): cl(r[2]) for r in R} if fcc else {}
if fcc: p(f"CCSR ICD-10-PCS : {os.path.basename(fcc)} -> cardiaque = {', '.join(sorted(CARD10))} (cœur : biopsie, conduction, pontages, angioplastie coronaire, autres coronaires, auricule, pontages cœur/gros vaisseaux, péricarde, greffe, septum, valves, stimulateurs/défibrillateurs, assistance)")
else: p("CCSR ICD-10-PCS ABSENT -> cardiaque = système « 2 » (cœur et gros vaisseaux)")
fcs, R9 = lire_hcup(["*prref*.csv", "*PRREF*.csv"])
ccs9 = {cl(r[0]): int(cl(r[1])) for r in R9 if cl(r[1]).isdigit()} if fcs else {}
if fcs: p(f"CCS ICD-9 : {os.path.basename(fcs)} -> cardiaque = catégories CCS 43–50 (valves, pontages, angioplastie, thrombolyse, cathétérisme, stimulateur, autre chirurgie cardiaque, CEC)")
def cardiaque(code, v):
    if v == 10: return ccsr.get(code) in CARD10 if ccsr else (len(code) > 1 and code[0] == "0" and code[1] == "2")
    if ccs9: return 43 <= ccs9.get(code, 0) <= 50
    return code[:2] in ("35", "36", "37") or code.startswith("3961")
def majeure(code, v, classes):
    if (code, v) in pclass: return pclass[(code, v)] in classes
    if v == 9 and not f9:
        c2 = int(code[:2]) if code[:2].isdigit() else -1
        return 1 <= c2 <= 86 and not re.match(r"^(4513|4523|4524|4525|4516|4442|3324|3327|3322|0331|8622|8628|3893|3897|3891|3899|3895|5491|3491|3404|4311|5185)", code)
    return False

# ---------- données MIMIC
pat = pd.read_csv(M + "patients.csv.gz", usecols=["subject_id", "anchor_age", "anchor_year", "dod"], parse_dates=["dod"])
adm = pd.read_csv(M + "admissions.csv.gz", usecols=["hadm_id", "admission_type"])
proc = pd.read_csv(M + "procedures_icd.csv.gz", usecols=["subject_id", "hadm_id", "chartdate", "icd_code", "icd_version"], parse_dates=["chartdate"], dtype={"icd_code": str})
dproc = pd.read_csv(M + "d_icd_procedures.csv.gz", dtype={"icd_code": str}); dproc["icd_code"] = dproc.icd_code.map(cl)
proc["icd_code"] = proc.icd_code.map(cl); proc = proc.merge(pat[["subject_id", "anchor_age", "anchor_year"]], on="subject_id")
proc = proc[proc.anchor_age + (proc.chartdate.dt.year - proc.anchor_year) >= 18]
ecg = pd.read_csv(str(required_dir("HOOPCARE_DATA_ROOT") / "mimic-iv-ecg/v1.0/record_list.csv"), usecols=["subject_id", "ecg_time"], parse_dates=["ecg_time"]).dropna().sort_values("ecg_time")
couv = proc.icd_code.map(str).to_frame().assign(v=proc.icd_version).apply(lambda r: (r.icd_code, r.v) in pclass, axis=1)
p(f"\nprocédures adultes : {n_(len(proc))} | codes couverts par les Procedure Classes : ICD-10 {couv[proc.icd_version == 10].mean():.1%} | ICD-9 {couv[proc.icd_version == 9].mean():.1%}")
ech_f = next((f for f in glob.glob(str(required_dir("HOOPCARE_DATA_ROOT") / "**/structured-measurement.csv.gz"), recursive=False) + glob.glob(str(required_dir("HOOPCARE_DATA_ROOT") / "*/*/structured-measurement.csv.gz")) + glob.glob(str(required_dir("HOOPCARE_DATA_ROOT") / "*/*/*/structured-measurement.csv.gz"))), None)
EF = ("lvef",)   # même définition que la validation diagnostique (joindre_echo.py) : mesure « lvef » d'une ETT
ech = pd.read_csv(ech_f, usecols=["subject_id", "measurement_datetime", "test_type", "measurement", "result"], parse_dates=["measurement_datetime"]).dropna(subset=["measurement_datetime"])
p("écho : types d'examen :", " | ".join(f"{k} {n_(v)}" for k, v in ech.test_type.value_counts().items()), "-> on garde tte (transthoracique)")
ech = ech[ech.test_type.astype(str).str.lower() == "tte"]
efm = ech.measurement.isin(EF) & pd.to_numeric(ech.result, errors="coerce").between(5, 90)
ech_ef = ech[efm][["subject_id", "measurement_datetime"]].drop_duplicates()
ech = ech[["subject_id", "measurement_datetime"]].drop_duplicates()
p(f"écho : {ech_f} ({n_(ech.subject_id.nunique())} patients, dont {n_(ech_ef.subject_id.nunique())} avec une FEVG « lvef » chiffrée, comme la validation diagnostique)")
diag = set(pd.read_csv(os.path.join(W, "results/paires_principales.csv")).query("cible.str.contains('FEVG')", engine="python").subject_id.astype(int)) if os.path.exists(os.path.join(W, "results/paires_principales.csv")) else set()

def cohorte(classes, nom):
    q = proc.copy(); q["maj"] = [majeure(c, v, classes) for c, v in zip(q.icd_code, q.icd_version)]; q = q[q.maj]
    q["card"] = [cardiaque(c, v) for c, v in zip(q.icd_code, q.icd_version)]
    ops = q.groupby(["subject_id", "hadm_id", "chartdate"]).agg(card=("card", "any")).reset_index().sort_values("chartdate")
    first = ops.groupby("subject_id").head(1)
    nc = first[~first.card]
    l = nc.sort_values("chartdate")
    m = pd.merge_asof(l, ecg, left_on="chartdate", right_on="ecg_time", by="subject_id", direction="backward", allow_exact_matches=False).dropna(subset=["ecg_time"])
    m["gap"] = (m.chartdate - m.ecg_time.dt.normalize()).dt.days; idx = m[(m.gap >= 1) & (m.gap <= 30)].copy()
    e = idx.merge(ech, on="subject_id", how="left"); g = (e.chartdate - e.measurement_datetime.dt.normalize()).dt.days
    idx["echo365"] = idx.subject_id.isin(e[(g >= 0) & (g <= 365)].subject_id)
    b = idx.merge(ech_ef, on="subject_id"); gb = (b.measurement_datetime - b.ecg_time).dt.total_seconds().abs() / 86400
    pont = set(b[gb <= 14].subject_id); prim = idx[~idx.echo365].join(pat.set_index("subject_id").dod, on="subject_id")
    j = (prim.dod - prim.chartdate).dt.days
    p(f"\n=== {nom}")
    p(f"  adultes avec ≥ 1 chirurgie majeure : {n_(len(first))} | 1re chirurgie cardiaque (exclus, comme Harris) : {n_(int(first.card.sum()))}")
    p(f"  1re chirurgie non cardiaque + ECG J-30–J-1 : {n_(len(idx))} (écart médian {idx.gap.median():.0f} j) | sans limite de 30 j (comme Harris, ECG ≥ 1 j avant) : {n_(len(m[m.gap >= 1]))}")
    p(f"  COHORTE PRINCIPALE (pas d'ETT dans l'année) : {n_(len(prim))} | décès totaux 30 j : {n_(int(((j >= 0) & (j <= 30)).sum()))} ({((j >= 0) & (j <= 30)).mean():.1%}) | 90 j : {n_(int(((j >= 0) & (j <= 90)).sum()))}")
    p(f"  COHORTE PONT (écho avec FEVG ≤ 14 j de l'ECG) : {n_(len(pont))} | recouvrement validation diagnostique : principale {n_(int(prim.subject_id.isin(diag).sum()))}, pont {n_(len(pont & diag))}")
    ty = prim.merge(adm, on="hadm_id", how="left").admission_type.value_counts(normalize=True)
    p("  admissions :", " | ".join(f"{k} {v:.0%}" for k, v in ty.head(5).items()))
    top = q[q.subject_id.isin(prim.subject_id) & ~q.card].merge(prim[["subject_id", "chartdate"]], on=["subject_id", "chartdate"]).merge(dproc, on=["icd_code", "icd_version"], how="left")
    p("  25 codes les plus fréquents dans la cohorte principale (patients) :")
    for (c, v, t), k in top.groupby(["icd_code", "icd_version", "long_title"], dropna=False).subject_id.nunique().sort_values(ascending=False).head(25).items(): p(f"    {n_(k):>7}  ICD-{v} {c:<8} {str(t)[:75]}")
    idx["pont"] = idx.subject_id.isin(pont)
    i90 = m[(m.gap >= 1) & (m.gap <= 90)].copy()                     # sensibilité du protocole : fenêtre ECG de 90 j
    e9 = i90[["subject_id", "chartdate"]].merge(ech, on="subject_id"); g9 = (e9.chartdate - e9.measurement_datetime.dt.normalize()).dt.days
    i90 = i90[~i90.subject_id.isin(e9[(g9 >= 0) & (g9 <= 365)].subject_id)]
    p(f"  sensibilité fenêtre ECG 90 j : cohorte principale {n_(len(i90))}")
    return prim, idx, i90
for cls, tag, nom in [({3, 4}, "c34", "Définition proposée : classes 3–4 = « procédure de bloc » HCUP (majeure diagnostique ou thérapeutique)"), ({4}, "c4", "Sensibilité : classe 4 seule « majeure thérapeutique »")]:
    prim, idx, i90 = cohorte(cls, nom)
    i90[["subject_id", "hadm_id", "chartdate", "ecg_time", "gap"]].to_csv(os.path.join(W, "results", f"chir_cohorte_v1_{tag}_ecg90.csv"), index=False)
    prim[["subject_id", "hadm_id", "chartdate", "ecg_time", "gap"]].to_csv(os.path.join(W, "results", f"chir_cohorte_v1_{tag}.csv"), index=False)
    idx[["subject_id", "hadm_id", "chartdate", "ecg_time", "gap", "echo365", "pont"]].to_csv(os.path.join(W, "results", f"chir_index_v1_{tag}.csv"), index=False)
    p(f"  contrôle : principale = {n_(int((~idx.echo365).sum()))} | pont = {n_(int(idx.pont.sum()))} (doivent égaler les lignes COHORTE ci-dessus)")
p("\nécrit : results/chir_cohorte_v1_*.csv et chir_index_v1_*.csv (identifiants, dates et indicateurs de cohorte seulement). Aucun score lu. Terminé."); OUT.close()
