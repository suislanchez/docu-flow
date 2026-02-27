"""
Creates a synthetic clinical trial protocol PDF for testing.

The generated PDF is realistic enough to test:
  - Section header detection (inclusion/exclusion criteria)
  - Native text extraction (no OCR needed)
  - Bulleted criterion lists
  - Multi-page document structure (title, TOC, body, criteria, appendix)

Usage:
    python tests/pdf_strategies/fixtures/make_synthetic.py
    python -c "from tests.pdf_strategies.fixtures.make_synthetic import create_synthetic_protocol; \
               from pathlib import Path; create_synthetic_protocol(Path('test.pdf'))"
"""

from __future__ import annotations

from pathlib import Path


PROTOCOL_CONTENT = {
    "title": "A Phase 3, Randomised, Double-Blind, Placebo-Controlled Study of\nXenomalib in Adult Patients with Moderate-to-Severe Rheumatoid Arthritis",
    "sponsor": "Helix Biotherapeutics, Inc.",
    "protocol_number": "HBX-2023-RA-001",
    "phase": "Phase 3",
    "version": "Version 2.1, dated 14 January 2025",
    "pages": [
        {
            "title": "TABLE OF CONTENTS",
            "body": (
                "1. Introduction and Background .......................... 3\n"
                "2. Study Objectives ..................................... 4\n"
                "3. Study Design ......................................... 5\n"
                "4. Study Population ..................................... 6\n"
                "4.1 Inclusion Criteria ................................. 6\n"
                "4.2 Exclusion Criteria ................................. 7\n"
                "5. Study Procedures ..................................... 9\n"
                "6. Statistical Analysis Plan ........................... 11\n"
                "7. Ethical Considerations .............................. 13\n"
            ),
        },
        {
            "title": "1. INTRODUCTION AND BACKGROUND",
            "body": (
                "Rheumatoid arthritis (RA) is a chronic, systemic autoimmune disease characterised by\n"
                "persistent joint inflammation, progressive joint damage, and significant impairment of\n"
                "physical function and quality of life. The global prevalence of RA is approximately\n"
                "0.5–1% of the adult population.\n\n"
                "Xenomalib (HBX-001) is an investigational monoclonal antibody that selectively\n"
                "inhibits the JAK1/TYK2 pathway. Preclinical studies have demonstrated potent\n"
                "anti-inflammatory activity with a favourable safety profile.\n\n"
                "This Phase 3 study is designed to evaluate the efficacy and safety of Xenomalib\n"
                "versus placebo in adult patients with moderate-to-severe active RA who have had\n"
                "an inadequate response to at least one conventional synthetic DMARD."
            ),
        },
        {
            "title": "2. STUDY OBJECTIVES\n\n3. STUDY DESIGN",
            "body": (
                "2.1 Primary Objective\n"
                "To evaluate the efficacy of Xenomalib 200 mg SC every 4 weeks compared with\n"
                "placebo in reducing signs and symptoms of RA as measured by ACR20 response\n"
                "at Week 24.\n\n"
                "2.2 Secondary Objectives\n"
                "- ACR50 and ACR70 response rates at Week 24\n"
                "- Change from baseline in DAS28-CRP at Week 24\n"
                "- Clinical remission (DAS28-CRP < 2.6) at Week 24\n\n"
                "3.1 Overview\n"
                "This is a 52-week, multicentre, randomised, double-blind, placebo-controlled study.\n"
                "Patients will be randomised 2:1 to receive Xenomalib 200 mg SC or matching placebo\n"
                "every 4 weeks for 52 weeks."
            ),
        },
        {
            "title": "4. STUDY POPULATION\n4.1 INCLUSION CRITERIA",
            "body": (
                "Patients must meet ALL of the following inclusion criteria to be eligible:\n\n"
                "IC-01. Age ≥ 18 years at the time of signing the informed consent form.\n\n"
                "IC-02. Diagnosis of RA according to the 2010 ACR/EULAR classification criteria\n"
                "        for at least 6 months prior to Screening.\n\n"
                "IC-03. Moderate-to-severe active disease defined as:\n"
                "        (a) ≥ 6 tender joints (of 68 assessed) AND\n"
                "        (b) ≥ 6 swollen joints (of 66 assessed) AND\n"
                "        (c) hsCRP > 5 mg/L OR ESR > 28 mm/hour at Screening.\n\n"
                "IC-04. Inadequate response to at least one conventional synthetic DMARD\n"
                "        (e.g., methotrexate, leflunomide, sulfasalazine) administered for\n"
                "        ≥ 12 weeks at an adequate therapeutic dose.\n\n"
                "IC-05. Female patients of childbearing potential must agree to use highly\n"
                "        effective contraception throughout the study and for 6 months after\n"
                "        the last dose of study drug.\n\n"
                "IC-06. Able to provide written informed consent and comply with all study procedures."
            ),
        },
        {
            "title": "4.2 EXCLUSION CRITERIA",
            "body": (
                "Patients meeting ANY of the following criteria are NOT eligible for this study:\n\n"
                "EC-01. Age < 18 years.\n\n"
                "EC-02. Prior exposure to any JAK inhibitor (e.g., tofacitinib, baricitinib,\n"
                "        upadacitinib) or any biologic DMARD (e.g., TNF inhibitor, IL-6 inhibitor,\n"
                "        abatacept, rituximab).\n\n"
                "EC-03. Active, serious infection requiring IV antibiotics within 4 weeks prior\n"
                "        to Baseline, or any chronic or recurrent infection considered by the\n"
                "        Investigator to place the patient at unacceptable risk.\n\n"
                "EC-04. History of or current active tuberculosis (TB). Patients with latent TB\n"
                "        who have received adequate prophylactic treatment (≥ 4 weeks of isoniazid\n"
                "        or equivalent) prior to Baseline may be enrolled.\n\n"
                "EC-05. Known or suspected current malignancy, or history of malignancy within\n"
                "        the past 5 years, with the exception of adequately treated non-melanoma\n"
                "        skin cancer or cervical carcinoma in situ.\n\n"
                "EC-06. Pregnancy or breastfeeding at Screening or Baseline. Women of\n"
                "        childbearing potential with a positive serum pregnancy test at Screening."
            ),
        },
        {
            "title": "4.2 EXCLUSION CRITERIA (continued)",
            "body": (
                "EC-07. Severe renal impairment defined as eGFR < 30 mL/min/1.73 m²\n"
                "        (CKD-EPI formula) at Screening.\n\n"
                "EC-08. Severe hepatic impairment (Child-Pugh Class C) or ALT or AST > 3× ULN\n"
                "        at Screening.\n\n"
                "EC-09. Clinically significant cardiovascular disease within 12 months prior to\n"
                "        Baseline, including myocardial infarction, unstable angina, stroke, or\n"
                "        New York Heart Association (NYHA) Class III–IV heart failure.\n\n"
                "EC-10. Known HIV infection, active hepatitis B (HBsAg positive), or active\n"
                "        hepatitis C (HCV RNA positive) at Screening.\n\n"
                "EC-11. Absolute neutrophil count (ANC) < 1,000 cells/μL, haemoglobin < 8.0 g/dL,\n"
                "        or platelet count < 100,000 cells/μL at Screening.\n\n"
                "EC-12. Current or recent (within 30 days prior to Baseline) use of any\n"
                "        live attenuated vaccine, or planned vaccination during the study.\n\n"
                "EC-13. Known hypersensitivity to any component of the study drug formulation.\n\n"
                "EC-14. Participation in any other clinical study involving an investigational\n"
                "        product within 30 days or 5 half-lives (whichever is longer) prior to\n"
                "        Baseline."
            ),
        },
        {
            "title": "5. STUDY PROCEDURES",
            "body": (
                "5.1 Screening Period (Days −28 to −1)\n"
                "Patients will attend a Screening Visit to assess eligibility. The following\n"
                "assessments will be performed: informed consent, medical history, physical\n"
                "examination, vital signs, 12-lead ECG, laboratory assessments (haematology,\n"
                "chemistry, urinalysis), serum pregnancy test (women of childbearing potential),\n"
                "TB test (QuantiFERON-TB Gold or equivalent), and prior/concomitant medication review.\n\n"
                "5.2 Baseline Visit (Day 1)\n"
                "All screening assessments will be repeated and eligibility confirmed prior to\n"
                "randomisation. Patients will receive the first dose of study drug on Day 1.\n\n"
                "5.3 Treatment Period (Weeks 1–52)\n"
                "Study drug will be administered every 4 weeks (±3 days). At each visit:\n"
                "joint counts, PGA, PhGA, hsCRP/ESR, and concomitant medication review.\n"
                "Safety laboratory assessments at Weeks 4, 12, 24, 36, and 52."
            ),
        },
        {
            "title": "6. STATISTICAL ANALYSIS PLAN",
            "body": (
                "6.1 Analysis Populations\n"
                "The Intent-to-Treat (ITT) population includes all randomised patients who\n"
                "received at least one dose of study drug. The Per-Protocol (PP) population\n"
                "includes all ITT patients without major protocol deviations.\n\n"
                "6.2 Primary Endpoint Analysis\n"
                "The primary endpoint (ACR20 response at Week 24) will be analysed using a\n"
                "logistic regression model with treatment group as the fixed effect and\n"
                "baseline DAS28-CRP, prior biologic use (yes/no), and geographic region as\n"
                "covariates. Non-responder imputation (NRI) will be used for missing data.\n\n"
                "6.3 Sample Size\n"
                "Assuming 60% ACR20 response rate for Xenomalib and 25% for placebo, with\n"
                "80% power and two-sided α = 0.05, a total of 240 patients (160 active:\n"
                "80 placebo) are required."
            ),
        },
    ],
}


