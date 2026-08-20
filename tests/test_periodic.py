from atomic_structure_explorer.periodic import (
    ELEMENTS,
    accepted_configuration,
    aufbau_configuration,
    format_configuration,
)


def test_periodic_table_has_all_elements():
    assert len(ELEMENTS) == 118
    assert {element.atomic_number for element in ELEMENTS} == set(range(1, 119))
    assert len({element.symbol for element in ELEMENTS}) == 118


def test_configurations_preserve_electron_count():
    for z in range(1, 119):
        assert aufbau_configuration(z).electron_count == z
        assert accepted_configuration(z).electron_count == z


def test_known_configuration_exception_is_not_hidden():
    predicted = format_configuration(aufbau_configuration(24))
    accepted = format_configuration(accepted_configuration(24))
    assert predicted != accepted
    assert "3d4" in predicted and "4s2" in predicted
    assert "3d5" in accepted and "4s" in accepted


def test_sodium_shorthand():
    assert format_configuration(accepted_configuration(11)) == "[Ne] 3s"
