#!/usr/bin/env python3
"""
Interactive quiz reader for GARP Risk & AI .tex question files.

Usage:
    python3 quiz.py garp_q351_450_fixed.tex
    python3 quiz.py garp_q451_550.tex --shuffle
    python3 quiz.py garp_q351_450_fixed.tex --start 10 --end 50
    python3 quiz.py garp_q351_450_fixed.tex --mode exam
"""

import re
import sys
import random
import argparse
from pathlib import Path


# ---------------------------------------------------------------------------
# PARSER
# ---------------------------------------------------------------------------

def parse_tex_file(path):
    """
    Extract questions from a Beamer .tex file.

    Each frame is expected to look like:

        \\begin{frame}{Q351 --- Title}
        \\begin{block}{Question}
        ... question text ...
        \\begin{enumerate}
        \\item Option A
        \\item Option B
        \\item Option C
        \\item Option D
        \\end{enumerate}
        \\end{block}
        \\begin{exampleblock}{Answer: B}\\end{exampleblock}
        \\begin{block}{Explanation}
        ... explanation ...
        \\end{block}
        \\end{frame}
    """
    text = Path(path).read_text(encoding="utf-8")

    questions = []

    # Split on \begin{frame}{...}
    frame_pattern = re.compile(
        r"\\begin\{frame\}\{(.*?)\}(.*?)\\end\{frame\}",
        re.DOTALL,
    )

    for match in frame_pattern.finditer(text):
        title = match.group(1).strip()
        body = match.group(2)

        # Skip title page or frames without a Question block
        if "\\begin{block}{Question}" not in body:
            continue

        # Extract question text
        q_match = re.search(
            r"\\begin\{block\}\{Question\}(.*?)\\begin\{enumerate\}",
            body,
            re.DOTALL,
        )
        if not q_match:
            continue
        question_text = clean_latex(q_match.group(1))

        # Extract options
        opts_match = re.search(
            r"\\begin\{enumerate\}(.*?)\\end\{enumerate\}",
            body,
            re.DOTALL,
        )
        if not opts_match:
            continue
        options_raw = opts_match.group(1)
        options = re.findall(r"\\item\s+(.*?)(?=\\item|$)", options_raw, re.DOTALL)
        options = [clean_latex(o) for o in options]

        if len(options) < 4:
            continue

        # Extract correct answer letter
        ans_match = re.search(
            r"\\begin\{exampleblock\}\{Answer:\s*([A-D])\s*\}",
            body,
        )
        if not ans_match:
            continue
        correct = ans_match.group(1).strip().upper()

        # Extract explanation
        expl_match = re.search(
            r"\\begin\{block\}\{Explanation\}(.*?)\\end\{block\}",
            body,
            re.DOTALL,
        )
        explanation = clean_latex(expl_match.group(1)) if expl_match else ""

        questions.append({
            "title": title,
            "question": question_text,
            "options": options,
            "correct": correct,
            "explanation": explanation,
        })

    return questions


