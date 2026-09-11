from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


OUT = Path("XboxSupport_Agent_Report.docx")
NAVY = "17365D"
BLUE = "D9EAF7"
PALE = "F4F7FA"
GRAY = "D9D9D9"


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    tc_pr.append(shading)


def set_cell_border(cell, color=GRAY):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = "w:" + edge
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:color"), color)


def set_cell_margins(cell, top=90, start=110, bottom=90, end=110):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for side, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn("w:" + side))
        if node is None:
            node = OxmlElement("w:" + side)
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def font(run, size=10.0, bold=False, color="000000", italic=False):
    run.font.name = "Aptos"
    run._element.rPr.rFonts.set(qn("w:ascii"), "Aptos")
    run._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos")
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = RGBColor.from_string(color)


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run("Page ")
    font(run, 8, color="555555")
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    paragraph._p.append(fld)


def add_heading(doc, text, level=1):
    p = doc.add_paragraph(style=f"Heading {level}")
    p.paragraph_format.space_before = Pt(7 if level == 1 else 4)
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run(text)
    font(run, 14 if level == 1 else 11, bold=True, color="000000")
    return p


def add_body(doc, text, size=9.5, after=4):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.08
    run = p.add_run(text)
    font(run, size)
    return p


def add_bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(1.5)
    p.paragraph_format.line_spacing = 1.0
    run = p.add_run(text)
    font(run, 8.8)


def add_table(doc, headers, rows, widths=None, font_size=8.3):
    table = doc.add_table(rows=1, cols=len(headers))
    table.autofit = False
    table.style = "Table Grid"
    for i, header in enumerate(headers):
        cell = table.rows[0].cells[i]
        if widths:
            cell.width = Inches(widths[i])
        set_cell_shading(cell, NAVY)
        set_cell_border(cell)
        set_cell_margins(cell)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        para = cell.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = para.add_run(header)
        font(run, font_size, bold=True, color="FFFFFF")
    for row_index, row in enumerate(rows):
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cell = cells[i]
            if widths:
                cell.width = Inches(widths[i])
            set_cell_border(cell)
            set_cell_margins(cell)
            if row_index % 2 == 1:
                set_cell_shading(cell, PALE)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            para = cell.paragraphs[0]
            para.paragraph_format.space_after = Pt(0)
            run = para.add_run(str(value))
            font(run, font_size)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)
    return table


def page_break(doc):
    doc.add_page_break()


def setup_document():
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.58)
    section.bottom_margin = Inches(0.55)
    section.left_margin = Inches(0.64)
    section.right_margin = Inches(0.64)
    section.header_distance = Inches(0.25)
    section.footer_distance = Inches(0.25)
    normal = doc.styles["Normal"]
    normal.font.name = "Aptos"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Aptos")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos")
    normal.font.size = Pt(9.5)
    for name in ("Title", "Heading 1", "Heading 2"):
        style = doc.styles[name]
        style.font.name = "Aptos"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Aptos")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos")
        style.font.color.rgb = RGBColor(0, 0, 0)
    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = header.add_run("XboxSupport Twitter Agent")
    font(run, 8, color="555555")
    add_page_number(section.footer.paragraphs[0])
    return doc


