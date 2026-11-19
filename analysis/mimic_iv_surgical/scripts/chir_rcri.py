"""
Cohorte chirurgicale MIMIC-IV — point 3 du protocole : RCRI + covariables (âge, sexe, urgence, catégorie d'opération).
ÉTAPE 1 : aucun score ECG lu, aucun décès lu. Fréquences agrégées seulement ; le fichier patient reste sur la VM.
Usage : python3 scripts/chir_rcri.py results/chir_cohorte_v1_c34.csv 3,4
Écrit results/chir_rcri_<tag>.txt et results/chir_covariables_<tag>.csv

Règle commune : un diagnostic compte s'il vient d'un séjour TERMINÉ AVANT la date d'opération (tous codes),
ou du séjour index mais seulement pour les codes chroniques / « antécédent de » (MIMIC n'a pas d'indicateur
« présent à l'admission » : un IDM, une IC aiguë ou un AVC codés au séjour index peuvent être postopératoires).
Variante B (pour comparer à Harris) : tous les codes du séjour index comptent.
"""
from study_config import required_dir, workspace_dir, script_path
import os, re, sys, glob, csv
import pandas as pd
W = str(workspace_dir()); M = str(required_dir("HOOPCARE_DATA_ROOT") / "mimic-iv/v3.1/hosp") + "/"; H = str(required_dir("HOOPCARE_HCUP_DIR"))
COH = sys.argv[1] if len(sys.argv) > 1 else "results/chir_cohorte_v1_c34.csv"
CLS = {int(x) for x in (sys.argv[2] if len(sys.argv) > 2 else "3,4").split(",")}
tag = re.sub(r"^chir_cohorte_v1_?|\.csv$", "", os.path.basename(COH)) or "v1"
OUT = open(os.path.join(W, "results", f"chir_rcri_{tag}.txt"), "w")
def p(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); OUT.write(s + "\n")
def n_(k): return "<10" if 0 < k < 10 else f"{k:,}".replace(",", " ")
cl = lambda s: re.sub(r"[^0-9A-Za-z]", "", str(s)).upper()
def lire_hcup(motif):
    f = sorted(glob.glob(os.path.join(H, motif)))[0]
    rows = list(csv.reader(open(f, encoding="latin-1")))
    i = next(k for k, r in enumerate(rows) if r and ("CODE" in cl(r[0]) or cl(r[0]).startswith("ICD")))
    return [[c.strip().strip("'\"") for c in r] for r in rows[i + 1:] if r and r[0].strip()]

# ---------- tables HCUP : classe (bloc ou non) et catégorie d'opération
pclass = {(cl(r[0]), 10): int(r[2]) for r in lire_hcup("PClassR_v*.csv")}
for r in lire_hcup("pc20*.csv"):
    c = next((int(x) for x in r[1:] if x in ("1", "2", "3", "4")), None)
    if c: pclass[(cl(r[0]), 9)] = c
ccsr = {cl(r[0]): cl(r[2]) for r in lire_hcup("PRCCSR*.csv")}
ccs9 = {cl(r[0]): int(cl(r[1])) for r in lire_hcup("prref*.csv") if cl(r[1]).isdigit()}
def categorie(code, v):
    if v == 10:
        k = ccsr.get(code, "")
        if k in ("MST013", "MST016") or k[:3] in ("CNS", "PNS"): return "neuro/rachis"
        return {"MST": "orthopédie", "GIS": "digestif", "HEP": "digestif", "CAR": "vasculaire", "RES": "thoracique",
                "URN": "uro/gynéco", "MRS": "uro/gynéco", "FRS": "uro/gynéco", "PGN": "uro/gynéco", "ENT": "tête-cou/endocrine",
                "EYP": "tête-cou/endocrine", "ENP": "tête-cou/endocrine", "SKB": "peau/sein/lymph", "LYM": "peau/sein/lymph"}.get(k[:3], "autre")
    c = ccs9.get(code, 0)
    if 1 <= c <= 9 or c == 158: return "neuro/rachis"
    for a, b, g in [(10, 33, "tête-cou/endocrine"), (34, 42, "thoracique"), (43, 63, "vasculaire"), (64, 67, "peau/sein/lymph"), (68, 99, "digestif"),
                    (100, 141, "uro/gynéco"), (142, 164, "orthopédie"), (165, 175, "peau/sein/lymph")]:
        if a <= c <= b: return g
    return "autre"