def clean_latex(s):
    """Strip common LaTeX markup for readable terminal output."""
    if not s:
        return ""
    s = re.sub(r"\\begin\{[^}]*\}", "", s)
    s = re.sub(r"\\end\{[^}]*\}", "", s)
    s = re.sub(r"\\textbf\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\textit\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\emph\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\texttt\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\text\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\item\s+", "\n  - ", s)
    s = re.sub(r"\\\\", "\n", s)
    s = re.sub(r"\\[a-zA-Z]+\{[^}]*\}", "", s)
    s = re.sub(r"\\[a-zA-Z]+", "", s)
    s = re.sub(r"[{}]", "", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


# ---------------------------------------------------------------------------
# QUIZ RUNNER
# ---------------------------------------------------------------------------

def run_quiz(questions, shuffle=False, exam_mode=False):
    if not questions:
        print("No questions found in file.")
        return

    if shuffle:
        random.shuffle(questions)

    total = len(questions)
    correct_count = 0
    wrong = []

    print("\n" + "=" * 78)
    print(f"  GARP Risk & AI Quiz  ---  {total} questions loaded")
    print(f"  Mode: {'exam (no feedback until end)' if exam_mode else 'practice (immediate feedback)'}")
    print("=" * 78)
    print("  Press Ctrl+C at any time to quit.\n")

    try:
        for i, q in enumerate(questions, start=1):
            print("-" * 78)
            print(f"Question {i} / {total}  ---  {q['title']}\n")
            print(wrap(q["question"], width=78))
            print()

            for j, opt in enumerate(q["options"]):
                letter = chr(ord("A") + j)
                print(f"  [{letter}] {wrap(opt, width=72, indent=6)}")

            print()
            choice = ""
            while choice not in ["A", "B", "C", "D", "Q"]:
                choice = input("Your answer (A/B/C/D, Q to quit): ").strip().upper()

            if choice == "Q":
                print("\nQuitting quiz.")
                break

            if choice == q["correct"]:
                correct_count += 1
                if not exam_mode:
                    print("\n  [OK] Correct!\n")
                    if q["explanation"]:
                        print("  Explanation:")
                        print(indent(wrap(q["explanation"], width=74), 4))
                else:
                    print("  Answer recorded.\n")
            else:
                wrong.append((i, q, choice))
                if not exam_mode:
                    print(f"\n  [X] Wrong. Correct answer: {q['correct']}\n")
                    print(f"  Correct option: {q['options'][ord(q['correct']) - ord('A')]}\n")
                    if q["explanation"]:
                        print("  Explanation:")
                        print(indent(wrap(q["explanation"], width=74), 4))
                else:
                    print("  Answer recorded.\n")

    except KeyboardInterrupt:
        print("\n\nQuiz interrupted.")

    # ---- Summary ----
    attempted = i if 'i' in locals() else 0
    print("\n" + "=" * 78)
    print("  RESULTS")
    print("=" * 78)
    print(f"  Attempted:  {attempted}")
    print(f"  Correct:    {correct_count}")
    if attempted:
        print(f"  Score:      {correct_count / attempted * 100:.1f}%")
    print()

    if wrong:
        print("  Review these questions:\n")
        for num, q, choice in wrong:
            print(f"  Q{num} ({q['title']})")
            print(f"    Your answer:    {choice}")
            print(f"    Correct answer: {q['correct']}")
            print(f"    {q['options'][ord(q['correct']) - ord('A')]}")
            print()

    print("=" * 78)


# ---------------------------------------------------------------------------
# TEXT UTILITIES
# ---------------------------------------------------------------------------

def wrap(text, width=78, indent=0):
    """Simple word wrap preserving paragraph breaks."""
    import textwrap
    prefix = " " * indent
    paragraphs = text.split("\n")
    lines = []
    for para in paragraphs:
        if not para.strip():
            lines.append("")
        else:
            wrapped = textwrap.wrap(para.strip(), width=width - indent)
            lines.extend(prefix + w for w in wrapped)
    return "\n".join(lines)


def indent(text, n):
    prefix = " " * n
    return "\n".join(prefix + line if line.strip() else line for line in text.split("\n"))


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Interactive quiz reader for GARP Risk & AI .tex files")
    parser.add_argument("file", help="Path to the .tex question file")
    parser.add_argument("--shuffle", action="store_true", help="Randomize question order")
    parser.add_argument("--start", type=int, default=1, help="Start at question N (1-indexed)")
    parser.add_argument("--end", type=int, default=None, help="Stop at question N (inclusive)")
    parser.add_argument("--mode", choices=["practice", "exam"], default="practice",
                        help="practice = immediate feedback; exam = feedback only at end")
    parser.add_argument("--limit", type=int, default=None, help="Only take first N questions")
    args = parser.parse_args()

    if not Path(args.file).exists():
        print(f"Error: file not found: {args.file}")
        sys.exit(1)

    questions = parse_tex_file(args.file)
    print(f"Parsed {len(questions)} questions from {args.file}")

    if not questions:
        print("No valid questions found. Check the file format.")
        sys.exit(1)

    # Apply slicing
    start = max(0, args.start - 1)
    end = args.end if args.end else len(questions)
    questions = questions[start:end]

    if args.limit:
        questions = questions[:args.limit]

    run_quiz(questions, shuffle=args.shuffle, exam_mode=(args.mode == "exam"))


if __name__ == "__main__":
    main()