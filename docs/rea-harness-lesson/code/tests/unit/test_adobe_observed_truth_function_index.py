import json

from scripts.adobe_observed_truth.function_index import FunctionIndex, load_index


def _record(address, name, ranges, status="written"):
    return json.dumps({"address": address, "name": name, "status": status,
                       "body": {"available": True, "ranges": [{"start": s, "end": e} for s, e in ranges]}})


JOURNAL = [
    _record("0x140001000", "FUN_140001000", [("0x140001000", "0x14000107f")]),
    _record("0x140002000", "Curves_Draw", [("0x140002000", "0x1400020ff"), ("0x140009000", "0x14000901f")]),
    _record("0x140003000", "thunk_FUN_140001000", [("0x140003000", "0x140003007")]),
    _record("EXTERNAL:0x16ee", "BIB.DLL::Ordinal_4", [], status="external"),
]


def test_an_address_belongs_to_the_function_whose_body_holds_it():
    index = FunctionIndex.from_journal(JOURNAL)
    assert index.containing(0x140001000) == "0x140001000"
    assert index.containing(0x14000107F) == "0x140001000"
    assert index.containing(0x140009010) == "0x140002000"  # a non-contiguous body's second piece
    assert index.containing(0x140001080) is None  # between bodies: no function
    assert index.containing(0x16EE) is None  # externals have no body in the binary


def test_callees_are_the_functions_named_in_a_function_pseudocode():
    index = FunctionIndex.from_journal(JOURNAL)
    pseudocode = """void FUN_140004000(void) {
  FUN_140001000(1);
  thunk_FUN_140001000();
  Curves_Draw(param_1, FUN_140001000);
  if (Curves_Draw == 0) return;
  FUN_140007777(2);
  memset(buf, 0, 4);
}"""
    # Named calls resolve through the journal; an unlisted FUN_ address is still that address;
    # a library call the journal does not hold is not a callee in this binary.
    assert index.callees(pseudocode) == ["0x140001000", "0x140002000", "0x140003000", "0x140007777"]


def test_the_index_is_scanned_from_the_journal_once_and_kept_beside_it(tmp_path):
    work = tmp_path / "Photoshop.exe"
    (work / "pseudocode").mkdir(parents=True)
    (work / "pseudocode" / "decompile-journal.jsonl").write_text("\n".join(JOURNAL) + "\n", encoding="utf-8")
    first = load_index(work)
    (work / "pseudocode" / "decompile-journal.jsonl").write_text("", encoding="utf-8")
    again = load_index(work)  # from the kept index, not the (now empty) journal
    assert again.containing(0x140009010) == first.containing(0x140009010) == "0x140002000"
    assert again.callees("void f(void) { Curves_Draw(); }") == ["0x140002000"]
    assert (work / "function-index.json").exists()