# ---------- RCRI 1 : chirurgie à haut risque (intrapéritonéale, intrathoracique, vasculaire sus-inguinale), procédure de bloc (classe 3–4)
HR9 = ("415", "424", "425", "426", "4319", "433", "434", "435", "436", "437", "438", "439", "44", "45", "46", "47", "484", "485", "486",
       "50", "51", "52", "541", "542", "544", "545", "546", "547", "5492", "5493", "5494", "5495", "5499", "537", "538",
       "65", "66", "683", "684", "686", "689", "576", "577",
       "32", "3328", "333", "334", "335", "336", "339", "3402", "3403", "3409", "341", "3421", "343", "345", "346", "348", "078",
       "3804", "3805", "3806", "3814", "3815", "3816", "3824", "3825", "3826", "3834", "3835", "3836", "3844", "3845", "3846",
       "3864", "3865", "3866", "3884", "3885", "3886", "3924", "3925", "3926")
HR9_NON = ("5410", "5411", "5412", "5419", "662", "4311", "4513", "4514", "4516", "4542", "4543")   # incisions de paroi, ligature tubaire endoscopique, endoscopies
HR10 = {"0D": "023456789ABCDEFGHJKLMNPSTUVW", "0F": None, "07": "MP", "0B": "23456789BCDFGHJKLMNPT", "0W": "9BCGJP",
        "0U": "012456789C", "04": "0123456789ABCDEFHJ", "02": "WX"}
def haut_risque(code, v):
    if pclass.get((code, v)) not in (3, 4): return False
    if v == 9: return code.startswith(HR9) and not code.startswith(HR9_NON)
    if len(code) < 7 or code[4] not in "04": return False                  # abord ouvert ou cœlio/thoracoscopique seulement
    if code[:2] == "0T": return code[2] == "T" and code[3] == "B"           # cystectomie
    if code[:2] not in HR10: return False
    bp = HR10[code[:2]]; return bp is None or code[3] in bp

# ---------- RCRI 2–5 : listes de diagnostics (préfixes, codes sans point)
D = {
 "cardiopathie_ischemique": {9: (("410", "411", "412", "413", "414", "V4581", "V4582"), ("412", "413", "414", "V4581", "V4582")),
                             10: (("I20", "I21", "I22", "I23", "I24", "I25", "Z951", "Z955"), ("I20", "I25", "Z951", "Z955"))},
 "insuffisance_cardiaque":  {9: (("428", "39891", "40201", "40211", "40291", "40401", "40403", "40411", "40413", "40491", "40493"), ("42822", "42832", "42842")),
                             10: (("I50", "I110", "I130", "I132", "I0981"), ("I5022", "I5032", "I5042", "I50812"))},
 "avc_ait":                 {9: (("430", "431", "432", "43301", "43311", "43321", "43331", "43381", "43391", "43401", "43411", "43491", "435", "436", "438", "V1254"), ("438", "V1254")),
                             10: (("I60", "I61", "I62", "I63", "I64", "G450", "G451", "G452", "G453", "G458", "G459", "G46", "I69", "Z8673"), ("I69", "Z8673"))},
}
DIAB = {9: ("250",), 10: ("E08", "E09", "E10", "E11", "E13")}
INSC = lambda c, v: c.startswith(("V5867",)) or (c[:3] == "250" and len(c) == 5 and c[4] in "13") if v == 9 else c.startswith(("Z794", "E10"))