def create_synthetic_protocol(output_path: Path) -> None:
    """Create a synthetic clinical trial protocol PDF at *output_path*."""
    import fitz  # PyMuPDF

    doc = fitz.open()

    # -- Title page --
    page = doc.new_page(width=595, height=842)  # A4
    _add_title_page(page, PROTOCOL_CONTENT)

    # -- Content pages --
    for page_content in PROTOCOL_CONTENT["pages"]:
        page = doc.new_page(width=595, height=842)
        _add_content_page(page, page_content["title"], page_content["body"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    doc.close()
    print(f"Synthetic protocol PDF written: {output_path}  ({output_path.stat().st_size // 1024} KB)")


def _add_title_page(page, content: dict) -> None:
    import fitz

    rect = page.rect
    y = 200.0

    # Title
    for line in content["title"].split("\n"):
        page.insert_text(
            (72, y), line,
            fontsize=14, fontname="helv", color=(0, 0, 0),
        )
        y += 22

    y += 30
    for label, key in [("Sponsor:", "sponsor"), ("Protocol No.:", "protocol_number"),
                        ("Phase:", "phase"), ("Version:", "version")]:
        page.insert_text((72, y), f"{label}  {content[key]}", fontsize=11, fontname="helv")
        y += 18

    # Footer
    page.insert_text((72, rect.height - 50), "CONFIDENTIAL", fontsize=10,
                     fontname="helv", color=(0.5, 0.5, 0.5))


def _add_content_page(page, title: str, body: str) -> None:
    y = 60.0
    # Section title
    for line in title.split("\n"):
        page.insert_text((72, y), line, fontsize=12, fontname="hebo", color=(0, 0, 0.6))
        y += 18
    y += 8

    # Body text — line-wrap at ~90 chars
    for paragraph in body.split("\n\n"):
        for line in paragraph.split("\n"):
            # Wrap long lines
            while len(line) > 90:
                chunk, line = line[:90], line[90:]
                page.insert_text((72, y), chunk, fontsize=10, fontname="helv")
                y += 14
            page.insert_text((72, y), line, fontsize=10, fontname="helv")
            y += 14
            if y > page.rect.height - 80:
                break
        y += 6  # paragraph spacing
        if y > page.rect.height - 80:
            break

    # Page number
    page_num = page.number + 1
    page.insert_text(
        (page.rect.width / 2 - 10, page.rect.height - 30),
        str(page_num), fontsize=9, fontname="helv", color=(0.5, 0.5, 0.5),
    )


if __name__ == "__main__":
    out = Path(__file__).parent / "synthetic_protocol.pdf"
    create_synthetic_protocol(out)
