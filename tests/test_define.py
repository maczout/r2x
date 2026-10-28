"""r2x define, show and the session without Wine: the catalogue, the questions, the docker
command, and the command line against the fake docker (tests/fake_docker.py)."""
import io
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from r2x import ask, catalogue
from r2x.ask import AnswerError, Question
from r2x.catalogue import CatalogueError, parse_step
from r2x.define import Prompter, file_name_from, report_for, set_line, worker_command
from r2x.settings import Settings
from r2x.shell import Shell, split_words

HERE = Path(__file__).parent
DIALOGS_TXT = HERE.parent / "docs" / "r2k-dialogs.txt"

# Each catalogue dialog's RT_DIALOG templates in r2k.exe (docs/r2k-dialogs.txt).
TEMPLATES = {"quick": [300, 302, 303, 304], "general": [120], "materials": [14],
             "section": [310], "long": [13], "trans": [13], "tendons": [13], "loads": [5],
             "units": [320], "factors": [320]}


def template_ids() -> dict[int, set[int]]:
    out, current = {}, None
    for line in DIALOGS_TXT.read_text(encoding="utf-8").splitlines():
        m = re.match(r"=== DIALOG (\d+) ", line)
        if m:
            current = out.setdefault(int(m.group(1)), set())
        elif current is not None and line.strip() and not line.startswith("#"):
            current.add(int(line.split()[0]))
    return out


# -- the catalogue ------------------------------------------------------------------------------
def test_every_control_is_in_the_dialogs_template():
    ids = template_ids()
    for d in catalogue.DIALOGS:
        pages = TEMPLATES[d.noun]
        for k, page in enumerate(d.pages):
            have = ids[pages[k] if len(pages) == len(d.pages) else pages[0]]
            for f in page.fields:
                used = [f.id, f.label, f.unit, f.unless, *(o.id for o in f.options)]
                missing = [c for c in used if c is not None and c not in have]
                assert not missing, f"{d.noun}.{f.key}: {missing} not in its template"
        if d.list:
            lc = d.list
            assert {lc.box, lc.name, lc.add, lc.modify, lc.delete} <= ids[pages[0]]


def test_catalogue_is_complete_and_consistent():
    assert catalogue.NOUNS == ("quick", "general", "materials", "section", "long", "trans",
                               "tendons", "loads", "units", "factors")
    for d in catalogue.DIALOGS:
        keys = [f.key for f in d.fields]
        assert len(keys) == len(set(keys)), d.noun
        assert all(f.kind in catalogue.KINDS for f in d.fields)
        assert (d.list is not None) == (d.kind == "list") and (d.item != "") == (d.kind == "list")
        if d.kind == "wizard":
            assert [p.title for p in d.pages] == [f"Quick Define - Step {i} of 4"
                                                   for i in range(1, 5)]
    # the menu commands of docs/define.md
    assert {d.noun: d.menu for d in catalogue.DIALOGS} == {
        "quick": 150, "general": 103, "materials": 117, "section": 153, "long": 156,
        "trans": 154, "tendons": 5098, "loads": 152, "units": 321, "factors": 321}


def test_parse_step():
    s = parse_step(["Long", "ADD", "web"])
    assert (s.noun, s.action, s.name, s.words()) == ("long", "add", "web", ["long", "add", "web"])
    assert parse_step(["trans"]).action is None
    assert parse_step(["quick"]).words() == ["quick"]
    for words, msg in ((["beam"], "no dialog 'beam'"), ([], "define what"),
                       (["quick", "x"], "takes no more words"),
                       (["long", "remove", "x"], "use add, modify or delete"),
                       (["long", "add", "a", "b"], "quote a name")):
        with pytest.raises(CatalogueError, match=msg):
            parse_step(words)


def test_help_text_lists_the_questions_in_order():
    text = catalogue.help_text(catalogue.BY_NOUN["quick"])
    assert text.index("Title") < text.index("Concrete Cylinder Strength") < text.index("Shape")
    assert "Quick Define - Step 3 of 4:" in text
    assert "add|modify|delete" in catalogue.help_text(catalogue.BY_NOUN["long"])


# -- questions and answers -----------------------------------------------------------------------
def test_answers_are_checked_for_their_form_only():
    num = Question("fc", "Concrete Cylinder Strength", "number", "35.0", "MPa")
    assert ask.check_answer(num, "") is None                 # Enter keeps the dialog's value
    assert ask.check_answer(num, " 40 ") == "40" and ask.check_answer(num, "-5") == "-5"
    for bad in ("abc", "nan", "inf", "1,5"):
        with pytest.raises(AnswerError):
            ask.check_answer(num, bad)
    with pytest.raises(AnswerError, match="whole number"):
        ask.check_answer(Question("n", "Number of Bars", "integer", "3"), "2.5")
    yn = Question("a", "Select bar by area", "check", "n")
    assert [ask.check_answer(yn, t) for t in ("y", "YES", "n", "No")] == ["y", "y", "n", "n"]
    need = Question("response", "Response asks: ...", "yesno", keep=False)
    with pytest.raises(AnswerError, match="needed"):
        ask.check_answer(need, "")
    with pytest.raises(AnswerError, match="Latin-1"):
        ask.check_answer(Question("t", "Title", "text"), "Pier cap — north")
    assert ask.check_answer(Question("t", "Title", "text"), "Côté") == "Côté"