if __name__ == "__main__":
    coh = pd.read_csv(os.path.join(W, COH), parse_dates=["chartdate"]); S = set(coh.subject_id)
    p(f"cohorte : {COH} ({n_(len(coh))} patients) | procédures de bloc = classes {sorted(CLS)}")
    pat = pd.read_csv(M + "patients.csv.gz", usecols=["subject_id", "gender", "anchor_age", "anchor_year"])
    adm = pd.read_csv(M + "admissions.csv.gz", usecols=["subject_id", "hadm_id", "admittime", "dischtime", "admission_type"], parse_dates=["admittime", "dischtime"])
    adm = adm[adm.subject_id.isin(S)]
    coh = coh.merge(pat, on="subject_id", how="left").merge(adm[["hadm_id", "admission_type"]], on="hadm_id", how="left")
    coh["age"] = coh.anchor_age + (coh.chartdate.dt.year - coh.anchor_year); coh["sexe_h"] = (coh.gender == "M").astype(int)
    coh["urgence"] = coh.admission_type.map(lambda t: "programmée" if t in ("ELECTIVE", "SURGICAL SAME DAY ADMISSION") else ("urgente" if t == "URGENT" else "en urgence/non programmée"))

    # opération index : codes du jour de l'opération
    pr = pd.read_csv(M + "procedures_icd.csv.gz", usecols=["subject_id", "hadm_id", "seq_num", "chartdate", "icd_code", "icd_version"], parse_dates=["chartdate"], dtype={"icd_code": str})
    pr = pr[pr.subject_id.isin(S)]; pr["icd_code"] = pr.icd_code.map(cl)
    pr = pr.merge(coh[["subject_id", "chartdate"]], on=["subject_id", "chartdate"])
    pr["hr"] = [haut_risque(c, v) for c, v in zip(pr.icd_code, pr.icd_version)]
    pr["bloc"] = [pclass.get((c, v)) in CLS for c, v in zip(pr.icd_code, pr.icd_version)]
    coh = coh.merge(pr.groupby("subject_id").hr.any().rename("haut_risque").reset_index(), on="subject_id", how="left")
    princ = pr[pr.bloc].sort_values("seq_num").groupby("subject_id").head(1)
    princ["categorie"] = [categorie(c, v) for c, v in zip(princ.icd_code, princ.icd_version)]
    coh = coh.merge(princ[["subject_id", "categorie"]], on="subject_id", how="left")

    # diagnostics : séjours antérieurs (tous codes) + séjour index (codes chroniques)
    dx = pd.read_csv(M + "diagnoses_icd.csv.gz", usecols=["subject_id", "hadm_id", "icd_code", "icd_version"], dtype={"icd_code": str})
    dx = dx[dx.subject_id.isin(S)]; dx["icd_code"] = dx.icd_code.map(cl)
    dx = dx.merge(adm[["hadm_id", "dischtime"]], on="hadm_id", how="left").merge(coh[["subject_id", "hadm_id", "chartdate"]].rename(columns={"hadm_id": "hadm_idx"}), on="subject_id")
    dx["index"] = dx.hadm_id == dx.hadm_idx; dx["avant"] = ~dx["index"] & (dx.dischtime < dx.chartdate)
    dx = dx[dx["index"] | dx["avant"]]
    for k, d in D.items():
        tous = [c.startswith(d[v][0]) for c, v in zip(dx.icd_code, dx.icd_version)]
        chron = [c.startswith(d[v][1]) for c, v in zip(dx.icd_code, dx.icd_version)]
        a = set(dx[pd.Series(tous, index=dx.index) & (dx.avant | pd.Series(chron, index=dx.index))].subject_id)
        b = set(dx[pd.Series(tous, index=dx.index)].subject_id)
        coh[k] = coh.subject_id.isin(a).astype(int); coh[k + "_B"] = coh.subject_id.isin(b).astype(int)
    diab = set(dx[[c.startswith(DIAB[v]) for c, v in zip(dx.icd_code, dx.icd_version)]].subject_id)
    insc = set(dx[[INSC(c, v) for c, v in zip(dx.icd_code, dx.icd_version)]].subject_id)

    # insuline prescrite avant la date d'opération
    rx = []
    for ch in pd.read_csv(M + "prescriptions.csv.gz", usecols=["subject_id", "starttime", "drug"], parse_dates=["starttime"], chunksize=5_000_000):
        ch = ch[ch.subject_id.isin(S) & ch.drug.astype(str).str.contains("insulin", case=False)]; rx.append(ch)
    rx = pd.concat(rx).merge(coh[["subject_id", "chartdate"]], on="subject_id"); rx = set(rx[rx.starttime < rx.chartdate].subject_id)
    coh["diabete_insuline"] = coh.subject_id.isin((diab & rx) | insc).astype(int)
    coh["diabete_insuline_B"] = coh.subject_id.isin(rx | insc).astype(int)

    # créatinine : dernière valeur sanguine de J-30 à la veille
    dl = pd.read_csv(M + "d_labitems.csv.gz")
    it = set(dl[(dl.label.astype(str).str.strip().str.lower() == "creatinine") & (dl.fluid.astype(str).str.lower() == "blood")].itemid)
    p(f"créatinine : itemid {sorted(it)}")
    lab = []
    for ch in pd.read_csv(M + "labevents.csv.gz", usecols=["subject_id", "itemid", "charttime", "valuenum"], parse_dates=["charttime"], chunksize=10_000_000):
        lab.append(ch[ch.itemid.isin(it) & ch.subject_id.isin(S)].dropna(subset=["valuenum"]))
    lab = pd.concat(lab).merge(coh[["subject_id", "chartdate"]], on="subject_id")
    lab = lab[(lab.charttime < lab.chartdate) & (lab.charttime >= lab.chartdate - pd.Timedelta(days=30))].sort_values("charttime").groupby("subject_id").tail(1)
    coh = coh.merge(lab[["subject_id", "valuenum"]].rename(columns={"valuenum": "creat_preop"}), on="subject_id", how="left")
    coh["creatinine_sup2"] = (coh.creat_preop > 2).astype(int)

    coh["haut_risque"] = coh.haut_risque.fillna(False).astype(int)
    comp = ["haut_risque", "cardiopathie_ischemique", "insuffisance_cardiaque", "avc_ait", "diabete_insuline", "creatinine_sup2"]
    coh["rcri"] = coh[comp].sum(axis=1); coh["rcri_B"] = coh[[c + ("_B" if c + "_B" in coh else "") for c in comp]].sum(axis=1)
    cat = lambda s: s.clip(upper=3).map({0: "0", 1: "1", 2: "2", 3: "≥3"})

    harris = {"haut_risque": 36.7, "cardiopathie_ischemique": 16.0, "insuffisance_cardiaque": 10.8, "avc_ait": 6.6, "diabete_insuline": 26.0, "creatinine_sup2": 13.3}
    p(f"\nâge médian {coh.age.median():.0f} ans | hommes {coh.sexe_h.mean():.1%} | créatinine préop. disponible {coh.creat_preop.notna().mean():.1%}")
    p("\ncomposante RCRI                 règle retenue   variante B (tous codes du séjour index)   Harris 2025")
    for c in comp:
        b = coh[c + "_B"].mean() if c + "_B" in coh else coh[c].mean()
        p(f"  {c:<28} {coh[c].mean():>7.1%}          {b:>7.1%}                                   {harris[c]:.1f} %")
    p("\nRCRI (règle retenue) :", " | ".join(f"{k} {v:.1%}" for k, v in cat(coh.rcri).value_counts(normalize=True).sort_index().items()))
    p("RCRI (variante B)    :", " | ".join(f"{k} {v:.1%}" for k, v in cat(coh.rcri_B).value_counts(normalize=True).sort_index().items()))
    p("\nurgence :", " | ".join(f"{k} {v:.1%}" for k, v in coh.urgence.value_counts(normalize=True).items()))
    p("catégorie d'opération :", " | ".join(f"{k} {v:.1%}" for k, v in coh.categorie.value_counts(normalize=True, dropna=False).items()))
    dp = pd.read_csv(M + "d_icd_procedures.csv.gz", dtype={"icd_code": str}); dp["icd_code"] = dp.icd_code.map(cl)
    t = pr[pr.hr].merge(dp, on=["icd_code", "icd_version"], how="left").groupby(["icd_version", "icd_code", "long_title"]).subject_id.nunique().sort_values(ascending=False)
    p("\n20 codes « haut risque » les plus fréquents (contrôle) :")
    for (v, c, tt), k in t.head(20).items(): p(f"  {n_(k):>6}  ICD-{v} {c:<8} {str(tt)[:70]}")
    cols = ["subject_id", "hadm_id", "chartdate", "age", "sexe_h", "admission_type", "urgence", "categorie", "creat_preop"] + comp + [c + "_B" for c in comp if c + "_B" in coh] + ["rcri", "rcri_B"]
    coh[cols].to_csv(os.path.join(W, "results", f"chir_covariables_{tag}.csv"), index=False)
    p(f"\nécrit : results/chir_covariables_{tag}.csv (covariables seulement : ni score, ni décès). Terminé."); OUT.close()