def main():
    doc = setup_document()

    # Page 1
    p = doc.add_paragraph(style="Title")
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_after = Pt(5)
    title = p.add_run("XboxSupport Twitter Agent")
    font(title, 25, bold=True)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(14)
    sub = p.add_run("A small but auditable AI support prototype built from real Twitter conversations")
    font(sub, 12, color="444444")
    add_heading(doc, "Why Xbox", 1)
    add_body(doc, "I chose XboxSupport because I genuinely love playing games, so this was a brand where I could understand the customer pain behind the tweets. It also gave me a large, messy support dataset with real questions about Game Pass, downloads, accounts, controllers, billing and Xbox Live. Basically, the good kind of messy.")
    add_heading(doc, "What I built", 1)
    add_body(doc, "The prototype reads an incoming customer tweet, assigns one of nine support intents, retrieves similar historical XboxSupport cases and a relevant official Xbox support page, drafts a safe reply, and decides whether the case can be auto-handled or must go to a human. Every escalation has a stated reason.")
    add_heading(doc, "The honest headline", 1)
    add_body(doc, "The agent beats a trivial intent baseline, but it is not ready to freely answer customers. On a locked 200-message golden set, intent macro-F1 is 0.455. The more important result is safety: even with narrow auto-handling rules, 6 of 31 auto-handled messages should have been escalated. That is why I would launch this only in shadow mode first.")
    add_table(doc, ["Metric", "Result", "Why it matters"], [
        ["Golden set", "200 reviewed tweets", "Held out by conversation thread"],
        ["Intent macro-F1", "0.455", "Better than the trivial baseline"],
        ["Auto-handle F1", "0.431", "Routing is harder than intent prediction"],
        ["Unsafe auto-handle rate", "19.4%", "Too high for live automation"],
    ], [1.55, 1.25, 4.1])
    add_body(doc, "Repository: github.com/naurjhanvi/hiver_SDE_assignment", 8.5, after=0)

    # Page 2
    page_break(doc)
    add_heading(doc, "Dataset and problem framing", 1)
    add_body(doc, "The source is Customer Support on Twitter, a Kaggle dataset with roughly three million tweets across many brands. I intentionally did not train on the full dataset. I extracted a focused Xbox-only subset and used 20,158 customer-message and XboxSupport-reply pairs for training. This makes the project practical to reproduce, inspect and discuss in an interview.")
    add_table(doc, ["Split", "Rows", "Role"], [
        ["Training", "20,158", "Fit the intent model and retrieve historical precedents"],
        ["Development", "2,241", "Choose a simple, balanced model"],
        ["Golden evaluation", "200", "Final reviewed test set, never used for tuning"],
    ], [1.6, 1.0, 4.3])
    add_body(doc, "Filtering logic: I retained every tweet authored by XboxSupport and recursively followed each tweet's reply chain backwards to keep the customer context. I did not simply keyword-search for 'Xbox', because that would pull in unrelated people talking about the brand.")
    add_heading(doc, "What good means here", 1)
    add_body(doc, "A good Xbox support agent should identify the broad issue, point someone to a genuine public workflow when that is safe, and know when to stop. Safety means not pretending to reset accounts, inspect videos, take payments or make enforcement decisions.")
    add_heading(doc, "What I deliberately did not build", 1)
    add_bullet(doc, "No login or access to Xbox accounts")
    add_bullet(doc, "No payment, refund, code-redemption or enforcement actions")
    add_bullet(doc, "No remote hardware diagnosis or actual image and video inspection")
    add_bullet(doc, "No fake promise that a human request is already resolved")
    add_heading(doc, "Intent design", 1)
    add_table(doc, ["Intent groups", "Examples"], [
        ["Account and profile", "Sign-in, password, gamertag, account recovery"],
        ["Billing and subscriptions", "Game Pass, refunds, codes, payment issues"],
        ["Games and device support", "Downloads, install problems, console, display"],
        ["Connectivity and safety", "Xbox Live, party chat, reports, enforcement"],
        ["Information and unclear cases", "How-to questions or insufficient context"],
    ], [2.25, 4.65])
    add_body(doc, "There are nine final labels in the repository. I used these five groups here only to make the taxonomy easy to scan.", 8.5)

    # Page 3
    page_break(doc)
    add_heading(doc, "How the agent works", 1)
    add_body(doc, "The final model is intentionally simple. It uses a balanced multinomial Naive Bayes classifier with word unigrams and bigrams. I capped each intent at 700 training examples so the largest categories did not completely dominate the smaller ones. It then retrieves lexical matches from historical customer messages and a small curated catalog of official Xbox support pages.")
    add_heading(doc, "Routing policy", 1)
    add_body(doc, "The first version only auto-handles clear subscription and game-download requests that have a documented public support workflow. It escalates account recovery, billing, codes, security, enforcement, hardware, ambiguous messages and anything with image or video cues. This is conservative by design.")
    add_heading(doc, "Results against baselines", 1)
    add_table(doc, ["System", "Development macro-F1", "Golden macro-F1"], [
        ["Trivial baseline: always account_access_profile", "0.068", "0.020"],
        ["Simple baseline: balanced Naive Bayes", "0.373", "0.455"],
        ["Final agent intent component", "0.373", "0.455"],
    ], [3.25, 1.75, 1.75])
    add_body(doc, "The final agent uses the selected simple classifier because the goal was an explainable baseline plus safe routing and evidence retrieval, not a black-box accuracy race.")
    add_heading(doc, "Reply quality check", 1)
    add_body(doc, "I also built an LLM-as-judge rubric. It checks groundedness, safety, relevance and whether the routing decision makes sense. Qwen 2.5 3B Instruct ran locally through Ollama, so this part used no paid API. I reviewed 30 sampled replies myself. The local LLM passed 14 and failed 16. Raw agreement was 46.7%; Cohen's kappa was 0.00 because I marked every human review as pass, so there was no human label variation. That is weak agreement evidence, and I say that clearly instead of hiding it.")
    add_heading(doc, "How the golden set was made", 1)
    add_body(doc, "I sampled 200 thread-disjoint customer messages. Retrieval was used to pre-label likely intents and likely handling outcomes, then I manually reviewed and finalized the columns. The historical reply is deliberately absent from the golden file, so the evaluator cannot peek at the answer while testing the agent.")

    # Page 4
    page_break(doc)
    add_heading(doc, "Failure analysis with real tweets", 1)
    add_body(doc, "These are not polished toy examples. They are real messages from the evaluation workflow. The examples are included to show where the agent needs help, not to pretend that 0.455 is amazing.")
    add_table(doc, ["Failure mode", "Real tweet example", "Likely reason"], [
        ["Account wording over-generalises", "'when I power cycle my xbox it gets stuck on the green logo screen :('", "The label model sees common account-like support wording even though this is closer to a console boot issue."],
        ["Very short or incomplete context", "'it's just plugged into the wall'", "A reply fragment alone has too little meaning. It needs thread context or a human follow-up."],
        ["Public or private boundary", "'I forgot my email password and I don't have my old phone number'", "The request sounds like a how-to, but recovery requires private account verification."],
        ["Historical links are weak evidence", "'There is no manual update listed for me to download under updates for the title.'", "Historical Twitter replies often contain short links, not the whole repair workflow."],
        ["Media cannot really be inspected", "'I can't install FIFA. I can't install WWII. I'm about to go nuts.'", "The export preserves text better than attachment metadata. The agent can spot media cues, but cannot see the media."],
    ], [1.35, 3.25, 2.15], 7.7)
    add_heading(doc, "Where the judge disagreed with me", 1)
    add_body(doc, "The local judge was much stricter than I was. For example, it failed several escalated replies because they were safe but generic. This is a useful signal: a reply can be correctly routed and still not be very helpful. The judge should be treated as another reviewer, not as truth.")
    add_table(doc, ["Example", "My review", "Local LLM review"], [
        ["$400 hold on my card for an exchanged console", "Pass: correct billing escalation", "Fail: reply may be too generic"],
        ["You cannot use Bluetooth headsets for Xbox?", "Pass: safely routed", "Fail: it wanted a more useful answer"],
    ], [3.5, 1.55, 1.7])

    # Page 5
    page_break(doc)
    add_heading(doc, "What is misleading about the headline number", 1)
    add_body(doc, "Macro-F1 of 0.455 is a real improvement over the majority baseline, but it is not a trust score. First, the golden set is only 200 messages and comes from the same historical channel as the training data. Second, the labels were retrieval-prelabelled before manual review. Third, broad categories hide hard distinctions, especially whether an account issue is public self-service or private recovery. Finally, an intent score says nothing about whether an auto-reply is safe.")
    add_body(doc, "The clearest reality check is the routing metric: the narrow policy still made 6 unsafe auto-handles out of 31 auto-handled cases. That 19.4% rate is the number I would worry about in a real launch.")
    add_heading(doc, "What I would do with one more week", 1)
    add_bullet(doc, "Ask a second person to independently label a fresh sample, including both pass and fail reply judgments.")
    add_bullet(doc, "Keep real media metadata so photo and video cases can be reliably escalated.")
    add_bullet(doc, "Replace lexical retrieval with a cached embedding index and measure whether it improves similar-case quality.")
    add_bullet(doc, "Expand and verify the official Xbox support article catalog instead of relying on saved Twitter short links.")
    add_bullet(doc, "Tune routing thresholds only on development data, then rerun the frozen golden set once.")
    add_bullet(doc, "Run the agent in shadow mode beside a human support queue before enabling any auto-handling.")
    add_heading(doc, "Why the project is still useful", 1)
    add_body(doc, "The system is small, but it is inspectable. A reviewer can run it quickly, see the retrieval evidence, inspect the golden labels and reproduce the uncomfortable safety results. For this task, that proof matters more than pretending I built a magical chatbot.")

    # Page 6
    page_break(doc)
    add_heading(doc, "Decision log", 1)
    decisions = [
        "I chose XboxSupport because it has enough volume, a focused support domain and personal relevance as someone who enjoys gaming.",
        "I filtered by XboxSupport account identity and reply ancestry, not just the word Xbox, to avoid irrelevant chatter.",
        "I classified customer messages. Historical agent replies were used as evidence for resolution style.",
        "I used nine broad, action-oriented intents so the taxonomy could be reviewed consistently.",
        "I kept an other or needs context class instead of forcing vague tweets into a wrong specific intent.",
        "I split by conversation thread so related messages could not leak across training and testing.",
        "I removed historical answers from golden rows to prevent reply leakage.",
        "I used retrieval to pre-label then manually reviewed the golden set because raw Twitter data is too noisy for blank-sheet labelling at this scale.",
        "I treated visual attachments and clear media references as escalation because the export cannot reliably expose visual content.",
        "I used official Xbox pages as redirection targets, never as proof that the agent performed an account action.",
        "I selected balanced Naive Bayes because it beat the trivial baseline and is easy to rerun and explain.",
        "I capped each intent at 700 training examples to reduce domination by frequent account/context language.",
        "I used narrow auto-handling for subscription and game-download workflows only.",
        "I reported unsafe auto-handles separately because intent F1 can make a risky system look better than it is.",
        "I used a local LLM judge to avoid dependency on paid APIs and reported its poor human agreement honestly.",
    ]
    for decision in decisions:
        add_bullet(doc, decision)
    add_heading(doc, "Sources and borrowed components", 1)
    add_bullet(doc, "Customer Support on Twitter dataset: Kaggle, thoughtvector/customer-support-on-twitter")
    add_bullet(doc, "Xbox official support pages: support.xbox.com/en-GB")
    add_bullet(doc, "Banking77: considered for intent-method inspiration only; not used for Xbox training")
    add_bullet(doc, "Ollama for local model runtime and Qwen 2.5 3B Instruct for the reply-quality judge")
    add_body(doc, "Full links and reproducibility instructions are in the repository README.", 8.5, after=0)

    doc.core_properties.title = "XboxSupport Twitter Agent Report"
    doc.core_properties.author = "Rani J"
    doc.save(OUT)
    print(OUT.resolve())


if __name__ == "__main__":
    main()
