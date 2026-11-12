import pytest

from app.core.languages import EXECUTABLE_LANGUAGES, SPECS, spec_for
from app.features.grading.models import Language


def test_every_language_has_a_spec():
    assert set(SPECS) == set(Language)


def test_executable_set_is_derived_not_duplicated():
    assert EXECUTABLE_LANGUAGES == frozenset(
        lang for lang, spec in SPECS.items() if spec.executable
    )


def test_c_cpp_and_python_are_executable():
    assert EXECUTABLE_LANGUAGES == frozenset({Language.C, Language.CPP, Language.PYTHON})


def test_python_has_no_binary_placeholder():
    spec = spec_for(Language.PYTHON)
    assert "{src}" in " ".join(spec.run_cmd)
    assert "{bin}" not in " ".join(spec.run_cmd)


def test_cpp_compiles_to_a_binary():
    spec = spec_for(Language.CPP)
    assert spec.compile_cmd is not None
    assert "{bin}" in " ".join(spec.compile_cmd)
    assert spec.run_cmd == ["{bin}"]


def test_extensions_are_unique_among_executables():
    extensions = [SPECS[lang].extension for lang in EXECUTABLE_LANGUAGES]
    assert len(extensions) == len(set(extensions))


def test_spec_for_rejects_unknown():
    with pytest.raises(KeyError):
        spec_for("perl")


def test_lizard_name_present_for_executables():
    for lang in EXECUTABLE_LANGUAGES:
        assert SPECS[lang].lizard_name
