"""
Presentation Generator for Enterprise Business Entity Resolution System.
Uses python-pptx to generate a professional, modern 16:9 presentation deck.
"""

import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def create_deck(output_filename="BusinessEntityResolution_Presentation.pptx"):
    prs = Presentation()
    # Set 16:9 widescreen dimensions (13.33 x 7.5 inches)
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Theme Colors
    BG_DARK = RGBColor(15, 23, 42)      # Deep Slate/Navy
    BG_CARD = RGBColor(30, 41, 59)      # Slate Card
    TEXT_WHITE = RGBColor(248, 250, 252)
    TEXT_MUTED = RGBColor(148, 163, 184)
    ACCENT_BLUE = RGBColor(56, 189, 248) # Cyan/Sky Blue
    ACCENT_GREEN = RGBColor(52, 211, 153)# Emerald
    ACCENT_GOLD = RGBColor(251, 191, 36) # Amber
    BORDER_COLOR = RGBColor(51, 65, 85)

    def add_bg(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = BG_DARK
        bg.line.color.rgb = BG_DARK
        return bg

    def add_header(slide, title_text, category_text="BUSINESS ENTITY RESOLUTION"):
        header_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.7), Inches(1.1))
        tf = header_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        
        p_cat = tf.paragraphs[0]
        p_cat.text = category_text.upper()
        p_cat.font.size = Pt(11)
        p_cat.font.bold = True
        p_cat.font.color.rgb = ACCENT_BLUE

        p_title = tf.add_paragraph()
        p_title.text = title_text
        p_title.font.size = Pt(24)
        p_title.font.bold = True
        p_title.font.color.rgb = TEXT_WHITE
        p_title.space_before = Pt(4)

    def add_card(slide, left, top, width, height, title="", border=True):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = BG_CARD
        if border:
            card.line.color.rgb = BORDER_COLOR
            card.line.width = Pt(1.2)
        else:
            card.line.fill.background()
            
        if title:
            tb = slide.shapes.add_textbox(left + Inches(0.25), top + Inches(0.2), width - Inches(0.5), Inches(0.5))
            tf = tb.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = title
            p.font.size = Pt(14)
            p.font.bold = True
            p.font.color.rgb = ACCENT_BLUE
        return card

    # -------------------------------------------------------------
    # SLIDE 1: Title Slide
    # -------------------------------------------------------------
    s1 = prs.slides.add_slide(blank_layout)
    add_bg(s1)

    t_box = s1.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(11.3), Inches(3.5))
    tf1 = t_box.text_frame
    tf1.word_wrap = True

    p0 = tf1.paragraphs[0]
    p0.text = "ENTERPRISE MACHINE LEARNING SYSTEM"
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = ACCENT_BLUE

    p1 = tf1.add_paragraph()
    p1.text = "Business Entity Resolution & Deduplication"
    p1.font.size = Pt(36)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_WHITE
    p1.space_before = Pt(8)

    p2 = tf1.add_paragraph()
    p2.text = "High-Precision Cross-Database Record Linkage without Shared Primary Keys"
    p2.font.size = Pt(18)
    p2.font.color.rgb = TEXT_MUTED
    p2.space_before = Pt(12)

    # Highlight metrics cards on title slide
    metrics = [
        ("99.33%", "Test Accuracy", ACCENT_GREEN),
        ("99.11%", "Precision (Low FP)", ACCENT_BLUE),
        ("99.55%", "Recall (High Coverage)", ACCENT_GOLD),
        (">99.9%", "Blocking Pruning Rate", ACCENT_GREEN)
    ]
    for i, (val, lbl, col) in enumerate(metrics):
        card = add_card(s1, Inches(1.0 + i * 2.85), Inches(5.2), Inches(2.7), Inches(1.3))
        tb = s1.shapes.add_textbox(Inches(1.0 + i * 2.85), Inches(5.3), Inches(2.7), Inches(1.1))
        tf = tb.text_frame
        p_val = tf.paragraphs[0]
        p_val.text = val
        p_val.font.size = Pt(24)
        p_val.font.bold = True
        p_val.font.color.rgb = col
        p_val.alignment = PP_ALIGN.CENTER
        
        p_lbl = tf.add_paragraph()
        p_lbl.text = lbl
        p_lbl.font.size = Pt(11)
        p_lbl.font.color.rgb = TEXT_MUTED
        p_lbl.alignment = PP_ALIGN.CENTER

    # -------------------------------------------------------------
    # SLIDE 2: Problem Statement & Challenges
    # -------------------------------------------------------------
    s2 = prs.slides.add_slide(blank_layout)
    add_bg(s2)
    add_header(s2, "The Core Challenge: Disconnected Data Silos", "Problem Definition")

    cards_s2 = [
        ("The Business Problem", [
            "Enterprises aggregate business records across multiple vendors, CRMs, and public filings (Source 1, Source 2, Source 3).",
            "Zero shared identifiers (No universal Tax ID, DUNS, or primary key).",
            "Duplication corrupts customer analytics, credit scoring, compliance, and marketing spend."
        ]),
        ("Data Noise & Discrepancies", [
            "Spelling errors & typos (e.g., 'Zephay Labs' vs 'Zephari Labs').",
            "Corporate legal suffixes ('Pvt Ltd', 'Inc', 'LLC', 'SARL', 'GmbH').",
            "Address abbreviations ('St' vs 'Street', missing suite numbers).",
            "International variations across countries and regional registries."
        ]),
        ("The O(N^2) Computational Barrier", [
            "Naive pairwise matching between 10,000 x 10,000 records requires 100 Million comparisons.",
            "Test dataset scale (11.7M records) would require 8.4 Trillion comparisons.",
            "Solution requires an ultra-fast Blocking Engine coupled with High-Precision ML."
        ])
    ]
    for i, (title, points) in enumerate(cards_s2):
        add_card(s2, Inches(0.8 + i * 3.95), Inches(1.8), Inches(3.75), Inches(5.0), title=title)
        tb = s2.shapes.add_textbox(Inches(1.0 + i * 3.95), Inches(2.5), Inches(3.35), Inches(4.0))
        tf = tb.text_frame
        tf.word_wrap = True
        for j, pt in enumerate(points):
            p = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
            p.text = f"- {pt}"
            p.font.size = Pt(12)
            p.font.color.rgb = TEXT_WHITE
            p.space_after = Pt(10)

    # -------------------------------------------------------------
    # SLIDE 3: End-to-End Pipeline Architecture
    # -------------------------------------------------------------
    s3 = prs.slides.add_slide(blank_layout)
    add_bg(s3)
    add_header(s3, "End-to-End System Architecture", "System Design")

    stages = [
        ("1. Data Cleansing", "Advanced Text Normalization\n- Strip 30+ legal suffixes\n- Standardize street abbreviations\n- City/State regex token parsing"),
        ("2. Multi-Key Blocking", "Search Space Pruning (>99.9%)\n- Prefix key: name[:3]\n- Phonetic key: Soundex(name)\n- Geographic key: Country code"),
        ("3. Feature Extraction", "13-Dimensional Feature Vector\n- Levenshtein & Partial ratios\n- Token Sort & Set similarities\n- Geographic & Anchor matches"),
        ("4. ML Tournament", "Model Championship\n- Random Forest (200 Trees)\n- 5-Fold Stratified CV (99.1%)\n- Calibrated probability output"),
        ("5. Graph Resolution", "Transitive Entity Closure\n- Disjoint Set / Connected Graphs\n- Merges S1 <-> S2 <-> S3 pairs\n- Generates canonical cluster IDs")
    ]
    for i, (stage_name, stage_desc) in enumerate(stages):
        add_card(s3, Inches(0.8 + i * 2.38), Inches(2.0), Inches(2.25), Inches(4.8), title=stage_name)
        tb = s3.shapes.add_textbox(Inches(0.9 + i * 2.38), Inches(2.7), Inches(2.05), Inches(3.9))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = stage_desc
        p.font.size = Pt(11)
        p.font.color.rgb = TEXT_WHITE
        p.space_after = Pt(6)

    # -------------------------------------------------------------
    # SLIDE 4: Module 3 - Better Blocking Benchmarks
    # -------------------------------------------------------------
    s4 = prs.slides.add_slide(blank_layout)
    add_bg(s4)
    add_header(s4, "Intelligent Multi-Key Blocking: 1,055x Speedup", "Module 3: Scalability")

    add_card(s4, Inches(0.8), Inches(1.8), Inches(11.7), Inches(5.0), title="Blocking Benchmark on Test Data Pairs")
    tb = s4.shapes.add_textbox(Inches(1.1), Inches(2.4), Inches(11.1), Inches(4.2))
    tf = tb.text_frame
    tf.word_wrap = True
    
    table_lines = [
        "Strategy Name                        | Logic Applied                      | Pairs Evaluated | Pruning Rate | Effective Speedup",
        "--------------------------------------------------------------------------------------------------------------------------------",
        "Naive (No Blocking - Baseline)       | Compare All Pairs (N x M)          | 2,500,000       | 0.00%        | 1.0x (Baseline)",
        "Lesson 2: First Letter Blocking      | clean_name[:1]                     | 124,240         | 95.03%       | ~20x faster",
        "Lesson 3: First 2 Letters Blocking   | clean_name[:2]                     | 17,579          | 99.30%       | ~142x faster",
        "Lesson 4: Country-Level Partitioning | country == country                 | 981,088         | 60.76%       | ~2.5x faster",
        "Lesson 5: Soundex Phonetic Indexing  | Soundex(first_token)               | 4,861           | 99.81%       | ~514x faster",
        "Lesson 6: Multi-Key Hybrid (Champion)| Country + Soundex(first_token)     | 2,368           | 99.91%       | 1,055x FASTER! [CHAMPION]"
    ]
    for idx, line in enumerate(table_lines):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.text = line
        p.font.name = "Consolas"
        p.font.size = Pt(11)
        p.font.color.rgb = ACCENT_GREEN if "CHAMPION" in line else (ACCENT_BLUE if idx < 2 else TEXT_WHITE)

    # -------------------------------------------------------------
    # SLIDE 5: 13-Feature Engineering Matrix & Importance
    # -------------------------------------------------------------
    s5 = prs.slides.add_slide(blank_layout)
    add_bg(s5)
    add_header(s5, "13-Feature Engineering & Empirical Feature Importance", "Feature Science")

    add_card(s5, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.0), title="Top Feature Importance (Random Forest)")
    tb_fi = s5.shapes.add_textbox(Inches(1.0), Inches(2.4), Inches(5.3), Inches(4.2))
    tf_fi = tb_fi.text_frame
    tf_fi.word_wrap = True

    fi_items = [
        ("1. name_similarity", "21.87%", "Levenshtein edit distance on normalized name"),
        ("2. partial_ratio", "19.93%", "Identifies strong substring overlap / brand core"),
        ("3. address_similarity", "14.89%", "Full street address matching ratio"),
        ("4. token_sort_ratio", "13.71%", "Permutation invariant (e.g. 'Lab Alpha' = 'Alpha Lab')"),
        ("5. token_set_ratio", "11.18%", "Robust to added words (e.g. 'Clinic' vs 'Specialty Clinic')"),
        ("6. common_word_count", "8.88%", "Absolute lexical token overlap count"),
        ("7. city_match", "3.52%", "City level geographic consistency"),
        ("8. first_word_match", "3.31%", "Anchor token brand identification")
    ]
    for idx, (f_name, f_wt, f_desc) in enumerate(fi_items):
        p = tf_fi.paragraphs[0] if idx == 0 else tf_fi.add_paragraph()
        p.text = f"{f_name:<20} {f_wt:>6}  | {f_desc}"
        p.font.name = "Consolas"
        p.font.size = Pt(10)
        p.font.color.rgb = ACCENT_GOLD if idx < 3 else TEXT_WHITE

    add_card(s5, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0), title="Why Multi-Faceted Features?")
    tb_why = s5.shapes.add_textbox(Inches(7.0), Inches(2.4), Inches(5.3), Inches(4.2))
    tf_why = tb_why.text_frame
    tf_why.word_wrap = True

    why_points = [
        ("Resistance to Word Reordering", "Token Sort Ratio ensures that entities recorded in reverse format ('General Motors Corp' vs 'Motors General Corp') receive perfect match scores."),
        ("Noise & Suffix Robustness", "Token Set Ratio disregards extraneous noise tokens and duplicate descriptions, preventing false negatives."),
        ("Anchor Brand Protection", "First-word exact matching and Soundex phonetic encoding ensure distinct brands with similar generic descriptions are not incorrectly merged."),
        ("Geographic Constraints", "City, State, and Country matching prevent cross-border false positives between identically named regional stores.")
    ]
    for idx, (w_t, w_b) in enumerate(why_points):
        p_t = tf_why.paragraphs[0] if idx == 0 else tf_why.add_paragraph()
        p_t.text = f"• {w_t}:"
        p_t.font.bold = True
        p_t.font.size = Pt(12)
        p_t.font.color.rgb = ACCENT_BLUE
        
        p_b = tf_why.add_paragraph()
        p_b.text = f"  {w_b}"
        p_b.font.size = Pt(11)
        p_b.font.color.rgb = TEXT_WHITE
        p_b.space_after = Pt(6)

    # -------------------------------------------------------------
    # SLIDE 6: Championship Model Tournament & Benchmarks
    # -------------------------------------------------------------
    s6 = prs.slides.add_slide(blank_layout)
    add_bg(s6)
    add_header(s6, "Championship Tournament: Model Benchmark", "Model Evaluation")

    add_card(s6, Inches(0.8), Inches(1.8), Inches(11.7), Inches(5.0), title="5-Fold Stratified Cross-Validation & Test Metrics")
    tb_mod = s6.shapes.add_textbox(Inches(1.1), Inches(2.5), Inches(11.1), Inches(4.0))
    tf_mod = tb_mod.text_frame
    tf_mod.word_wrap = True

    model_lines = [
        "Algorithm                  | 5-Fold CV Mean | CV Std Dev | Precision  | Recall     | F1-Score   | Status",
        "-------------------------------------------------------------------------------------------------------------------",
        "Random Forest (200 Trees)  | 99.10%         | +/- 0.43%  | 99.11%     | 99.55%     | 99.33%     | CHAMPION WINNER [★]",
        "XGBoost Classifier         | 99.10%         | +/- 0.43%  | 98.80%     | 99.40%     | 99.10%     | Benchmark Baseline",
        "LightGBM Classifier        | 99.10%         | +/- 0.47%  | 98.80%     | 99.30%     | 99.05%     | High Speed Baseline",
        "",
        "Confusion Matrix Breakdown (Holdout Test of 450 Entity Pairs):",
        "  • True Negatives (TN)  : 223 pairs (Correctly distinguished different entities)",
        "  • True Positives (TP)  : 224 pairs (Accurately identified duplicate entities across sources)",
        "  • False Positives (FP) :   2 pairs (Ultra-rare identical address sharing)",
        "  • False Negatives (FN) :   1 pair  (Heavy acronym distortion)",
        "",
        "Key Decision: Random Forest was selected for production due to superior precision (99.11%)",
        "minimizing destructive erroneous customer record merges."
    ]
    for idx, ml in enumerate(model_lines):
        p = tf_mod.paragraphs[0] if idx == 0 else tf_mod.add_paragraph()
        p.text = ml
        p.font.name = "Consolas"
        p.font.size = Pt(11)
        if "CHAMPION WINNER" in ml:
            p.font.color.rgb = ACCENT_GREEN
            p.font.bold = True
        elif idx < 2:
            p.font.color.rgb = ACCENT_BLUE
        else:
            p.font.color.rgb = TEXT_WHITE

    # -------------------------------------------------------------
    # SLIDE 7: Transitive Closure & Graph Linking
    # -------------------------------------------------------------
    s7 = prs.slides.add_slide(blank_layout)
    add_bg(s7)
    add_header(s7, "Multi-Source Graph Linking & Transitive Closure", "Module 7 & 8: Resolution")

    add_card(s7, Inches(0.8), Inches(1.8), Inches(5.7), Inches(5.0), title="Why Graph Linking is Required")
    tb_g1 = s7.shapes.add_textbox(Inches(1.0), Inches(2.4), Inches(5.3), Inches(4.2))
    tf_g1 = tb_g1.text_frame
    tf_g1.word_wrap = True

    g1_points = [
        "Pairwise matching only resolves 2 records at a time (e.g. S1 <-> S2).",
        "Enterprise reality involves N-way relationships: S1 matches S2, and S2 matches S3.",
        "Without transitive closure, S1 and S3 remain isolated duplicates.",
        "Connected Component Clustering groups all related entity records into a single Canonical Entity ID.",
        "Generates clean, unified golden customer profiles across all operational databases."
    ]
    for idx, pt in enumerate(g1_points):
        p = tf_g1.paragraphs[0] if idx == 0 else tf_g1.add_paragraph()
        p.text = f"• {pt}"
        p.font.size = Pt(12)
        p.font.color.rgb = TEXT_WHITE
        p.space_after = Pt(12)

    add_card(s7, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0), title="Submission & Cluster Resolution")
    tb_g2 = s7.shapes.add_textbox(Inches(7.0), Inches(2.4), Inches(5.3), Inches(4.2))
    tf_g2 = tb_g2.text_frame
    tf_g2.word_wrap = True

    g2_points = [
        ("Output Deliverables", "Generated official submission files in 'output/submission.tsv' and 'output/submission.csv' matching competition specifications."),
        ("Consistent Transitivity", "If A = B with 99% confidence and B = C with 98% confidence, cluster {A, B, C} is unified under one entity identifier."),
        ("Edge Case Conflict Resolution", "Graph pruning threshold drops weak edges (< 0.50 probability) before clustering to prevent transitive chain drift.")
    ]
    for idx, (t, d) in enumerate(g2_points):
        p_t = tf_g2.paragraphs[0] if idx == 0 else tf_g2.add_paragraph()
        p_t.text = f"✔ {t}:"
        p_t.font.bold = True
        p_t.font.size = Pt(12)
        p_t.font.color.rgb = ACCENT_GREEN
        
        p_d = tf_g2.add_paragraph()
        p_d.text = f"  {d}"
        p_d.font.size = Pt(11)
        p_d.font.color.rgb = TEXT_WHITE
        p_d.space_after = Pt(8)

    # -------------------------------------------------------------
    # SLIDE 8: Deployment, Inference & Future Roadmap
    # -------------------------------------------------------------
    s8 = prs.slides.add_slide(blank_layout)
    add_bg(s8)
    add_header(s8, "Production Inference & Technical Roadmap", "Deployment & Next Steps")

    cards_s8 = [
        ("Production Inference (predict.py)", [
            "Reusable Python API & CLI interface.",
            "Real-time pair scoring with confidence metrics.",
            "Immediate breakdown of top feature contributions.",
            "Sub-millisecond inference per candidate pair."
        ]),
        ("Error Analysis Insights", [
            "False Positives occur when franchise branches share corporate headquarters addresses.",
            "False Negatives occur when brand names are heavily abbreviated (e.g. 'IBM' vs 'International Business Machines').",
            "Mitigated via Soundex and Token Set ratios."
        ]),
        ("Future Enhancements", [
            "Dense Vector Embeddings (Sentence-Transformers / BAAI) combined with FAISS indexing.",
            "Active Learning human-in-the-loop verification for marginal probabilities (45% - 55%).",
            "Distributed PySpark implementation for 100M+ global enterprise entity datasets."
        ])
    ]
    for i, (title, pts) in enumerate(cards_s8):
        add_card(s8, Inches(0.8 + i * 3.95), Inches(1.8), Inches(3.75), Inches(5.0), title=title)
        tb = s8.shapes.add_textbox(Inches(1.0 + i * 3.95), Inches(2.5), Inches(3.35), Inches(4.0))
        tf = tb.text_frame
        tf.word_wrap = True
        for j, pt in enumerate(pts):
            p = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
            p.text = f"• {pt}"
            p.font.size = Pt(12)
            p.font.color.rgb = TEXT_WHITE
            p.space_after = Pt(10)

    prs.save(output_filename)
    print(f"[OK] Successfully generated presentation: {output_filename}")

if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else "BusinessEntityResolution_Presentation.pptx"
    create_deck(out_file)