def test_choices_by_number_text_or_unique_start():
    stirrups = ["None", "Single Leg", "Open Stirrup", "Closed Stirrup", "Hoop",
                "T Headed single leg", "Interlocking Hoops"]
    assert ask.pick(stirrups, "4") == "Closed Stirrup"
    assert ask.pick(stirrups, "closed") == "Closed Stirrup"
    assert ask.pick(stirrups, "hoop") == "Hoop"             # exact beats the other Hoops
    assert ask.pick(stirrups, "t") == "T Headed single leg"
    with pytest.raises(AnswerError, match="could be"):
        ask.pick(stirrups, "le")              # Single Leg, T Headed single leg
    with pytest.raises(AnswerError, match="none of"):
        ask.pick(stirrups, "spiral")


def test_prompt_shows_the_unit_and_the_value_enter_keeps():
    assert Question("fc", "f'c", "number", "35.0", "MPa").prompt() == "  f'c (MPa) [35.0]: "
    assert Question("a", "By area", "check", "y").prompt() == "  By area [y]: "
    assert Question("r", "Response asks: x?", "yesno", keep=False).prompt() == \
        "  Response asks: x?: "


def test_prompter_with_piped_answers():
    out = io.StringIO()
    p = Prompter(io.StringIO("abc\n42\n\n"), out)
    q = Question("fc", "f'c", "number", "35.0", "MPa")
    assert p.answer(q) == (True, "42")                   # "abc" is asked again
    assert p.answer(q) == (True, None)                   # Enter keeps
    assert p.answer(q) == (True, None)                   # the input ended: Enter
    assert p.answer(Question("r", "Response asks", "yesno", keep=False)) == (False, None)
    assert "'abc' is not a number" in out.getvalue()


def test_file_names_and_set_lines():
    assert file_name_from("New Cross Section") == "new-cross-section.r2t"
    assert file_name_from("Pier cap (north)") == "pier-cap-north.r2t"
    assert report_for(Path("a/pier-cap.r2t")) == Path("a/pier-cap.r2x.html")
    assert set_line([]) == "  set: nothing, every answer as Response had it"
    line = set_line([["Title", "Pier cap"], ["b", "900 mm"]])
    assert line == "  set: Title Pier cap; b 900 mm"


def test_split_words_keeps_backslashes():
    assert split_words(r'open C:\work\pier cap.r2t') == ["open", r"C:\work\pier", "cap.r2t"]
    assert split_words(r'open "C:\work\pier cap.r2t"') == ["open", r"C:\work\pier cap.r2t"]
    assert split_words('define long add ""') == ["define", "long", "add", ""]
    with pytest.raises(ValueError):
        split_words('open "x')


# -- the docker command -------------------------------------------------------------------------
def test_worker_command_mounts_the_file_and_its_folder(tmp_path):
    f = tmp_path / "pier cap.r2t"
    cmd = worker_command(["docker"], "r2x", str, ["long", "add", "web"], input_file=f, out=f,
                         report=report_for(f), date="2026/10/27",
                         settings=Settings(units="us"))
    assert cmd[:4] == ["docker", "run", "--rm", "-i"]
    assert ["-v", f"{f}:/in/pier cap.r2t:ro"] == cmd[cmd.index("-v"):cmd.index("-v") + 2]
    assert f"{tmp_path}:/out" in cmd
    tail = cmd[cmd.index("r2x"):]
    assert tail == ["r2x", "python", "-m", "r2x.worker", "define", "long", "add", "web",
                    "--input", "/in/pier cap.r2t", "--out", "/out/pier cap.r2t",
                    "--report", "/out/pier cap.r2x.html", "--date", "2026/10/27",
                    "--units", "us"]
    show = worker_command(["docker"], "r2x", str, ["long"], input_file=f, mode="show")
    assert ":/out" not in " ".join(show) and show[-1] == "--show"
    screen = worker_command(["docker"], "r2x", str, [], input_file=f, report=report_for(f),
                            screen="undo")
    assert screen[-2:] == ["--screen", "undo"] and f"{tmp_path}:/out" in screen


# -- the command line, against the fake docker ----------------------------------------------------
def r2x(*argv, cwd, stdin=""):
    env = dict(os.environ, PYTHONPATH=str(HERE.parent / "src"), FAKE_DOCKER_MODE="fake",
               R2X_DOCKER=f'"{sys.executable}" "{HERE / "fake_docker.py"}"')
    p = subprocess.run([sys.executable, "-m", "r2x.cli", *argv], input=stdin, text=True,
                       capture_output=True, env=env, cwd=cwd)
    return p.returncode, p.stdout, p.stderr


