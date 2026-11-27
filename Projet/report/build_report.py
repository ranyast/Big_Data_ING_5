"""Genere report/rapport.pdf (4 pages max) avec reportlab.
Usage : python report/build_report.py   (depuis Projet/, apres src/04_figures.py)
"""
import copy
import io
import os

import matplotlib
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

fonts = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
pdfmetrics.registerFont(TTFont("DV", os.path.join(fonts, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DV-B", os.path.join(fonts, "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DV-I", os.path.join(fonts, "DejaVuSans-Oblique.ttf")))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV-I", boldItalic="DV-B")

INK, MUTED, BLUE = colors.HexColor("#0b0b0b"), colors.HexColor("#52514e"), colors.HexColor("#2a78d6")
body = ParagraphStyle("body", fontName="DV", fontSize=9.2, leading=12.4, textColor=INK, spaceAfter=4)
h1 = ParagraphStyle("h1", parent=body, fontName="DV-B", fontSize=14, leading=17, spaceAfter=2)
h2 = ParagraphStyle("h2", parent=body, fontName="DV-B", fontSize=11, leading=14, textColor=BLUE,
                    spaceBefore=8, spaceAfter=3, keepWithNext=1)
small = ParagraphStyle("small", parent=body, fontSize=8, leading=10, textColor=MUTED)
cell = ParagraphStyle("cell", parent=body, fontSize=8.4, leading=10.4, spaceAfter=0)
cellb = ParagraphStyle("cellb", parent=cell, fontName="DV-B")
TODO = '<font color="#b00020"><b>[À COMPLÉTER]</b></font>'

# Mesures DuckDB sur Onyxia (src/06_benchmark_duckdb.py, 27/11/2026, capture 07)
DUCKDB_X1 = "0,24 s"
DUCKDB_X100 = "3,39 s"
DUCKDB_TEXT = ("0,24 s à ×1 et 3,39 s à ×100, soit le même ordre de grandeur que pandas et environ 12 fois plus "
               "rapide que Spark <i>local[*]</i> à ×100 (même service Onyxia, mêmes données). Comme pandas, DuckDB "
               "tourne sur une seule machine ; il aurait été un excellent choix à ce volume, mais ne répond pas à "
               "l'objectif de traitement distribué du cours.")

# Captures du dossier evidence/ : (fichier, description). Celles qui existent sont incluses en annexe.
EVIDENCE = [
    ("01_upload_raw_s3.png", "Dépôt du CSV brut dans bronze/ (aws s3 cp)"),
    ("02_spark_bronze_to_silver.png", "Spark 01_bronze_to_silver.py : compteurs de qualité, écriture silver"),
    ("03_spark_silver_to_gold.png", "Spark 02_silver_to_gold.py : quartiles et corrélations"),
    ("04_verification_pandas.png", "Vérification indépendante pandas (mêmes valeurs)"),
    ("05_bucket_contenu_1.png", "Contenu du bucket (1/2) : bronze/, gold/"),
    ("05_bucket_contenu_2.png", "Contenu du bucket (2/2) : gold/, silver/ (suite de la capture 1/2)"),
    ("06_benchmark_pandas_spark.png", "Mesures pandas / Spark à ×1 et ×100"),
    ("07_benchmark_duckdb.png", "Mesures DuckDB à ×1 et ×100"),
    ("08_k8s_job_upload.png", "Job Kubernetes d'upload du brut (kubectl)"),
]
EVIDENCE_DIR = "evidence"
PX_TO_CM = 17.2 / 1640  # meme echelle pour toutes les captures : texte de meme taille partout


def table(rows, widths, header=True):
    data = [[Paragraph(str(c), cellb if (header and i == 0) else cell) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1 if header else 0)
    t.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0 if header else -1), 0.6, MUTED),
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#e4e3df")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6),
        ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def P(text, style=body):
    return Paragraph(text, style)


s = []
s += [P("Fréquence des sessions et vitesse de course : les plus rapides sont-ils les plus assidus ?", h1),
      P(f"Écosystème Big Data II — Groupe {TODO} — NOM1 Prénom1, NOM2 Prénom2 — "
        f"Dépôt Git : {TODO}", small)]

s += [P("1. Problématique et dataset", h2),
      P("<b>Question.</b> Les coureurs les plus rapides sont-ils nécessairement les plus assidus ? Pour chaque "
        "athlète, nous mesurons la <i>fréquence</i> (nombre de sessions sur l'année) et la <i>vitesse</i> "
        "(km totaux / heures totales, donc pondérée par la durée), puis la corrélation (Pearson, Spearman), la "
        "vitesse par quartile de fréquence et le recouvrement entre « les plus rapides » et « les plus assidus »."),
      P(f"<b>Dataset</b> : <i>running_data_france_final.csv</i>, sessions de course d'athlètes français en 2020. "
        f"Source / URL : {TODO} (Kaggle) ; licence : {TODO} ; téléchargé le {TODO}. Le fichier d'origine dépassait "
        f"5 Mo : il a été réduit ({TODO} méthode exacte). <b>Taille finale : 4,48 Mo</b>, 65 880 lignes, 9 colonnes, "
        "180 athlètes × 366 jours (une ligne par athlète et par jour, y compris les jours sans course).")]
s += [table([
    ["Colonne", "Type", "Rôle / remarque"],
    ["Unnamed: 0", "int", "index pandas parasite, supprimé en silver"],
    ["datetime, athlete", "date, int", "clé (athlète, jour) : aucun doublon"],
    ["distance (km), duration (min)", "double", "0 / 0 = jour de repos ; vitesse = distance / (duration/60)"],
    ["gender, age_group", "string", "M/F ; 18-34, 35-54, 55+ (constants par athlète)"],
    ["country, major", "string", "country = France partout ; major = liste « MARATHON AAAA » séparée par virgules "
                                  "→ converti en nombre de majors"],
], [4.4, 1.7, 11.4])]

s += [P("2. Pipeline, choix techniques et alternatives", h2),
      Image("report/figures/fig2_pipeline.png", width=17.2 * cm, height=17.2 * cm * 0.28),
      P("<b>Architecture médaillon (lab 05) sur le S3 Onyxia (lab 03).</b> <i>Bronze</i> : le CSV est déposé tel quel "
        "(<font face='DV-I'>aws s3 cp</font>, ou Job k8s <i>k8s/job-upload-raw.yaml</i>) ; il reste la source de vérité "
        "rejouable. <i>Silver</i> : PySpark (labs 06-07) type, nettoie et marque les anomalies sans rien supprimer de "
        "ce qui est exploitable, sortie Parquet. <i>Gold</i> : SparkSQL, une ligne par athlète + quartiles + "
        "corrélations (Parquet). <i>Vérification</i> : pandas recalcule les résultats directement depuis le CSV brut, "
        "sans Spark ni silver, ce qui donne une preuve indépendante."),
      P("<b>Choix de Spark.</b> Parquet est colonnaire et typé (au contraire du CSV) et Spark lit/écrit S3 via S3A avec "
        "les identifiants temporaires d'Onyxia. Nous avons <b>mesuré</b> l'alternative pandas seul <b>sur Onyxia</b> "
        "(service vscode-pyspark, 4 CPU / 4 Go ; médiane de 3 essais, même agrégation ; le dataset ×100 réplique "
        "le CSV avec des identifiants d'athlètes décalés ; Spark en mode <i>local[*]</i>, démarrage de la session : "
        "7,4 s) :")]
s += [table([
    ["Volume", "Lignes", "CSV", "pandas", "Spark local[*]", "DuckDB"],
    ["×1 (réel)", "65 880", "4,4 Mo", "0,05 s", "3,67 s", DUCKDB_X1],
    ["×100", "6 588 000", "454,5 Mo", "2,54 s", "41,8 s", DUCKDB_X100],
], [2.6, 2.6, 2.6, 2.6, 3.2, 3.2]),
      P("<b>Conclusion honnête</b> : à cette taille, pandas est nettement plus rapide : Spark paie le démarrage de la "
        "JVM et la lecture du CSV avec inférence du schéma (deux passes) et, en mode <i>local[*]</i> sur une seule "
        "machine, ne peut pas compenser. Nous gardons Spark parce que "
        "(i) le sujet et le cours portent sur le traitement distribué et que le pipeline s'exécute sur le cluster "
        "Onyxia, (ii) pandas charge tout en mémoire d'une seule machine (en local, 2,1 Go pour ×100 avec les 9 "
        "colonnes) et cesserait de fonctionner dès que les données dépassent la RAM, alors que Spark passe à "
        "l'échelle en ajoutant des exécuteurs. pandas est conservé "
        "pour la <i>vérification</i>. <b>DuckDB</b> (lab 04, <i>src/06_benchmark_duckdb.py</i>, même agrégation en "
        f"SQL) a aussi été mesuré : {DUCKDB_TEXT} Il redonne exactement les mêmes corrélations (0,2015 et 0,1936), "
        "ce qui constitue une troisième vérification. dbt (lab 05) n'a pas été mesuré : il orchestre des "
        "requêtes SQL sur un moteur (DuckDB ici) et n'apporte pas de calcul plus rapide.", body)]

s += [P("3. Problèmes de qualité des données", h2),
      table([
          ["Problème constaté", "Lignes concernées", "Traitement"],
          ["Colonne parasite <i>Unnamed: 0</i> (index pandas exporté)", "65 880 (toutes)", "supprimée"],
          ["Jours sans course (distance = 0 et durée = 0) mélangés aux sessions", "47 612 (72,3 %)",
           "conservés, flag <i>is_session</i> = faux ; exclus du calcul de vitesse"],
          ["Vitesses aberrantes (&lt; 3 km/h : 29 ; &gt; 25 km/h : 4)", "33 sessions",
           "flag <i>is_outlier</i>, exclues de la fréquence et de la vitesse"],
          ["Athlètes sans aucune session sur l'année", "4 athlètes (1 464 lignes)",
           "exclus de l'analyse : 176 athlètes restent"],
          ["<i>major</i> : plusieurs valeurs dans une seule chaîne", "colonne entière",
           "converti en <i>majors_count</i> (non utilisé dans la conclusion)"],
          ["Valeurs nulles, doublons (athlète, jour), incohérences distance/durée", "0", "contrôles en place (compteurs affichés)"],
      ], [7.4, 3.6, 6.5])]

s += [P("4. Résultats et limites", h2),
      Image("report/figures/fig1_resultats.png", width=17.2 * cm, height=17.2 * cm * 0.405),
      P("<b>Réponse : non, pas nécessairement.</b> Le lien existe mais est faible : Pearson <b>0,20</b> "
        "(p = 0,007), Spearman <b>0,19</b> (p = 0,010) sur 176 athlètes ; la fréquence n'explique que ~4 % de la "
        "variance de la vitesse (R² = 0,04) et chaque tranche de 100 sessions supplémentaires correspond à "
        "+0,43 km/h. Par quartile de fréquence, la vitesse vaut 10,8 / 10,4 / 10,8 / 11,3 km/h : seul le quartile "
        "le plus assidu se détache, la progression n'est pas monotone. Parmi les 25 % les plus rapides, "
        "<b>43 %</b> sont aussi parmi les 25 % les plus assidus (25 % attendus sans lien) : donc 57 % des plus "
        "rapides ne sont <i>pas</i> parmi les plus assidus. <b>Contrôle de composition</b> : en retirant les effets du "
        "sexe et de la tranche d'âge, la corrélation reste à 0,19 ; elle vaut 0,21 chez les hommes (n = 149) et "
        "0,08 chez les femmes (n = 27, non concluant)."),
      P("<b>Vérification indépendante</b> : Spark (gold) et pandas (depuis le CSV brut) donnent les mêmes valeurs "
        "(Pearson 0,2015, Spearman 0,1936, mêmes quartiles). Cette comparaison a révélé un écart initial sur "
        "Spearman (0,1932 contre 0,1936) dû aux ex-aequo : <i>rank()</i> de Spark attribue le plus petit rang, pandas "
        "le rang moyen ; corrigé par un rang moyen explicite."),
      P("<b>Limites.</b> Corrélation n'est pas causalité (les coureurs rapides peuvent courir plus parce qu'ils "
        "progressent). Un an, 176 athlètes dont seulement 27 femmes et 8 athlètes de 55+ ans. La fréquence ne "
        "dit rien du volume ni de l'intensité (nous n'avons que distance et durée). Le dataset a été réduit "
        "à 4,5 Mo par nos soins, ce qui peut avoir modifié sa représentativité. Le seuil [3 ; 25] km/h est un "
        "choix d'analyse.")]

s += [P("5. Si le dataset était 100 fois plus gros", h2),
      P("Mesuré ci-dessus (×100 = 6,6 millions de lignes, 455 Mo, 17 600 athlètes) : le résultat de l'agrégation reste "
        "identique (le jeu ×100 est une réplication, il n'apporte pas d'information nouvelle) ; avec de vraies "
        "données 100 fois plus nombreuses, la corrélation serait estimée avec une bien meilleure précision et "
        "les sous-groupes (femmes, 55+) deviendraient exploitables. Côté ingénierie : (i) pandas "
        "atteindrait ses limites mémoire (2,1 Go mesurés en local à ×100), Spark distribué devient indispensable ; (ii) "
        "<i>inferSchema</i> relit tout le CSV : un schéma explicite est nécessaire ; (iii) Parquet partitionné "
        "par mois et lecture par colonnes ; (iv) <i>ntile</i> / <i>rank</i> avec <i>Window.orderBy</i> sans partition "
        "ramènent tout sur une seule partition : remplacer par <i>approxQuantile</i> ; (v) mettre le silver en cache "
        "(il est lu plusieurs fois) et ajuster le nombre de partitions ; (vi) passer à Iceberg (lab 08) pour "
        "les réécritures et l'historique des versions.")]

present = [(f, d) for f, d in EVIDENCE if os.path.exists(os.path.join(EVIDENCE_DIR, f))]
rows = [["Fichier (evidence/)", "Contenu", "État"]]
for f, d in EVIDENCE:
    ok = os.path.exists(os.path.join(EVIDENCE_DIR, f))
    rows.append([f, d, "annexe" if ok else TODO])
s += [P("6. Preuves d'exécution et initiatives", h2),
      P("Toutes les captures ont été prises sur Onyxia les 26 et 27/11/2026 : chacune affiche le namespace "
        "<b>user-r-stitou-ece</b> (<i>echo $LAB_BUCKET_NAME</i>) et la date et l'heure (<i>date</i>, en UTC) avant "
        "la commande exécutée. Elles sont reproduites en annexe, à la même échelle."),
      table(rows, [5.6, 9.4, 2.5]),
      Spacer(1, 3),
      P("<b>Initiatives</b> : mode d'exécution local (<i>LOCAL_RUN=1</i>) pour tester sans Onyxia ; vérification "
        "indépendante par pandas, puis par DuckDB ; mesures pandas / Spark / DuckDB à ×1 et ×100 ; contrôle par sexe "
        "et par âge ; Job Kubernetes pour l'upload ; figures et rapport reproductibles (<i>src/04_figures.py</i>, "
        "<i>report/build_report.py</i>). Les temps de la section 2 ont été mesurés sur Onyxia ; "
        "seule la mémoire de pandas (2,1 Go) provient d'une mesure en local.")]

# --- Annexe : captures, a la meme echelle (largeur proportionnelle a la largeur en pixels) ---------
MAX_PAGES = 4


def annex(scale: float) -> list:
    """Captures presentes dans evidence/, toutes a la meme echelle `scale` (1 = pleine largeur)."""
    if not present:
        return []
    from PIL import Image as PILImage

    out = [P("Annexe — captures d'exécution sur Onyxia (images en pleine résolution : zoomer pour lire)", h2)]
    for f, d in present:
        path = os.path.join(EVIDENCE_DIR, f)
        with PILImage.open(path) as im:
            w_px, h_px = im.size
        w = min(17.2, w_px * PX_TO_CM * scale) * cm
        img = Image(path, width=w, height=w * h_px / w_px)
        img.hAlign = "LEFT"
        out += [KeepTogether([P(f"<b>{f}</b> — {d}", small), img, Spacer(1, 3)])]
    return out


def build(story: list, target) -> int:
    doc = SimpleDocTemplate(target, pagesize=A4, leftMargin=1.7 * cm, rightMargin=1.7 * cm,
                            topMargin=1.4 * cm, bottomMargin=1.3 * cm,
                            title="Fréquence des sessions et vitesse de course", author="")
    doc.build(story)
    return doc.page


# Plus grande echelle des captures qui tient dans MAX_PAGES pages (le sujet ne lit pas au-dela)
for scale in [round(1 - 0.02 * i, 2) for i in range(26)]:  # 1.00, 0.98, ... 0.50
    pages = build(copy.deepcopy(s) + annex(scale), io.BytesIO())
    if pages <= MAX_PAGES:
        break
pages = build(copy.deepcopy(s) + annex(scale), "report/rapport.pdf")
print(f"report/rapport.pdf : {pages} pages, captures a l'echelle {scale}")
if pages > MAX_PAGES:
    print(f"ATTENTION : plus de {MAX_PAGES} pages, les pages en trop ne seront pas lues")