def test_define_on_the_command_line(tmp_path):
    code, out, err = r2x("define", "quick", "pier-cap.r2t", cwd=tmp_path, stdin="Pier cap\n")
    assert code == 0, err
    assert "  Title [fake]: Pier cap" in out and "set: Title Pier cap" in out
    assert "r2x: saved pier-cap.r2t, report pier-cap.r2x.html" in out
    assert (tmp_path / "pier-cap.r2t").read_bytes() == b"<section/>\r\ntitle Pier cap\r\n"
    assert (tmp_path / "pier-cap.r2x.html").exists()
    # a define on the file opens it and saves it back
    code, out, err = r2x("define", "general", "pier-cap.r2t", cwd=tmp_path, stdin="\n")
    assert code == 0, err
    assert "set: nothing" in out


def test_define_quick_asks_before_replacing_a_file(tmp_path):
    (tmp_path / "x.r2t").write_bytes(b"old")
    code, out, err = r2x("define", "quick", "x.r2t", cwd=tmp_path, stdin="n\n")
    assert code == 0 and "x.r2t exists: replace its section [n]: n" in out
    assert (tmp_path / "x.r2t").read_bytes() == b"old"
    code, out, err = r2x("define", "quick", "x.r2t", cwd=tmp_path, stdin="y\nNew\n")
    assert code == 0, err
    assert (tmp_path / "x.r2t").read_bytes() == b"oldtitle New\r\n"   # fake: input + answer


def test_define_usage_errors(tmp_path):
    for argv, msg in ((["define", "quick"], "comes last"),
                      (["define", "beam", "x.r2t"], "no dialog 'beam'"),
                      (["define", "general", "missing.r2t"], "no file missing.r2t"),
                      (["show", "quick", "x.r2t"], "no file")):
        code, _, err = r2x(*argv, cwd=tmp_path)
        assert code == 2 and msg in err, err


def test_show_on_the_command_line(tmp_path):
    (tmp_path / "x.r2t").write_bytes(b"section")
    code, out, err = r2x("show", "x.r2t", cwd=tmp_path)
    assert code == 0 and "file: x.r2t (SHA-256 " in out and "record: none yet" in out
    code, out, err = r2x("show", "long", "x.r2t", cwd=tmp_path)
    assert code == 0 and "  Title: fake" in out


def test_giving_up_at_a_question_saves_nothing(tmp_path):
    (tmp_path / "x.r2t").write_bytes(b"old")
    shell_input = "open x.r2t\ndefine general\n"     # the input ends at the question: Enter
    code, out, err = r2x(cwd=tmp_path, stdin=shell_input)
    assert code == 0 and "set: nothing" in out


def test_session(tmp_path):
    script = "\n".join([
        "help", "show", "define long add web", "define units", "US",
        "define quick", "", "Pier cap",         # file name: the default, then Title
        "show", "define general", "North",       # a second step on the same file
        "undo", "show", "save copy", "undo", "show",
        "bogus", "help define", "help define long", "quit", "never read"]) + "\n"
    code, out, err = r2x(cwd=tmp_path, stdin=script)
    assert code == 0, err
    assert "r2x> help\nCommands" in out
    assert out.count("no section yet: define quick, or open FILE") == 2
    assert "US Customary: for the section define quick makes" in out
    assert "  File name [new-cross-section.r2t]: " in out
    f = tmp_path / "new-cross-section.r2t"
    assert f.read_bytes() == b"<section/>\r\ntitle Pier cap\r\n"   # undo put it back
    assert "undone: new-cross-section.r2t is as it was before define general" in out
    assert "file: new-cross-section.r2t" in out and "undo: back to before define quick" in out
    assert (tmp_path / "copy.r2t").read_bytes() == f.read_bytes()
    assert "save copy.r2t made copy.r2t, which stays as it is; back to new-cross-section.r2t" \
        in out
    assert "no command 'bogus'" in out
    assert "long add|modify|delete [NAME]" in out and "Dist. from Bottom" in out
    assert "never read" not in out


def test_session_without_a_file_asks_for_one(tmp_path):
    code, out, err = r2x(cwd=tmp_path, stdin="solve\nshow long\nopen nope.r2t\nundo\nsave\n")
    assert code == 0
    assert out.count("no section yet") == 3 and "no file" in out and "nothing to undo" in out


def test_session_solve_options(tmp_path):
    (tmp_path / "x.r2t").write_bytes(b"section")
    code, out, err = r2x(cwd=tmp_path, stdin="open x.r2t\nsolve --stdout\nsolve --stage 3\n"
                                              "show\n")
    assert code == 0, err
    assert "--stdout: not in a session" in out
    assert "[x] solved: 10 stages, peak 7 -> x.r2x.txt, x.r2x.html" in err
    assert "record: x.r2x.txt" in out


def test_record_status_says_when_the_record_is_stale(tmp_path):
    from r2x import record
    from r2x.shell import record_status, sha
    f = tmp_path / "x.r2t"
    f.write_bytes(b"one")
    assert record_status(f) == "none yet (solve)"
    data = record.encode({"input-sha256": sha(f), "stage-count": "60", "peak-stage": "56"}, [])
    (tmp_path / "x.r2x.txt").write_bytes(data)
    assert record_status(f) == "x.r2x.txt, a solve of this file (60 stages, peak 56)"
    f.write_bytes(b"two")
    assert "stale" in record_status(f)
